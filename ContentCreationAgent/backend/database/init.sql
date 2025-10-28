-- Content Creation Agent - PostgreSQL Initialization Script
-- This script runs automatically when the PostgreSQL container starts for the first time
-- SQLAlchemy will create all application tables via Base.metadata.create_all()

-- ============================================================================
-- Database Setup
-- ============================================================================

-- Ensure the user has a password set (important for external connections)
-- This is redundant with docker-entrypoint but ensures password is properly set
DO $$
BEGIN
    EXECUTE 'ALTER USER agentuser WITH PASSWORD ''changeme''';
END
$$;

-- Update pg_hba.conf to trust localhost connections (development mode)
-- This allows password-free connections from the host machine
COPY (SELECT 'host    all             all             0.0.0.0/0               trust') TO '/tmp/pg_hba_add.conf';
-- Note: The actual pg_hba.conf modification needs to be done via Docker host auth method

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Set timezone
SET timezone = 'UTC';

-- ============================================================================
-- Performance Optimizations
-- ============================================================================

-- Improve JSON query performance
ALTER DATABASE content_agent SET search_path TO public;

-- ============================================================================
-- Initial Data (Optional)
-- ============================================================================

-- Default tenant will be created by the application on first run
-- SQLAlchemy models handle all table creation

-- ============================================================================
-- Verification
-- ============================================================================

-- Log successful initialization
DO $$
BEGIN
    RAISE NOTICE 'Database content_agent initialized successfully';
    RAISE NOTICE 'SQLAlchemy will create application tables on first backend startup';
END
$$;
