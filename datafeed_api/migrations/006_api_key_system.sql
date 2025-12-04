-- ========================================
-- API KEY ACCESS SYSTEM
-- ========================================
-- Migration: 006_api_key_system
-- Adds comprehensive API key management, RBAC, and rate limiting

-- ========================================
-- DROP EXISTING TABLE IF EXISTS
-- ========================================
-- Drop old api_clients table if it exists (we're replacing it)
DROP TABLE IF EXISTS api_usage_logs CASCADE;
DROP TABLE IF EXISTS api_clients CASCADE;

-- ========================================
-- API CLIENTS TABLE
-- ========================================
CREATE TABLE api_clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN (
        'public',
        'dev',
        'fantasy.basic',
        'fantasy.advanced',
        'sportsbook.pro',
        'promotion.enterprise'
    )),
    api_key TEXT UNIQUE NOT NULL,
    status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK (status IN (
        'ACTIVE',
        'SUSPENDED',
        'REVOKED'
    )),
    rate_limit_per_minute INT NOT NULL DEFAULT 60,
    rate_limit_per_hour INT DEFAULT 3600,
    rate_limit_per_day INT DEFAULT 50000,
    scope TEXT, -- Legacy field for backward compatibility
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ,
    notes TEXT,
    
    -- Indexes
    CONSTRAINT api_clients_name_key UNIQUE (name)
);

CREATE INDEX idx_api_clients_api_key ON api_clients(api_key);
CREATE INDEX idx_api_clients_tier ON api_clients(tier);
CREATE INDEX idx_api_clients_status ON api_clients(status);

COMMENT ON TABLE api_clients IS 'API client credentials and tier management';
COMMENT ON COLUMN api_clients.tier IS 'Access tier: public, dev, fantasy.basic, fantasy.advanced, sportsbook.pro, promotion.enterprise';
COMMENT ON COLUMN api_clients.status IS 'Client status: ACTIVE, SUSPENDED, REVOKED';
COMMENT ON COLUMN api_clients.rate_limit_per_minute IS 'Max requests per minute';

-- ========================================
-- API USAGE LOGS TABLE
-- ========================================
CREATE TABLE api_usage_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES api_clients(id) ON DELETE CASCADE,
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    response_time_ms INT,
    ip_address TEXT,
    user_agent TEXT,
    
    -- Indexes for rate limiting queries
    CONSTRAINT fk_client FOREIGN KEY (client_id) REFERENCES api_clients(id)
);

CREATE INDEX idx_usage_logs_client_timestamp ON api_usage_logs(client_id, timestamp DESC);
CREATE INDEX idx_usage_logs_endpoint ON api_usage_logs(endpoint);
CREATE INDEX idx_usage_logs_timestamp ON api_usage_logs(timestamp);

COMMENT ON TABLE api_usage_logs IS 'API usage tracking for rate limiting and analytics';

-- ========================================
-- FUNCTION: Generate Secure API Key
-- ========================================
CREATE OR REPLACE FUNCTION generate_api_key(prefix TEXT DEFAULT 'FJAI')
RETURNS TEXT AS $$
DECLARE
    random_part TEXT;
    api_key TEXT;
BEGIN
    -- Generate cryptographically secure random string
    random_part := encode(gen_random_bytes(24), 'base64');
    
    -- Remove URL-unsafe characters
    random_part := replace(random_part, '/', '_');
    random_part := replace(random_part, '+', '-');
    random_part := replace(random_part, '=', '');
    
    -- Format: PREFIX_RANDOMPART
    api_key := prefix || '_' || random_part;
    
    RETURN api_key;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION generate_api_key IS 'Generate cryptographically secure API key with prefix';

-- ========================================
-- FUNCTION: Check Rate Limit
-- ========================================
CREATE OR REPLACE FUNCTION check_rate_limit(
    p_client_id UUID,
    p_period TEXT, -- 'minute', 'hour', 'day'
    p_limit INT
)
RETURNS TABLE (
    is_allowed BOOLEAN,
    current_count INT,
    limit_value INT,
    reset_at TIMESTAMPTZ
) AS $$
DECLARE
    v_count INT;
    v_cutoff TIMESTAMPTZ;
    v_reset TIMESTAMPTZ;
BEGIN
    -- Determine cutoff time based on period
    CASE p_period
        WHEN 'minute' THEN
            v_cutoff := NOW() - INTERVAL '1 minute';
            v_reset := DATE_TRUNC('minute', NOW()) + INTERVAL '1 minute';
        WHEN 'hour' THEN
            v_cutoff := NOW() - INTERVAL '1 hour';
            v_reset := DATE_TRUNC('hour', NOW()) + INTERVAL '1 hour';
        WHEN 'day' THEN
            v_cutoff := NOW() - INTERVAL '1 day';
            v_reset := DATE_TRUNC('day', NOW()) + INTERVAL '1 day';
        ELSE
            RAISE EXCEPTION 'Invalid period: %. Must be minute, hour, or day', p_period;
    END CASE;
    
    -- Count requests in the time window
    SELECT COUNT(*) INTO v_count
    FROM api_usage_logs
    WHERE client_id = p_client_id
      AND timestamp > v_cutoff;
    
    -- Return result
    RETURN QUERY
    SELECT 
        v_count < p_limit AS is_allowed,
        v_count AS current_count,
        p_limit AS limit_value,
        v_reset AS reset_at;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_rate_limit IS 'Check if client has exceeded rate limit for given period';

-- ========================================
-- FUNCTION: Get Tier Access Permissions
-- ========================================
CREATE OR REPLACE FUNCTION get_tier_permissions(p_tier TEXT)
RETURNS TABLE (
    tier TEXT,
    can_access_public BOOLEAN,
    can_access_fantasy BOOLEAN,
    can_access_advanced_fantasy BOOLEAN,
    can_access_markets BOOLEAN,
    can_access_events BOOLEAN,
    can_access_websocket BOOLEAN,
    can_access_enterprise BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p_tier AS tier,
        TRUE AS can_access_public, -- All tiers can access public
        p_tier IN ('fantasy.basic', 'fantasy.advanced', 'sportsbook.pro', 'promotion.enterprise') AS can_access_fantasy,
        p_tier IN ('fantasy.advanced', 'sportsbook.pro', 'promotion.enterprise') AS can_access_advanced_fantasy,
        p_tier IN ('sportsbook.pro', 'promotion.enterprise') AS can_access_markets,
        p_tier IN ('sportsbook.pro', 'promotion.enterprise') AS can_access_events,
        p_tier IN ('fantasy.advanced', 'sportsbook.pro', 'promotion.enterprise') AS can_access_websocket,
        p_tier = 'promotion.enterprise' AS can_access_enterprise;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_tier_permissions IS 'Get access permissions for a given tier';

-- ========================================
-- TRIGGER: Update updated_at
-- ========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER api_clients_updated_at
    BEFORE UPDATE ON api_clients
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- SEED DATA: Demo API Keys
-- ========================================
-- Create demo API keys for testing
INSERT INTO api_clients (name, tier, api_key, rate_limit_per_minute, rate_limit_per_hour, rate_limit_per_day, notes)
VALUES
    ('Public Demo', 'public', 'FJAI_PUBLIC_DEMO_001', 60, 3600, 50000, 'Demo public access'),
    ('Dev Demo', 'dev', 'FJAI_DEV_DEMO_001', 120, 7200, 100000, 'Demo developer access'),
    ('Fantasy Basic Demo', 'fantasy.basic', 'FJAI_FANTASY_BASIC_001', 180, 10800, 150000, 'Demo basic fantasy access'),
    ('Fantasy Advanced Demo', 'fantasy.advanced', 'FJAI_FANTASY_ADV_001', 300, 18000, 250000, 'Demo advanced fantasy access'),
    ('Sportsbook Pro Demo', 'sportsbook.pro', 'FJAI_SPORTSBOOK_001', 600, 36000, 500000, 'Demo sportsbook access'),
    ('Enterprise Demo', 'promotion.enterprise', 'FJAI_ENTERPRISE_001', 1200, 72000, 1000000, 'Demo enterprise access');

-- ========================================
-- VIEW: API Usage Summary
-- ========================================
CREATE OR REPLACE VIEW api_usage_summary AS
SELECT
    c.id AS client_id,
    c.name AS client_name,
    c.tier,
    c.status,
    COUNT(l.id) AS total_requests,
    COUNT(l.id) FILTER (WHERE l.timestamp > NOW() - INTERVAL '1 minute') AS requests_last_minute,
    COUNT(l.id) FILTER (WHERE l.timestamp > NOW() - INTERVAL '1 hour') AS requests_last_hour,
    COUNT(l.id) FILTER (WHERE l.timestamp > NOW() - INTERVAL '1 day') AS requests_last_day,
    AVG(l.response_time_ms) AS avg_response_time_ms,
    MAX(l.timestamp) AS last_request_at
FROM api_clients c
LEFT JOIN api_usage_logs l ON c.id = l.client_id
GROUP BY c.id, c.name, c.tier, c.status;

COMMENT ON VIEW api_usage_summary IS 'Real-time API usage summary per client';

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'API Key System Migration Complete' as status;

-- Show demo API keys
SELECT 
    name,
    tier,
    api_key,
    status,
    rate_limit_per_minute
FROM api_clients
ORDER BY 
    CASE tier
        WHEN 'public' THEN 1
        WHEN 'dev' THEN 2
        WHEN 'fantasy.basic' THEN 3
        WHEN 'fantasy.advanced' THEN 4
        WHEN 'sportsbook.pro' THEN 5
        WHEN 'promotion.enterprise' THEN 6
    END;
