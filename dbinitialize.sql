-- db/initialize.sql

CREATE TABLE IF NOT EXISTS damage_reports (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    damage_info TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
