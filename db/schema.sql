CREATE TABLE IF NOT EXISTS dim_crime_type (
    crime_type_key SERIAL PRIMARY KEY,
    iucr CHAR(4) NOT NULL UNIQUE,
    primary_type VARCHAR(50) NOT NULL,
    description VARCHAR(100) NOT NULL,
    fbi_code VARCHAR(5) NOT NULL
);

CREATE TABLE IF NOT EXISTS dim_location (
    location_key SERIAL PRIMARY KEY,
    block VARCHAR(50) NOT NULL,
    location_description VARCHAR(60),
    beat SMALLINT,
    district SMALLINT,
    ward SMALLINT,
    community_area SMALLINT,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key DATE PRIMARY KEY,
    year SMALLINT NOT NULL,
    quarter SMALLINT NOT NULL,
    month SMALLINT NOT NULL,
    day SMALLINT NOT NULL,
    day_of_week SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_crime (
    crime_id BIGINT PRIMARY KEY,
    case_number VARCHAR(20) NOT NULL,
    occurred_at TIMESTAMP NOT NULL,
    updated_on TIMESTAMP NOT NULL,
    date_key DATE REFERENCES dim_date(date_key),
    location_key INTEGER REFERENCES dim_location(location_key),
    crime_type_key INTEGER REFERENCES dim_crime_type(crime_type_key),
    arrest BOOLEAN NOT NULL,
    domestic BOOLEAN NOT NULL
);


CREATE UNIQUE INDEX IF NOT EXISTS unique_location
ON dim_location (
    block,
    location_description,
    beat,
    district,
    ward,
    community_area,
    latitude,
    longitude
) NULLS NOT DISTINCT;
