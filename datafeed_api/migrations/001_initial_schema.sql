-- Fight Judge AI Data Feed - Initial Schema
-- Financial-grade sports data syndication system
-- Version: 1.0.0

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ========================================
-- EVENTS TABLE
-- ========================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    venue TEXT,
    promotion TEXT,
    start_time_utc TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_code ON events(code);
CREATE INDEX idx_events_start_time ON events(start_time_utc);

COMMENT ON TABLE events IS 'MMA events/fight cards';
COMMENT ON COLUMN events.code IS 'Unique event code (e.g., PFC50)';

-- ========================================
-- FIGHTERS TABLE
-- ========================================
CREATE TABLE fighters (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    nickname TEXT,
    country TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_fighters_name ON fighters(last_name, first_name);

COMMENT ON TABLE fighters IS 'Fighter profiles';

-- ========================================
-- FIGHTS TABLE
-- ========================================
CREATE TABLE fights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    bout_order INT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    red_fighter_id UUID NOT NULL REFERENCES fighters(id),
    blue_fighter_id UUID NOT NULL REFERENCES fighters(id),
    scheduled_rounds INT NOT NULL DEFAULT 3,
    weight_class TEXT,
    rule_set TEXT DEFAULT 'Unified Rules',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT different_fighters CHECK (red_fighter_id != blue_fighter_id)
);

CREATE INDEX idx_fights_event ON fights(event_id);
CREATE INDEX idx_fights_code ON fights(code);
CREATE INDEX idx_fights_bout_order ON fights(event_id, bout_order);

COMMENT ON TABLE fights IS 'Individual fights within events';
COMMENT ON COLUMN fights.code IS 'Unique fight code (e.g., PFC50-F3)';
COMMENT ON COLUMN fights.bout_order IS 'Fight order on card (1 = first fight)';

-- ========================================
-- ROUND_STATE TABLE (MONOTONIC SEQUENCING)
-- ========================================
CREATE TABLE round_state (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL REFERENCES fights(id) ON DELETE CASCADE,
    round INT NOT NULL CHECK (round >= 1),
    ts_ms BIGINT NOT NULL,
    seq BIGINT NOT NULL,
    
    -- Red corner stats
    red_strikes INT DEFAULT 0,
    red_sig_strikes INT DEFAULT 0,
    red_knockdowns INT DEFAULT 0,
    red_control_sec INT DEFAULT 0,
    red_ai_damage NUMERIC(5,2) DEFAULT 0.0,
    red_ai_win_prob NUMERIC(4,3) DEFAULT 0.5,
    
    -- Blue corner stats
    blue_strikes INT DEFAULT 0,
    blue_sig_strikes INT DEFAULT 0,
    blue_knockdowns INT DEFAULT 0,
    blue_control_sec INT DEFAULT 0,
    blue_ai_damage NUMERIC(5,2) DEFAULT 0.0,
    blue_ai_win_prob NUMERIC(4,3) DEFAULT 0.5,
    
    -- Lock state
    round_locked BOOLEAN DEFAULT FALSE,
    
    -- Audit fields
    created_at TIMESTAMPTZ DEFAULT NOW(),
    source TEXT DEFAULT 'fightjudge.ai',
    
    -- Monotonic constraint: seq must always increase
    CONSTRAINT unique_fight_seq UNIQUE (fight_id, seq)
);

-- Critical indexes for real-time performance
CREATE INDEX idx_round_state_fight ON round_state(fight_id);
CREATE INDEX idx_round_state_seq ON round_state(fight_id, seq DESC);
CREATE INDEX idx_round_state_round ON round_state(fight_id, round, seq DESC);
CREATE INDEX idx_round_state_ts ON round_state(ts_ms DESC);

COMMENT ON TABLE round_state IS 'Real-time fight state snapshots with monotonic sequencing';
COMMENT ON COLUMN round_state.seq IS 'Monotonically increasing sequence number for sportsbook safety';
COMMENT ON COLUMN round_state.ts_ms IS 'Timestamp in milliseconds since epoch';
COMMENT ON COLUMN round_state.round_locked IS 'True when round is finalized and immutable';

-- ========================================
-- FIGHT_RESULTS TABLE
-- ========================================
CREATE TABLE fight_results (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL REFERENCES fights(id) ON DELETE CASCADE,
    winner_side TEXT NOT NULL CHECK (winner_side IN ('RED', 'BLUE', 'DRAW', 'NC')),
    method TEXT NOT NULL,
    round INT,
    time TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT one_result_per_fight UNIQUE (fight_id)
);

CREATE INDEX idx_fight_results_fight ON fight_results(fight_id);

COMMENT ON TABLE fight_results IS 'Official fight results';
COMMENT ON COLUMN fight_results.winner_side IS 'RED, BLUE, DRAW, or NC (No Contest)';
COMMENT ON COLUMN fight_results.method IS 'KO, TKO, SUB, UD, SD, MD, etc.';

-- ========================================
-- API_CLIENTS TABLE (AUTHENTICATION)
-- ========================================
CREATE TABLE api_clients (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name TEXT NOT NULL,
    api_key TEXT UNIQUE NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('fantasy.basic', 'fantasy.advanced', 'sportsbook.pro')),
    active BOOLEAN DEFAULT TRUE,
    rate_limit_per_min INT DEFAULT 1000,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used_at TIMESTAMPTZ
);

CREATE INDEX idx_api_clients_key ON api_clients(api_key) WHERE active = TRUE;

COMMENT ON TABLE api_clients IS 'API key management and scoping';
COMMENT ON COLUMN api_clients.scope IS 'fantasy.basic, fantasy.advanced, or sportsbook.pro';

-- ========================================
-- AUDIT_LOG TABLE (SPORTSBOOK COMPLIANCE)
-- ========================================
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID REFERENCES fights(id),
    action TEXT NOT NULL,
    actor TEXT,
    changes JSONB,
    ts_ms BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_log_fight ON audit_log(fight_id);
CREATE INDEX idx_audit_log_ts ON audit_log(ts_ms DESC);

COMMENT ON TABLE audit_log IS 'Immutable audit trail for regulatory compliance';

-- ========================================
-- TRIGGERS FOR UPDATED_AT
-- ========================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_events_updated_at BEFORE UPDATE ON events
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fighters_updated_at BEFORE UPDATE ON fighters
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_fights_updated_at BEFORE UPDATE ON fights
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- SEQUENCE GENERATOR FUNCTION
-- ========================================
CREATE SEQUENCE round_state_seq_global START 1;

CREATE OR REPLACE FUNCTION get_next_seq(p_fight_id UUID)
RETURNS BIGINT AS $$
DECLARE
    next_seq BIGINT;
BEGIN
    -- Get max seq for this fight and increment
    SELECT COALESCE(MAX(seq), 0) + 1 INTO next_seq
    FROM round_state
    WHERE fight_id = p_fight_id;
    
    RETURN next_seq;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION get_next_seq IS 'Generates monotonically increasing sequence numbers per fight';

-- ========================================
-- ROW LEVEL SECURITY (RLS) - Optional
-- ========================================
-- Enable RLS if using Supabase auth
-- ALTER TABLE round_state ENABLE ROW LEVEL SECURITY;
-- CREATE POLICY "Public read access" ON round_state FOR SELECT USING (true);

-- ========================================
-- SAMPLE DATA FUNCTION
-- ========================================
CREATE OR REPLACE FUNCTION seed_sample_data()
RETURNS VOID AS $$
DECLARE
    v_event_id UUID;
    v_fight_id UUID;
    v_red_fighter_id UUID;
    v_blue_fighter_id UUID;
    v_api_key_basic UUID;
    v_api_key_advanced UUID;
BEGIN
    -- Create sample event
    INSERT INTO events (code, name, venue, promotion, start_time_utc)
    VALUES ('PFC50', 'Pankration FC 50: Legends Clash', 'T-Mobile Arena', 'Pankration FC', NOW() + INTERVAL '7 days')
    RETURNING id INTO v_event_id;
    
    -- Create sample fighters
    INSERT INTO fighters (first_name, last_name, nickname, country)
    VALUES ('John', 'Striker', 'The Hammer', 'USA')
    RETURNING id INTO v_red_fighter_id;
    
    INSERT INTO fighters (first_name, last_name, nickname, country)
    VALUES ('Carlos', 'Grappler', 'El Pulpo', 'Brazil')
    RETURNING id INTO v_blue_fighter_id;
    
    -- Create sample fight
    INSERT INTO fights (event_id, bout_order, code, red_fighter_id, blue_fighter_id, scheduled_rounds, weight_class)
    VALUES (v_event_id, 3, 'PFC50-F3', v_red_fighter_id, v_blue_fighter_id, 3, 'Welterweight')
    RETURNING id INTO v_fight_id;
    
    -- Create API keys
    INSERT INTO api_clients (name, api_key, scope, active)
    VALUES 
        ('Fantasy App Basic', 'test_fantasy_basic_' || gen_random_uuid()::text, 'fantasy.basic', TRUE),
        ('Fantasy App Advanced', 'test_fantasy_advanced_' || gen_random_uuid()::text, 'fantasy.advanced', TRUE),
        ('Sportsbook Pro', 'test_sportsbook_pro_' || gen_random_uuid()::text, 'sportsbook.pro', TRUE);
    
    RAISE NOTICE 'Sample data created successfully';
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION seed_sample_data IS 'Creates sample event, fighters, fight, and API keys for testing';

-- Run seed function (optional - comment out for production)
-- SELECT seed_sample_data();
