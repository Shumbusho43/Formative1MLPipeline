-- =============================================================
--  Beijing Air Quality — MySQL Schema (from Task 2)
--  Usage:  mysql -u <user> -p < database/schema_mysql.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS beijing_air_quality
    DEFAULT CHARACTER SET utf8mb4;
USE beijing_air_quality;

-- Table 1: stations — master record for each of the 12 monitoring stations.
CREATE TABLE IF NOT EXISTS stations (
    station_id    INT           NOT NULL AUTO_INCREMENT,
    station_name  VARCHAR(50)   NOT NULL,
    city          VARCHAR(100)  NOT NULL DEFAULT 'Beijing',
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (station_id),
    UNIQUE KEY uq_station_name (station_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 2: readings — one row per station per hour.
CREATE TABLE IF NOT EXISTS readings (
    reading_id      BIGINT        NOT NULL AUTO_INCREMENT,
    station_id      INT           NOT NULL,
    timestamp       DATETIME      NOT NULL,
    pm25            FLOAT                  COMMENT 'PM2.5  μg/m³',
    pm10            FLOAT                  COMMENT 'PM10   μg/m³',
    so2             FLOAT                  COMMENT 'SO2    μg/m³',
    no2             FLOAT                  COMMENT 'NO2    μg/m³',
    co              FLOAT                  COMMENT 'CO     μg/m³',
    o3              FLOAT                  COMMENT 'O3     μg/m³',
    temp            FLOAT                  COMMENT 'Temperature   °C',
    pres            FLOAT                  COMMENT 'Air pressure   hPa',
    dewp            FLOAT                  COMMENT 'Dew-point temperature  °C',
    rain            FLOAT                  COMMENT 'Precipitation  mm/h',
    wind_direction  VARCHAR(10)            COMMENT 'Compass direction (e.g. NNW)',
    wind_speed      FLOAT                  COMMENT 'Wind speed  m/s',
    PRIMARY KEY (reading_id),
    UNIQUE KEY uq_station_ts (station_id, timestamp),
    CONSTRAINT fk_readings_station
        FOREIGN KEY (station_id) REFERENCES stations (station_id)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    INDEX idx_timestamp   (timestamp),
    INDEX idx_station_ts  (station_id, timestamp)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 3: pollutant_reference — WHO 2021 guideline values per pollutant.
CREATE TABLE IF NOT EXISTS pollutant_reference (
    pollutant_id       INT           NOT NULL AUTO_INCREMENT,
    code               VARCHAR(20)   NOT NULL,
    full_name          VARCHAR(100)  NOT NULL,
    unit               VARCHAR(20)   NOT NULL,
    who_annual_limit   FLOAT                  COMMENT 'WHO annual mean guideline (μg/m³)',
    who_24h_limit      FLOAT                  COMMENT 'WHO 24-hour mean guideline (μg/m³)',
    description        TEXT,
    PRIMARY KEY (pollutant_id),
    UNIQUE KEY uq_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
