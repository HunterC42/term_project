import os
import time
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError, ProgrammingError

load_dotenv()

st.set_page_config(
    page_title="Chicago Crimes Analytics | Team 7",
    layout="wide",
)

# Official 77 Chicago Community Areas:
# area_num -> (community_name, chicago_region, area_sq_mi, population)
COMMUNITY_AREA_META: dict[int, tuple[str, str, float, int]] = {
    1: ("Rogers Park", "Far North Side", 1.84, 54173),
    2: ("West Ridge", "Far North Side", 3.53, 78373),
    3: ("Uptown", "Far North Side", 2.32, 56344),
    4: ("Lincoln Square", "Far North Side", 2.56, 41651),
    5: ("North Center", "North Side", 2.05, 36014),
    6: ("Lake View", "North Side", 3.12, 102827),
    7: ("Lincoln Park", "North Side", 3.16, 67987),
    8: ("Near North Side", "Central", 2.74, 107331),
    9: ("Edison Park", "Far North Side", 1.13, 11558),
    10: ("Norwood Park", "Far North Side", 4.37, 39840),
    11: ("Jefferson Park", "Far North Side", 2.33, 26649),
    12: ("Forest Glen", "Far North Side", 3.20, 19901),
    13: ("North Park", "Far North Side", 2.52, 18356),
    14: ("Albany Park", "Far North Side", 1.92, 45538),
    15: ("Portage Park", "Northwest Side", 3.95, 63031),
    16: ("Irving Park", "Northwest Side", 3.21, 53332),
    17: ("Dunning", "Northwest Side", 3.72, 41233),
    18: ("Montclare", "Northwest Side", 0.99, 14280),
    19: ("Belmont Cragin", "Northwest Side", 3.91, 72088),
    20: ("Hermosa", "Northwest Side", 1.17, 22576),
    21: ("Avondale", "North Side", 1.98, 35533),
    22: ("Logan Square", "North Side", 3.59, 71192),
    23: ("Humboldt Park", "West Side", 3.60, 56153),
    24: ("West Town", "West Side", 4.58, 88164),
    25: ("Austin", "West Side", 7.15, 97452),
    26: ("West Garfield Park", "West Side", 1.28, 15096),
    27: ("East Garfield Park", "West Side", 1.93, 20731),
    28: ("Near West Side", "West Side", 5.69, 68165),
    29: ("North Lawndale", "West Side", 3.21, 33958),
    30: ("South Lawndale", "West Side", 4.59, 69884),
    31: ("Lower West Side", "West Side", 2.93, 33446),
    32: ("Loop", "Central", 1.65, 42550),
    33: ("Near South Side", "Central", 1.78, 30482),
    34: ("Armour Square", "South Side", 1.00, 13885),
    35: ("Douglas", "South Side", 1.65, 21088),
    36: ("Oakland", "South Side", 0.58, 6937),
    37: ("Fuller Park", "South Side", 0.71, 2345),
    38: ("Grand Boulevard", "South Side", 1.74, 25181),
    39: ("Kenwood", "South Side", 1.04, 18417),
    40: ("Washington Park", "South Side", 1.52, 12313),
    41: ("Hyde Park", "South Side", 1.61, 30599),
    42: ("Woodlawn", "South Side", 2.07, 23801),
    43: ("South Shore", "South Side", 2.93, 53588),
    44: ("Chatham", "Far Southeast Side", 2.95, 29942),
    45: ("Avalon Park", "Far Southeast Side", 1.25, 9024),
    46: ("South Chicago", "Far Southeast Side", 3.34, 27551),
    47: ("Burnside", "Far Southeast Side", 0.61, 2304),
    48: ("Calumet Heights", "Far Southeast Side", 1.75, 11229),
    49: ("Roseland", "Far Southeast Side", 4.82, 36635),
    50: ("Pullman", "Far Southeast Side", 2.12, 6744),
    51: ("South Deering", "Far Southeast Side", 10.90, 12854),
    52: ("East Side", "Far Southeast Side", 2.98, 22613),
    53: ("West Pullman", "Far Southeast Side", 3.56, 24549),
    54: ("Riverdale", "Far Southeast Side", 3.53, 10340),
    55: ("Hegewisch", "Far Southeast Side", 5.24, 8927),
    56: ("Garfield Ridge", "Southwest Side", 4.23, 36732),
    57: ("Archer Heights", "Southwest Side", 2.01, 13414),
    58: ("Brighton Park", "Southwest Side", 2.72, 42994),
    59: ("McKinley Park", "Southwest Side", 1.41, 14854),
    60: ("Bridgeport", "South Side", 2.09, 33638),
    61: ("New City", "Southwest Side", 4.83, 40065),
    62: ("West Elsdon", "Southwest Side", 1.17, 17901),
    63: ("Gage Park", "Southwest Side", 2.20, 36081),
    64: ("Clearing", "Southwest Side", 2.55, 23629),
    65: ("West Lawn", "Southwest Side", 2.95, 31942),
    66: ("Chicago Lawn", "Southwest Side", 3.53, 54409),
    67: ("West Englewood", "Southwest Side", 3.15, 28144),
    68: ("Englewood", "Southwest Side", 3.07, 23195),
    69: ("Greater Grand Crossing", "South Side", 3.55, 31471),
    70: ("Ashburn", "Far Southwest Side", 4.86, 42007),
    71: ("Auburn Gresham", "Far Southwest Side", 3.77, 43779),
    72: ("Beverly", "Far Southwest Side", 3.18, 20034),
    73: ("Washington Heights", "Far Southwest Side", 2.86, 25065),
    74: ("Mount Greenwood", "Far Southwest Side", 2.71, 18628),
    75: ("Morgan Park", "Far Southwest Side", 3.30, 21186),
    76: ("O'Hare", "Far North Side", 13.34, 13418),
    77: ("Edgewater", "Far North Side", 1.74, 56296),
}

COMMUNITY_AREA_DF = pd.DataFrame(
    [
        {
            "community_area": num,
            "community_name": meta[0],
            "region": meta[1],
            "area_sq_mi": meta[2],
            "population": meta[3],
        }
        for num, meta in COMMUNITY_AREA_META.items()
    ]
)

ALL_REGIONS: list[str] = sorted(COMMUNITY_AREA_DF["region"].unique().tolist())

REGION_COLOR_MAP: dict[str, str] = {
    "Central": "#636EFA",
    "Far North Side": "#00CC96",
    "Far Southeast Side": "#AB63FA",
    "Far Southwest Side": "#FFA15A",
    "North Side": "#19D3F3",
    "Northwest Side": "#FF6692",
    "South Side": "#EF553B",
    "Southwest Side": "#B6E880",
    "West Side": "#FECB52",
}


def format_community_area(area_num) -> str:
    """Format community area number as '<Official Name> (#<Number>)'."""
    if pd.isna(area_num):
        return "Unknown"
    num = int(area_num)
    meta = COMMUNITY_AREA_META.get(num)
    return f"{meta[0]} (#{num})" if meta else f"Area #{num}"


def get_area_region(area_num) -> str:
    """Return official Chicago region for a community area number."""
    if pd.isna(area_num):
        return "Unknown"
    meta = COMMUNITY_AREA_META.get(int(area_num))
    return meta[1] if meta else "Unknown"


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
    selected_regions: list[str],
    selected_areas: list[int],
    selected_types: list[str],
    arrests_only: bool,
    search_term: str,
) -> tuple[str, dict]:
    """Build parameterized SQL WHERE conditions for filtered star-schema queries."""
    clauses = ["f.occurred_at::date BETWEEN :start_date AND :end_date"]
    params: dict = {"start_date": start_date, "end_date": end_date}

    effective_areas: list[int] | None = None
    if selected_regions:
        region_areas = [
            num for num, meta in COMMUNITY_AREA_META.items() if meta[1] in selected_regions
        ]
        effective_areas = region_areas

    if selected_areas:
        if effective_areas is not None:
            effective_areas = [a for a in selected_areas if a in effective_areas]
        else:
            effective_areas = list(selected_areas)

    if effective_areas is not None:
        if not effective_areas:
            clauses.append("1 = 0")
        else:
            clauses.append("l.community_area = ANY(:areas)")
            params["areas"] = effective_areas

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
    """Which areas of Chicago have the most reported crimes?"""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            l.community_area,
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
        df = pd.read_sql(sql, conn, params=params)
    if not df.empty:
        df["area_label"] = df["community_area"].map(format_community_area)
        df["region"] = df["community_area"].map(get_area_region)
    return df


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
def query_crime_region_matrix(where_sql: str, params: dict) -> pd.DataFrame:
    """Is there a correlation between types of crime and regions in the city?"""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            l.community_area,
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
        df = pd.read_sql(sql, conn, params=params)
    if df.empty:
        return df
    df["region"] = df["community_area"].map(get_area_region)
    df = df[df["region"] != "Unknown"]
    return (
        df.groupby(["region", "primary_type"], as_index=False)["crime_count"]
        .sum()
    )


@st.cache_data(ttl=60)
def query_area_crime_counts(where_sql: str, params: dict) -> pd.DataFrame:
    """Crime counts per community area merged with official population."""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            l.community_area,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
          AND l.community_area IS NOT NULL
          AND l.community_area > 0
        GROUP BY l.community_area;
        """
    )
    with engine.connect() as conn:
        counts_df = pd.read_sql(sql, conn, params=params)

    merged = COMMUNITY_AREA_DF.merge(counts_df, on="community_area", how="left")
    merged["crime_count"] = merged["crime_count"].fillna(0).astype(int)
    merged["crimes_per_1k"] = (merged["crime_count"] / merged["population"]) * 1000.0
    return merged


@st.cache_data(ttl=60)
def query_trends_by_region(where_sql: str, params: dict) -> pd.DataFrame:
    """How have crime patterns changed over time in different regions of Chicago?"""
    engine = get_engine()
    sql = text(
        f"""
        SELECT
            DATE_TRUNC('month', f.occurred_at)::date AS period,
            l.community_area,
            COUNT(*) AS crime_count
        FROM fact_crime f
        JOIN dim_crime_type ct
            ON f.crime_type_key = ct.crime_type_key
        JOIN dim_location l
            ON f.location_key = l.location_key
        {where_sql}
          AND l.community_area IS NOT NULL
          AND l.community_area > 0
        GROUP BY period, l.community_area
        ORDER BY period ASC;
        """
    )
    with engine.connect() as conn:
        df = pd.read_sql(sql, conn, params=params)
    if df.empty:
        return df
    df["region"] = df["community_area"].map(get_area_region)
    df = df[df["region"] != "Unknown"]
    return (
        df.groupby(["period", "region"], as_index=False)["crime_count"]
        .sum()
        .sort_values(["period", "region"])
    )


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
        df = pd.read_sql(sql, conn, params=params)
    if not df.empty:
        df["community_area_name"] = df["community_area"].map(format_community_area)
        df["region"] = df["community_area"].map(get_area_region)
    return df


# --- App Layout ---
st.title("Chicago Crimes Analytics")
st.caption(
    "DAEN 328 Term Project — Team 7 (Hunter Cruce, Yohan Arul, Ethan Rasmussen, Navya Vegesna)"
)

if not wait_for_tables():
    st.error(
        "Database tables (`fact_crime`, `dim_crime_type`, `dim_location`, `dim_date`) are not populated yet. "
        "Run `docker compose --profile etl run --rm etl` to populate PostgreSQL."
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

    selected_regions = st.multiselect(
        "Chicago Regions",
        options=ALL_REGIONS,
        default=[],
        placeholder="All 9 Chicago regions",
    )

    available_areas = (
        [
            a
            for a in options["areas"]
            if get_area_region(a) in selected_regions
        ]
        if selected_regions
        else options["areas"]
    )

    selected_areas = st.multiselect(
        "Community Areas",
        options=available_areas,
        default=[],
        format_func=format_community_area,
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
    selected_regions=selected_regions,
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
latest_update = kpis.get("latest_update")

col1, col2, col3 = st.columns(3)
col1.metric("Filtered Crime Records", f"{total_crimes:,}")
col2.metric(
    "Arrest Rate",
    f"{arrest_rate:.1f}%",
    f"{total_arrests:,} arrests",
    delta_color="off",
    delta_arrow="off",
)
col3.metric("Latest DB Checkpoint", str(latest_update)[:19] if latest_update else "N/A")

st.divider()

# --- Row 1: Top Community Areas & Most Common Crime Types ---
left_col, right_col = st.columns(2)

with left_col:
    st.subheader("Which Areas of Chicago Have the Most Reported Crimes?")
    top_areas_df = query_top_areas(where_sql, params)
    if top_areas_df.empty:
        st.info("No area records match the current filters.")
    else:
        fig_areas = px.bar(
            top_areas_df.sort_values("crime_count", ascending=True),
            x="crime_count",
            y="area_label",
            color="region",
            color_discrete_map=REGION_COLOR_MAP,
            category_orders={"region": ALL_REGIONS},
            orientation="h",
            labels={
                "crime_count": "Reported Crimes",
                "area_label": "Community Area",
                "region": "Chicago Region",
            },
        )
        fig_areas.update_layout(height=440, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_areas, use_container_width=True)

with right_col:
    st.subheader("What Are the Most Common Types of Crime Reported?")
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
        fig_types.update_layout(height=440, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_types, use_container_width=True)

# --- Row 2: Crime Type vs Region Correlation & Total Crimes vs Population ---
left_col2, right_col2 = st.columns(2)

with left_col2:
    st.subheader("Correlation Between Crime Types and City Regions")
    matrix_df = query_crime_region_matrix(where_sql, params)
    if matrix_df.empty:
        st.info("Not enough regional data for the current filter selection.")
    else:
        top_8_types = (
            matrix_df.groupby("primary_type")["crime_count"]
            .sum()
            .nlargest(8)
            .index.tolist()
        )
        sub_matrix = matrix_df[matrix_df["primary_type"].isin(top_8_types)]
        pivot = sub_matrix.pivot_table(
            index="primary_type",
            columns="region",
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
            labels={"x": "Chicago Region", "y": "Crime Type", "color": "% of Region Crimes"},
        )
        fig_heatmap.update_layout(height=415, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_heatmap, use_container_width=True)

with right_col2:
    st.subheader("Total Number of Crimes vs. Population")
    pop_granularity = st.radio(
        "Aggregation Level",
        options=["By Region (9 Chicago Sides)", "By Community Area (77 Areas)"],
        horizontal=True,
        label_visibility="collapsed",
    )
    area_pop_df = query_area_crime_counts(where_sql, params)
    if selected_regions:
        area_pop_df = area_pop_df[area_pop_df["region"].isin(selected_regions)]
    if selected_areas:
        area_pop_df = area_pop_df[area_pop_df["community_area"].isin(selected_areas)]

    if pop_granularity == "By Region (9 Chicago Sides)":
        plot_df = (
            area_pop_df.groupby("region", as_index=False)
            .agg(
                population=("population", "sum"),
                crime_count=("crime_count", "sum"),
            )
        )
        plot_df["crimes_per_1k"] = (plot_df["crime_count"] / plot_df["population"]) * 1000.0
        hover_name_col = "region"
        hover_cols = {
            "crime_count": ":,",
            "population": ":,",
            "crimes_per_1k": ":.1f",
        }
    else:
        plot_df = area_pop_df.copy()
        plot_df["area_label"] = plot_df["community_area"].map(format_community_area)
        hover_name_col = "area_label"
        hover_cols = {
            "region": True,
            "crime_count": ":,",
            "population": ":,",
            "crimes_per_1k": ":.1f",
        }

    if len(plot_df) < 2:
        st.info("Select at least two regions or community areas to compare total crimes vs. population.")
    else:
        corr = plot_df["population"].corr(plot_df["crime_count"])
        r_squared = corr ** 2 if pd.notna(corr) else float("nan")
        st.caption(
            (
                f"Population vs. total crimes correlation: **r = {corr:.2f}** (**R² = {r_squared:.2f}**) | "
                if pd.notna(corr)
                else "Population vs. total crimes correlation: N/A | "
            )
            + "Population: U.S. Census / CMAP Community Data Snapshots"
        )
        fig_pop = px.scatter(
            plot_df,
            x="population",
            y="crime_count",
            color="region",
            color_discrete_map=REGION_COLOR_MAP,
            category_orders={"region": ALL_REGIONS},
            hover_name=hover_name_col,
            hover_data=hover_cols,
            labels={
                "population": "Population (residents)",
                "crime_count": "Total Reported Crimes",
                "crimes_per_1k": "Crimes per 1,000 Residents",
                "region": "Chicago Region",
            },
        )
        fig_pop.update_traces(
            marker=dict(
                size=13 if pop_granularity == "By Region (9 Chicago Sides)" else 9,
                opacity=0.9,
            )
        )
        if plot_df["population"].nunique() > 1:
            slope, intercept = np.polyfit(
                plot_df["population"], plot_df["crime_count"], 1
            )
            x_vals = np.linspace(
                plot_df["population"].min(),
                plot_df["population"].max(),
                50,
            )
            fig_pop.add_trace(
                go.Scatter(
                    x=x_vals,
                    y=slope * x_vals + intercept,
                    mode="lines",
                    name="Linear Fit (OLS)",
                    line=dict(color="rgba(120, 120, 120, 0.7)", dash="dash"),
                )
            )
        fig_pop.update_layout(height=385, margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig_pop, use_container_width=True)

# --- Row 3: Crime Patterns Over Time by Region ---
st.subheader("How Have Crime Patterns Changed Over Time in Different Regions?")
trends_df = query_trends_by_region(where_sql, params)
if trends_df.empty:
    st.info("No time-series records available for the current filters.")
else:
    fig_trends = px.line(
        trends_df,
        x="period",
        y="crime_count",
        color="region",
        color_discrete_map=REGION_COLOR_MAP,
        category_orders={"region": ALL_REGIONS},
        markers=True,
        labels={
            "period": "Month",
            "crime_count": "Reported Crimes",
            "region": "Chicago Region",
        },
    )
    fig_trends.update_layout(height=380, margin=dict(l=10, r=10, t=10, b=10))
    month_start = start_date.replace(day=1)
    if month_start < end_date.replace(day=1):
        fig_trends.update_xaxes(range=[str(month_start), str(end_date)])
    st.plotly_chart(fig_trends, use_container_width=True)

# --- Row 4: Incident Map & Interactive Table ---
st.subheader("Recent Incident Locations & Records Explorer")
sample_df = query_sample_records(where_sql, params)
map_col, table_col = st.columns([1.15, 1.15])

with map_col:
    geo_df = sample_df.dropna(subset=["latitude", "longitude"]).copy()
    geo_df = geo_df[
        geo_df["latitude"].between(41.6, 42.1)
        & geo_df["longitude"].between(-88.0, -87.5)
    ]
    if geo_df.empty:
        st.info("No valid coordinates in the current filtered slice.")
    else:
        geo_df["date_str"] = pd.to_datetime(geo_df["date"]).dt.strftime("%Y-%m-%d %H:%M")
        map_kwargs = dict(
            lat="latitude",
            lon="longitude",
            color="primary_type",
            color_discrete_sequence=px.colors.qualitative.Light24,
            hover_name="primary_type",
            hover_data={
                "description": True,
                "case_number": True,
                "date_str": True,
                "block": True,
                "community_area_name": True,
                "arrest": True,
                "latitude": False,
                "longitude": False,
                "primary_type": False,
            },
            zoom=9.6,
            center={"lat": 41.835, "lon": -87.685},
            labels={
                "primary_type": "Crime Type",
                "description": "Description",
                "case_number": "Case #",
                "date_str": "Occurred At",
                "block": "Block",
                "community_area_name": "Community Area",
                "arrest": "Arrest",
            },
        )
        if hasattr(px, "scatter_map"):
            fig_map = px.scatter_map(geo_df, map_style="carto-darkmatter", **map_kwargs)
        else:
            fig_map = px.scatter_mapbox(geo_df, mapbox_style="carto-darkmatter", **map_kwargs)

        fig_map.update_traces(marker=dict(size=8, opacity=0.9))
        fig_map.update_layout(
            height=380,
            margin=dict(l=0, r=0, t=0, b=0),
            legend=dict(
                title="Crime Type",
                bgcolor="rgba(17, 24, 39, 0.85)",
                font=dict(color="#F9FAFB"),
            ),
        )
        st.plotly_chart(fig_map, use_container_width=True)

with table_col:
    if sample_df.empty:
        st.info("No records match the current filters.")
    else:
        display_df = sample_df[
            [
                "case_number",
                "date",
                "primary_type",
                "description",
                "community_area_name",
                "region",
                "arrest",
            ]
        ].rename(columns={"community_area_name": "community_area"})
        st.dataframe(display_df, use_container_width=True, height=380)

st.divider()

# --- Data Sources & Reference Metadata ---
st.subheader("Data Sources & Reference Metadata")
st.markdown(
    """
    * **Primary Crime Records (PostgreSQL Star Schema):** [City of Chicago Data Portal — Crimes (2001 to Present)](https://data.cityofchicago.org/Public-Safety/Crimes-2001-to-Present/ijzp-q8t2) (`ijzp-q8t2`), ingested via the ETL pipeline into `fact_crime`, `dim_crime_type`, `dim_location`, and `dim_date`.
    * **Community Area Names & Boundaries (1–77):** [City of Chicago Data Portal — Boundaries: Community Areas](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Community-Areas/igwz-8jzy) (`igwz-8jzy`).
    * **Community Area Population Figures:** U.S. Census Bureau & [Chicago Metropolitan Agency for Planning (CMAP) Community Data Snapshots](https://www.cmap.illinois.gov/data/community-snapshots), joined on official Community Area ID (`1–77`) to compare total reported crimes against population.
    * **Chicago Geographic Regions (9 Sides):** City of Chicago / Chicago Department of Public Health (CDPH) standard regional grouping (*Central, Far North Side, Far Southeast Side, Far Southwest Side, North Side, Northwest Side, South Side, Southwest Side, West Side*).
    """
)