-- Initialize OIDC Database
-- This script runs when the PostgreSQL container starts for the first time

-- Create database if it doesn't exist (handled by POSTGRES_DB environment variable)
-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Set timezone
SET timezone = 'UTC';

-- Create additional users/roles if needed
-- CREATE ROLE readonly WITH LOGIN PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE oidc_db TO readonly;
-- GRANT USAGE ON SCHEMA public TO readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO readonly;

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'OIDC Database initialized successfully at %', now();
END $$; 