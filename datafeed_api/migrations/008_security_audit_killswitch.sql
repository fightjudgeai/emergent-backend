-- ========================================
-- SECURITY, AUDIT TRAILS & KILL-SWITCH
-- ========================================
-- Migration: 008_security_audit_killswitch
-- Adds comprehensive audit logging and emergency controls

-- ========================================
-- SECURITY AUDIT LOG TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS security_audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type TEXT NOT NULL,  -- 'api_call', 'websocket_connect', 'settlement', 'fantasy_compute', 'auth_failure', 'admin_action'
    client_id UUID REFERENCES api_clients(id) ON DELETE SET NULL,
    user_id TEXT,  -- Optional internal user ID for admin actions
    action TEXT NOT NULL,  -- Specific action taken
    resource_type TEXT,  -- 'fight', 'market', 'fantasy', 'client', etc.
    resource_id TEXT,
    details JSONB,  -- Additional context
    ip_address TEXT,
    user_agent TEXT,
    status TEXT NOT NULL,  -- 'success', 'failure', 'blocked'
    error_message TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    -- Indexes for fast queries
    INDEX idx_audit_event_type (event_type),
    INDEX idx_audit_client_id (client_id),
    INDEX idx_audit_timestamp (timestamp DESC),
    INDEX idx_audit_status (status),
    INDEX idx_audit_resource (resource_type, resource_id)
);

COMMENT ON TABLE security_audit_log IS 'Comprehensive security and compliance audit trail';

-- ========================================
-- SETTLEMENT TRACKING (Prevent Duplicates)
-- ========================================
CREATE TABLE IF NOT EXISTS settlement_executions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_id UUID NOT NULL,
    fight_id UUID NOT NULL,
    execution_hash TEXT UNIQUE NOT NULL,  -- Hash to prevent duplicates
    executed_by TEXT,
    executed_at TIMESTAMPTZ DEFAULT NOW(),
    result_payload JSONB,
    status TEXT DEFAULT 'completed',
    
    INDEX idx_settlement_market (market_id),
    INDEX idx_settlement_fight (fight_id),
    INDEX idx_settlement_hash (execution_hash)
);

COMMENT ON TABLE settlement_executions IS 'Tracks settlement executions to prevent duplicates';

-- ========================================
-- FANTASY COMPUTATION TRACKING
-- ========================================
CREATE TABLE IF NOT EXISTS fantasy_computations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL,
    profile_id TEXT NOT NULL,
    computation_hash TEXT UNIQUE NOT NULL,
    client_id UUID REFERENCES api_clients(id),
    result JSONB,
    computed_at TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_fantasy_fight (fight_id),
    INDEX idx_fantasy_profile (profile_id),
    INDEX idx_fantasy_client (client_id)
);

COMMENT ON TABLE fantasy_computations IS 'Tracks fantasy computations for audit and caching';

-- ========================================
-- SYSTEM STATUS (Kill-Switch)
-- ========================================
CREATE TABLE IF NOT EXISTS system_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component TEXT UNIQUE NOT NULL,  -- 'api', 'websocket', 'fantasy', 'markets', 'settlement'
    status TEXT NOT NULL DEFAULT 'active',  -- 'active', 'maintenance', 'emergency_stop'
    reason TEXT,
    updated_by TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    CHECK (status IN ('active', 'maintenance', 'emergency_stop'))
);

-- Initialize system components
INSERT INTO system_status (component, status) VALUES
    ('api', 'active'),
    ('websocket', 'active'),
    ('fantasy', 'active'),
    ('markets', 'active'),
    ('settlement', 'active')
ON CONFLICT (component) DO NOTHING;

COMMENT ON TABLE system_status IS 'Emergency kill-switch for system components';

-- ========================================
-- FUNCTION: Log Security Event
-- ========================================
CREATE OR REPLACE FUNCTION log_security_event(
    p_event_type TEXT,
    p_client_id UUID,
    p_action TEXT,
    p_resource_type TEXT DEFAULT NULL,
    p_resource_id TEXT DEFAULT NULL,
    p_details JSONB DEFAULT NULL,
    p_ip_address TEXT DEFAULT NULL,
    p_user_agent TEXT DEFAULT NULL,
    p_status TEXT DEFAULT 'success',
    p_error_message TEXT DEFAULT NULL
)
RETURNS UUID AS $$
DECLARE
    v_log_id UUID;
BEGIN
    INSERT INTO security_audit_log (
        event_type,
        client_id,
        action,
        resource_type,
        resource_id,
        details,
        ip_address,
        user_agent,
        status,
        error_message
    ) VALUES (
        p_event_type,
        p_client_id,
        p_action,
        p_resource_type,
        p_resource_id,
        p_details,
        p_ip_address,
        p_user_agent,
        p_status,
        p_error_message
    ) RETURNING id INTO v_log_id;
    
    RETURN v_log_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_security_event IS 'Log security event for audit trail';

-- ========================================
-- FUNCTION: Check System Status (Kill-Switch)
-- ========================================
CREATE OR REPLACE FUNCTION check_system_status(p_component TEXT)
RETURNS TABLE (
    is_active BOOLEAN,
    status TEXT,
    reason TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        s.status = 'active' AS is_active,
        s.status,
        s.reason
    FROM system_status s
    WHERE s.component = p_component;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_system_status IS 'Check if system component is active (kill-switch check)';

-- ========================================
-- FUNCTION: Prevent Duplicate Settlement
-- ========================================
CREATE OR REPLACE FUNCTION check_settlement_duplicate(
    p_market_id UUID,
    p_fight_id UUID
)
RETURNS BOOLEAN AS $$
DECLARE
    v_count INT;
BEGIN
    SELECT COUNT(*) INTO v_count
    FROM settlement_executions
    WHERE market_id = p_market_id
      AND status = 'completed';
    
    RETURN v_count > 0;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION check_settlement_duplicate IS 'Check if settlement already executed for market';

-- ========================================
-- FUNCTION: Record Settlement Execution
-- ========================================
CREATE OR REPLACE FUNCTION record_settlement_execution(
    p_market_id UUID,
    p_fight_id UUID,
    p_executed_by TEXT,
    p_result_payload JSONB
)
RETURNS UUID AS $$
DECLARE
    v_execution_id UUID;
    v_hash TEXT;
BEGIN
    -- Generate hash from market_id and fight_id
    v_hash := MD5(p_market_id::TEXT || p_fight_id::TEXT);
    
    -- Check for duplicate
    IF check_settlement_duplicate(p_market_id, p_fight_id) THEN
        RAISE EXCEPTION 'Settlement already executed for market %', p_market_id;
    END IF;
    
    -- Record execution
    INSERT INTO settlement_executions (
        market_id,
        fight_id,
        execution_hash,
        executed_by,
        result_payload,
        status
    ) VALUES (
        p_market_id,
        p_fight_id,
        v_hash,
        p_executed_by,
        p_result_payload,
        'completed'
    ) RETURNING id INTO v_execution_id;
    
    -- Log to audit trail
    PERFORM log_security_event(
        'settlement',
        NULL,
        'market_settlement',
        'market',
        p_market_id::TEXT,
        jsonb_build_object('fight_id', p_fight_id, 'result', p_result_payload),
        NULL,
        NULL,
        'success',
        NULL
    );
    
    RETURN v_execution_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION record_settlement_execution IS 'Record settlement execution and prevent duplicates';

-- ========================================
-- VIEW: Security Events Summary
-- ========================================
CREATE OR REPLACE VIEW security_events_summary AS
SELECT
    event_type,
    COUNT(*) AS total_events,
    COUNT(*) FILTER (WHERE status = 'success') AS successful,
    COUNT(*) FILTER (WHERE status = 'failure') AS failed,
    COUNT(*) FILTER (WHERE status = 'blocked') AS blocked,
    MAX(timestamp) AS last_event
FROM security_audit_log
WHERE timestamp > NOW() - INTERVAL '24 hours'
GROUP BY event_type;

COMMENT ON VIEW security_events_summary IS '24-hour security events summary';

-- ========================================
-- VIEW: Failed Auth Attempts
-- ========================================
CREATE OR REPLACE VIEW failed_auth_attempts AS
SELECT
    ip_address,
    client_id,
    COUNT(*) AS attempt_count,
    MAX(timestamp) AS last_attempt,
    array_agg(DISTINCT error_message) AS error_messages
FROM security_audit_log
WHERE event_type = 'auth_failure'
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY ip_address, client_id
HAVING COUNT(*) > 5
ORDER BY COUNT(*) DESC;

COMMENT ON VIEW failed_auth_attempts IS 'Suspicious auth failure patterns (>5 in 1 hour)';

-- ========================================
-- ADMIN ACTIONS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS admin_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_user TEXT NOT NULL,
    action_type TEXT NOT NULL,  -- 'create_client', 'suspend_client', 'change_tier', 'emergency_stop'
    target_client_id UUID REFERENCES api_clients(id),
    old_value JSONB,
    new_value JSONB,
    reason TEXT,
    ip_address TEXT,
    timestamp TIMESTAMPTZ DEFAULT NOW(),
    
    INDEX idx_admin_user (admin_user),
    INDEX idx_admin_action_type (action_type),
    INDEX idx_admin_timestamp (timestamp DESC)
);

COMMENT ON TABLE admin_actions IS 'Audit trail for admin actions';

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'Security, Audit & Kill-Switch Migration Complete' as status;

-- Show table structures
SELECT 
    table_name,
    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = t.table_name) as column_count
FROM information_schema.tables t
WHERE table_name IN ('security_audit_log', 'settlement_executions', 'system_status', 'admin_actions')
ORDER BY table_name;
