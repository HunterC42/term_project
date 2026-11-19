import os
import time
import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

load_dotenv()

st.set_page_config(
    page_title="Chicago Crimes Analytics | Team 7",
    layout="wide",
)


def get_database_url() -> str:
    """Build PostgreSQL connection URL from .env / environment variables."""
    load_dotenv()
    if os.getenv("DATABASE_URL"):
        return os.environ["DATABASE_URL"]

    user = os.getenv("POSTGRES_USER") or os.getenv("DB_USER") or "postgres"
    password = os.getenv("POSTGRES_PASSWORD") or os.getenv("DB_PASSWORD")
    if not password:
        raise RuntimeError(
            "POSTGRES_PASSWORD is not set. Ensure .env is configured before starting the dashboard."
        )
    host = os.getenv("POSTGRES_HOST") or os.getenv("DB_HOST") or "db"
    port = os.getenv("POSTGRES_PORT") or os.getenv("DB_PORT") or "5432"
    dbname = os.getenv("POSTGRES_DB") or os.getenv("DB_NAME") or "chicago_crimes"
    return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}"


@st.cache_resource
def get_engine():
    return create_engine(get_database_url(), pool_pre_ping=True)


def wait_for_tables(max_retries: int = 40, delay_sec: int = 3) -> bool:
    """Wait gracefully if the ETL container is still creating/populating star-schema tables."""
    engine = get_engine()
    check_sql = text(
        """
        SELECT COUNT(*)
        FROM information_schema.tables
        WHERE table_schema = 'public'
          AND table_name IN ('fact_crime', 'dim_crime_type', 'dim_location', 'dim_date');
        """
    )
    for _ in range(max_retries):
        try:
            with engine.connect() as conn:
                table_count = conn.execute(check_sql).scalar() or 0
                if table_count == 4:
                    crime_rows = conn.execute(text("SELECT COUNT(*) FROM fact_crime;")).scalar() or 0
                    if crime_rows > 0:
                        return True
        except (OperationalError, ProgrammingError):
            pass
        time.sleep(delay_sec)
    return False


@st.cache_data(ttl=60)
def load_filter_options() -> dict:
    """Fetch distinct filter bounds and categories from PostgreSQL star schema."""
    engine = get_engine()
    with engine.connect() as conn:
        date_bounds = conn.execute(
            text("SELECT MIN(occurred_at)::date AS min_d, MAX(occurred_at)::date AS max_d FROM fact_crime;")
        ).mappings().first()

        areas_df = pd.read_sql(
            text(
                """
                SELECT DISTINCT community_area
                FROM dim_location
                WHERE community_area IS NOT NULL
                  AND community_area > 0
                ORDER BY community_area;
                """
            ),
            conn,
        )

        types_df = pd.read_sql(
            text(
                """
                SELECT ct.primary_type, COUNT(*) AS cnt
                FROM fact_crime f
                JOIN dim_crime_type ct
                    ON f.crime_type_key = ct.crime_type_key
                WHERE ct.primary_type IS NOT NULL
                GROUP BY ct.primary_type
                ORDER BY cnt DESC;
                """
            ),
            conn,
        )

    return {
        "min_date": date_bounds["min_d"],
        "max_date": date_bounds["max_d"],
        "areas": [int(a) for a in areas_df["community_area"].tolist()],
        "crime_types": types_df["primary_type"].tolist(),
    }


def build_where_clause(
    start_date,
    end_date,
    selected_areas: list[int],
    selected_types: list[str],
    arrests_only: bool,
    search_term: str,
) -> tuple[str, dict]:
    """Build parameterized SQL WHERE conditions for filtered star-schema queries."""
    clauses = ["f.occurred_at::date BETWEEN :start_date AND :end_date"]
    params: dict = {"start_date": start_date, "end_date": end_date}

    if selected_areas:
        clauses.append("l.community_area = ANY(:areas)")
        params["areas"] = selected_areas

    if selected_types:
        clauses.append("ct.primary_type = ANY(:crime_types)")
        params["crime_types"] = selected_types

    if arrests_only:
        clauses.append("f.arrest IS TRUE")

    if search_term.strip():
        clauses.append(
            "(ct.description ILIKE :search OR l.block ILIKE :search OR l.location_description ILIKE :search)"
        )
        params["search"] = f"%{search_term.strip()}%"

    return " WHERE " + " AND ".join(clauses), params


@st.cache_data(ttl=60)
def query_kpis(where_sql: str, params: dict) -> dict:
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            COUNT(*) AS total_crimes,
            SUM(CASE WHEN f.arrest THEN 1 ELSE 0 END) AS total_arrests,
            COUNT(DISTINCT l.community_area) FILTER (WHERE l.community_area > 0) AS active_areas,
            MAX(f.updated_on) AS latest_update
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql};
        """
    )
    with engine.connect() as conn:
        row = conn.execute(sql, params).mappings().first()
    return dict(row) if row else {}


@st.cache_data(ttl=60)
def query_top_areas(where_sql: str, params: dict) -> pd.DataFrame:
    """Q1: Which community areas of Chicago have the most reported crimes?"""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            l.community_area,
            'Area #' || l.community_area::text AS area_label,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
          AND l.community_area IS NOT NULL
          AND l.community_area > 0
        GROUP BY l.community_area
        ORDER BY crime_count DESC
        LIMIT 15;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=60)
def query_common_crimes(where_sql: str, params: dict) -> pd.DataFrame:
    """What are the most common types of crime reported in Chicago?"""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            ct.primary_type,
            CASE WHEN f.arrest THEN 'Arrest Made' ELSE 'No Arrest' END AS arrest_status,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
        GROUP BY ct.primary_type, arrest_status
        ORDER BY crime_count DESC;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=60)
def query_crime_area_matrix(where_sql: str, params: dict) -> pd.DataFrame:
    """Crime type share across top community areas."""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            'Area #' || l.community_area::text AS area_label,
            ct.primary_type,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
          AND l.community_area IS NOT NULL
          AND l.community_area > 0
        GROUP BY l.community_area, ct.primary_type;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=60)
def query_hourly_activity(where_sql: str, params: dict) -> pd.DataFrame:
    """Crime frequency by hour of day."""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            EXTRACT(HOUR FROM f.occurred_at)::int AS hour_of_day,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
        GROUP BY hour_of_day
        ORDER BY hour_of_day ASC;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=60)
def query_trends_by_type(where_sql: str, params: dict) -> pd.DataFrame:
    """How have crime patterns changed over time across top crime categories?"""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            DATE_TRUNC('month', f.occurred_at)::date AS period,
            ct.primary_type,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
        GROUP BY period, ct.primary_type
        ORDER BY period ASC, ct.primary_type ASC;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


@st.cache_data(ttl=60)
def query_sample_records(where_sql: str, params: dict) -> pd.DataFrame:
    """Fetch recent filtered records for interactive map and table inspection."""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            f.crime_id AS id,
            f.case_number,
            f.occurred_at AS date,
            ct.primary_type,
            ct.description,
            l.location_description,
            l.block,
            f.arrest,
            l.community_area,
            l.latitude,
            l.longitude
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
        ORDER BY f.occurred_at DESC
        LIMIT 500;
        """
    )
    with engine.connect() as conn:
        return pd.read_sql(sql, conn, params=params)


# --- App Layout ---
st.title("Chicago Crimes & Community Area Analytics")
st.caption("DAEN 328 Term Project — Team 7 | Live PostgreSQL + Streamlit Pipeline")

if not wait_for_tables():
    st.error(
        "Database tables (`fact_crime`, `dim_crime_type`, `dim_location`, `dim_date`) are not populated yet. "
        "Check `docker-compose logs etl` to verify the ETL container completed."
    )
    st.stop()

options = load_filter_options()
if not options["min_date"] or not options["max_date"]:
    st.warning("No crime records found in PostgreSQL.")
    st.stop()

# --- Sidebar Interactive Controls ---
with st.sidebar:
    st.header("Dashboard Filters")

    if st.button("Refresh Data from DB", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

    date_range = st.date_input(
        "Incident Date Range",
        value=(options["min_date"], options["max_date"]),
        min_value=options["min_date"],
        max_value=options["max_date"],
    )
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date, end_date = date_range
    else:
        start_date = end_date = date_range[0] if isinstance(date_range, tuple) else date_range

    selected_areas = st.multiselect(
        "Community Area Numbers",
        options=options["areas"],
        default=[],
        format_func=lambda x: f"Area #{x}",
        placeholder="All community areas",
    )

    selected_types = st.multiselect(
        "Primary Crime Types",
        options=options["crime_types"],
        default=[],
        placeholder="All crime types",
    )

    arrests_only = st.checkbox("Show arrests only", value=False)
    search_term = st.text_input(
        "Search block, description, or location",
        placeholder="e.g., APARTMENT, RETAIL, HALSTED",
    )

where_sql, params = build_where_clause(
    start_date=start_date,
    end_date=end_date,
    selected_areas=selected_areas,
    selected_types=selected_types,
    arrests_only=arrests_only,
    search_term=search_term,
)

# --- Top KPI Metrics ---
kpis = query_kpis(where_sql, params)
total_crimes = int(kpis.get("total_crimes") or 0)
total_arrests = int(kpis.get("total_arrests") or 0)
arrest_rate = (total_arrests / total_crimes * 100) if total_crimes else 0.0
active_areas = int(kpis.get("active_areas") or 0)
latest_update = kpis.get("latest_update")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Filtered Crime Records", f"{total_crimes:,}")
col2.metric("Arrest Rate", f"{arrest_rate:.1f}%", f"{total_arrests:,} arrests")
col3.metric("Community Areas Represented", f"{active_areas}")
col4.metric("Latest DB Checkpoint", str(latest_update)[:19] if latest_update else "N/A")

st.divider()

# --- Row 1: Top Areas & Most Common Crime Types ---
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("1. Top Community Areas by Reported Crimes")
    top_areas_df = query_top_areas(where_sql, params)
    if top_areas_df.empty:
        st.info("No area records match the current filters.")
    else:
        fig_areas = px.bar(
            top_areas_df.sort_values("crime_count", ascending=True),
            x="crime_count",
            y="area_label",
            orientation="h",
            labels={
                "crime_count": "Reported Crimes",
                "area_label": "Community Area",
            },
        )
        fig_areas.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_areas, use_container_width=True)

with right_col:
    st.subheader("2. Most Common Crime Types & Arrest Breakdown")
    common_df = query_common_crimes(where_sql, params)
    if common_df.empty:
        st.info("No crime types match the current filters.")
    else:
        top_10_types = (
            common_df.groupby("primary_type")["crime_count"]
            .sum()
            .nlargest(10)
            .index.tolist()
        )
        filtered_common = common_df[common_df["primary_type"].isin(top_10_types)]
        fig_types = px.bar(
            filtered_common,
            x="crime_count",
            y="primary_type",
            color="arrest_status",
            orientation="h",
            barmode="stack",
            category_orders={"primary_type": top_10_types},
            labels={
                "crime_count": "Reported Crimes",
                "primary_type": "Primary Crime Type",
                "arrest_status": "Outcome",
            },
        )
        fig_types.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_types, use_container_width=True)

# --- Row 2: Crime Type Share Across Top Areas & Hourly Distribution ---
left_col2, right_col2 = st.columns(2)

with left_col2:
    st.subheader("3. Crime Type Share Across Top Community Areas")
    matrix_df = query_crime_area_matrix(where_sql, params)
    if matrix_df.empty:
        st.info("Not enough community area data for the current filter selection.")
    else:
        top_8_types = (
            matrix_df.groupby("primary_type")["crime_count"]
            .sum()
            .nlargest(8)
            .index.tolist()
        )
        top_8_areas = (
            matrix_df.groupby("area_label")["crime_count"]
            .sum()
            .nlargest(8)
            .index.tolist()
        )
        sub_matrix = matrix_df[
            matrix_df["primary_type"].isin(top_8_types)
            & matrix_df["area_label"].isin(top_8_areas)
        ]
        pivot = sub_matrix.pivot_table(
            index="primary_type",
            columns="area_label",
            values="crime_count",
            aggfunc="sum",
            fill_value=0,
        )
        pct_pivot = pivot.div(pivot.sum(axis=0), axis=1) * 100
        fig_heatmap = px.imshow(
            pct_pivot.round(1),
            text_auto=True,
            aspect="auto",
            color_continuous_scale="Blues",
            labels={"x": "Community Area", "y": "Crime Type", "color": "% of Area Crimes"},
        )
        fig_heatmap.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_heatmap, use_container_width=True)

with right_col2:
    st.subheader("4. Reported Crimes by Hour of Day")
    hourly_df = query_hourly_activity(where_sql, params)
    if hourly_df.empty:
        st.info("No hourly data available for the current filters.")
    else:
        fig_hourly = px.bar(
            hourly_df,
            x="hour_of_day",
            y="crime_count",
            labels={
                "hour_of_day": "Hour of Day (0–23)",
                "crime_count": "Reported Crimes",
            },
        )
        fig_hourly.update_layout(height=430, margin=dict(l=10, r=10, t=10, b=10))
        fig_hourly.update_xaxes(dtick=2)
        st.plotly_chart(fig_hourly, use_container_width=True)

# --- Row 3: Crime Patterns Over Time ---
st.subheader("5. Monthly Crime Trends by Top Crime Types")
trends_df = query_trends_by_type(where_sql, params)
if trends_df.empty:
    st.info("No time-series records available for the current filters.")
else:
    top_5_trend_types = (
        trends_df.groupby("primary_type")["crime_count"]
        .sum()
        .nlargest(5)
        .index.tolist()
    )
    filtered_trends = trends_df[trends_df["primary_type"].isin(top_5_trend_types)]
    fig_trends = px.line(
        filtered_trends,
        x="period",
        y="crime_count",
        color="primary_type",
        markers=True,
        labels={
            "period": "Month",
            "crime_count": "Reported Crimes",
            "primary_type": "Crime Type",
        },
    )
    fig_trends.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    fig_trends.update_xaxes(range=[str(start_date), str(end_date)])
    st.plotly_chart(fig_trends, use_container_width=True)

# --- Row 4: Incident Map & Interactive Table ---
st.subheader("6. Recent Incident Locations & Records Explorer")
sample_df = query_sample_records(where_sql, params)
map_col, table_col = st.columns([1, 1.3])

with map_col:
    geo_df = sample_df.dropna(subset=["latitude", "longitude"]).copy()
    if geo_df.empty:
        st.info("No valid coordinates in the current filtered slice.")
    else:
        st.map(geo_df[["latitude", "longitude"]])

with table_col:
    display_cols = [
        "case_number",
        "date",
        "primary_type",
        "description",
        "community_area",
        "arrest",
    ]
    st.dataframe(sample_df[display_cols], use_container_width=True, height=340)
