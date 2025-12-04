-- ========================================
-- WEBSOCKET AUTH & USAGE METERING
-- ========================================
-- Migration: 007_websocket_auth_billing
-- Adds JWT token system for WebSocket auth and billing usage tracking

-- ========================================
-- BILLING USAGE TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS billing_usage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES api_clients(id) ON DELETE CASCADE,
    period TEXT NOT NULL,  -- Format: YYYY-MM
    api_calls INT DEFAULT 0,
    websocket_minutes INT DEFAULT 0,
    data_bytes_served BIGINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique constraint: one row per client per period
    CONSTRAINT unique_client_period UNIQUE (client_id, period)
);

CREATE INDEX idx_billing_usage_client_period ON billing_usage(client_id, period);
CREATE INDEX idx_billing_usage_period ON billing_usage(period);

COMMENT ON TABLE billing_usage IS 'Usage metering for billing and revenue forecasting';
COMMENT ON COLUMN billing_usage.period IS 'Billing period in YYYY-MM format';
COMMENT ON COLUMN billing_usage.api_calls IS 'Total API calls in period';
COMMENT ON COLUMN billing_usage.websocket_minutes IS 'Total WebSocket connection minutes';
COMMENT ON COLUMN billing_usage.data_bytes_served IS 'Total data transferred in bytes';

-- ========================================
-- WEBSOCKET SESSIONS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS websocket_sessions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES api_clients(id) ON DELETE CASCADE,
    session_token TEXT UNIQUE NOT NULL,
    event_slug TEXT,
    connected_at TIMESTAMPTZ DEFAULT NOW(),
    disconnected_at TIMESTAMPTZ,
    duration_seconds INT,
    ip_address TEXT,
    user_agent TEXT,
    
    -- Index for active sessions
    CONSTRAINT chk_session_duration CHECK (disconnected_at IS NULL OR disconnected_at > connected_at)
);

CREATE INDEX idx_websocket_sessions_client ON websocket_sessions(client_id);
CREATE INDEX idx_websocket_sessions_token ON websocket_sessions(session_token);
CREATE INDEX idx_websocket_sessions_active ON websocket_sessions(client_id, connected_at) 
    WHERE disconnected_at IS NULL;

COMMENT ON TABLE websocket_sessions IS 'Active and historical WebSocket sessions for billing';

-- ========================================
-- FUNCTION: Update Billing Usage
-- ========================================
CREATE OR REPLACE FUNCTION update_billing_usage(
    p_client_id UUID,
    p_api_calls INT DEFAULT 0,
    p_websocket_minutes INT DEFAULT 0,
    p_data_bytes BIGINT DEFAULT 0
)
RETURNS VOID AS $$
DECLARE
    v_period TEXT;
BEGIN
    -- Get current period (YYYY-MM)
    v_period := TO_CHAR(NOW(), 'YYYY-MM');
    
    -- Insert or update billing usage
    INSERT INTO billing_usage (client_id, period, api_calls, websocket_minutes, data_bytes_served)
    VALUES (p_client_id, v_period, p_api_calls, p_websocket_minutes, p_data_bytes)
    ON CONFLICT (client_id, period)
    DO UPDATE SET
        api_calls = billing_usage.api_calls + p_api_calls,
        websocket_minutes = billing_usage.websocket_minutes + p_websocket_minutes,
        data_bytes_served = billing_usage.data_bytes_served + p_data_bytes,
        updated_at = NOW();
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION update_billing_usage IS 'Increment billing usage counters for a client';

-- ========================================
-- FUNCTION: Calculate WebSocket Duration
-- ========================================
CREATE OR REPLACE FUNCTION calculate_websocket_duration()
RETURNS TRIGGER AS $$
BEGIN
    -- Calculate duration when session ends
    IF NEW.disconnected_at IS NOT NULL AND OLD.disconnected_at IS NULL THEN
        NEW.duration_seconds := EXTRACT(EPOCH FROM (NEW.disconnected_at - NEW.connected_at))::INT;
        
        -- Update billing usage (convert seconds to minutes, round up)
        PERFORM update_billing_usage(
            NEW.client_id,
            0,
            CEIL(NEW.duration_seconds / 60.0)::INT,
            0
        );
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-calculate duration and update billing
CREATE TRIGGER websocket_session_ended
    BEFORE UPDATE ON websocket_sessions
    FOR EACH ROW
    WHEN (NEW.disconnected_at IS NOT NULL AND OLD.disconnected_at IS NULL)
    EXECUTE FUNCTION calculate_websocket_duration();

-- ========================================
-- VIEW: Current Month Billing Summary
-- ========================================
CREATE OR REPLACE VIEW current_month_billing AS
SELECT
    c.id AS client_id,
    c.name AS client_name,
    c.tier,
    b.period,
    b.api_calls,
    b.websocket_minutes,
    b.data_bytes_served,
    ROUND(b.data_bytes_served / 1024.0 / 1024.0, 2) AS data_mb_served,
    ROUND(b.data_bytes_served / 1024.0 / 1024.0 / 1024.0, 3) AS data_gb_served,
    b.updated_at AS last_updated
FROM api_clients c
LEFT JOIN billing_usage b ON c.id = b.client_id
WHERE b.period = TO_CHAR(NOW(), 'YYYY-MM')
ORDER BY b.api_calls DESC NULLS LAST;

COMMENT ON VIEW current_month_billing IS 'Current month billing summary per client';

-- ========================================
-- VIEW: Active WebSocket Sessions
-- ========================================
CREATE OR REPLACE VIEW active_websocket_sessions AS
SELECT
    ws.id,
    ws.client_id,
    c.name AS client_name,
    c.tier,
    ws.event_slug,
    ws.connected_at,
    EXTRACT(EPOCH FROM (NOW() - ws.connected_at))::INT AS seconds_connected,
    ws.ip_address
FROM websocket_sessions ws
JOIN api_clients c ON ws.client_id = c.id
WHERE ws.disconnected_at IS NULL
ORDER BY ws.connected_at DESC;

COMMENT ON VIEW active_websocket_sessions IS 'Currently active WebSocket connections';

-- ========================================
-- FUNCTION: Generate JWT Token (Stub)
-- ========================================
-- Note: JWT generation should be done in application code
-- This is a placeholder to store token mapping

CREATE TABLE IF NOT EXISTS jwt_tokens (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    client_id UUID NOT NULL REFERENCES api_clients(id) ON DELETE CASCADE,
    token_hash TEXT UNIQUE NOT NULL,  -- Store hash, not actual token
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    revoked BOOLEAN DEFAULT FALSE,
    
    -- Index for fast lookup
    CONSTRAINT chk_token_expiry CHECK (expires_at > created_at)
);

CREATE INDEX idx_jwt_tokens_client ON jwt_tokens(client_id);
CREATE INDEX idx_jwt_tokens_hash ON jwt_tokens(token_hash);
CREATE INDEX idx_jwt_tokens_expiry ON jwt_tokens(expires_at) WHERE NOT revoked;

COMMENT ON TABLE jwt_tokens IS 'JWT token tracking for WebSocket authentication';

-- ========================================
-- FUNCTION: Clean Expired Tokens
-- ========================================
CREATE OR REPLACE FUNCTION clean_expired_tokens()
RETURNS INT AS $$
DECLARE
    v_deleted INT;
BEGIN
    DELETE FROM jwt_tokens
    WHERE expires_at < NOW() OR revoked = TRUE;
    
    GET DIAGNOSTICS v_deleted = ROW_COUNT;
    
    RETURN v_deleted;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION clean_expired_tokens IS 'Remove expired and revoked JWT tokens';

-- ========================================
-- INITIAL DATA
-- ========================================
-- Initialize billing usage for existing clients (current month)
INSERT INTO billing_usage (client_id, period)
SELECT id, TO_CHAR(NOW(), 'YYYY-MM')
FROM api_clients
ON CONFLICT (client_id, period) DO NOTHING;

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'WebSocket Auth & Billing Migration Complete' as status;

-- Show billing table structure
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns
WHERE table_name IN ('billing_usage', 'websocket_sessions', 'jwt_tokens')
ORDER BY table_name, ordinal_position;
