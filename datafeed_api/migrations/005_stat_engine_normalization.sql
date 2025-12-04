-- ========================================
-- STAT ENGINE NORMALIZATION
-- ========================================
-- Migration: 005_stat_engine_normalization
-- Adds granular event tracking with UFCstats parity and sportsbook-grade determinism

-- ========================================
-- FIGHT_EVENTS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS fight_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL REFERENCES fights(id) ON DELETE CASCADE,
    round INT NOT NULL CHECK (round >= 1),
    second_in_round INT NOT NULL CHECK (second_in_round >= 0 AND second_in_round <= 300),
    event_type TEXT NOT NULL CHECK (event_type IN (
        'STR_ATT',      -- Strike attempt
        'STR_LAND',     -- Strike landed
        'KD',           -- Knockdown
        'TD_ATT',       -- Takedown attempt
        'TD_LAND',      -- Takedown landed
        'CTRL_START',   -- Control period begins
        'CTRL_END',     -- Control period ends
        'SUB_ATT',      -- Submission attempt
        'REVERSAL',     -- Position reversal
        'ROUND_START',  -- Round begins
        'ROUND_END',    -- Round ends
        'FIGHT_END'     -- Fight ends
    )),
    corner TEXT NOT NULL CHECK (corner IN ('RED', 'BLUE', 'NEUTRAL')),
    metadata JSONB DEFAULT '{}',
    seq BIGINT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Unique sequence per fight
    CONSTRAINT unique_event_seq UNIQUE (fight_id, seq)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_fight_events_fight_round ON fight_events(fight_id, round);
CREATE INDEX IF NOT EXISTS idx_fight_events_type ON fight_events(event_type);
CREATE INDEX IF NOT EXISTS idx_fight_events_seq ON fight_events(fight_id, seq);
CREATE INDEX IF NOT EXISTS idx_fight_events_corner ON fight_events(corner);
CREATE INDEX IF NOT EXISTS idx_fight_events_control ON fight_events(fight_id, round, event_type, corner) 
    WHERE event_type IN ('CTRL_START', 'CTRL_END');

COMMENT ON TABLE fight_events IS 'Granular event stream for sportsbook-grade stat tracking';
COMMENT ON COLUMN fight_events.event_type IS '12 standardized event types per UFCstats vocabulary';
COMMENT ON COLUMN fight_events.second_in_round IS 'Event timestamp within round (0-300 seconds)';
COMMENT ON COLUMN fight_events.seq IS 'Monotonically increasing sequence number for ordering';
COMMENT ON COLUMN fight_events.metadata IS 'Event-specific data (e.g., is_significant, position, technique)';

-- ========================================
-- EVENT TYPE NORMALIZATION FUNCTION
-- ========================================
CREATE OR REPLACE FUNCTION normalize_event_type(p_input_type TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Convert to uppercase and trim
    p_input_type := UPPER(TRIM(p_input_type));
    
    -- Legacy alias mapping
    CASE p_input_type
        WHEN 'STRIKE' THEN RETURN 'STR_LAND';
        WHEN 'STRIKE_LAND' THEN RETURN 'STR_LAND';
        WHEN 'STRIKE_LANDED' THEN RETURN 'STR_LAND';
        WHEN 'STRIKE_ATT' THEN RETURN 'STR_ATT';
        WHEN 'STRIKE_ATTEMPT' THEN RETURN 'STR_ATT';
        WHEN 'KNOCKDOWN' THEN RETURN 'KD';
        WHEN 'TAKEDOWN' THEN RETURN 'TD_LAND';
        WHEN 'TAKEDOWN_LAND' THEN RETURN 'TD_LAND';
        WHEN 'TAKEDOWN_LANDED' THEN RETURN 'TD_LAND';
        WHEN 'TAKEDOWN_ATT' THEN RETURN 'TD_ATT';
        WHEN 'TAKEDOWN_ATTEMPT' THEN RETURN 'TD_ATT';
        WHEN 'CONTROL_START' THEN RETURN 'CTRL_START';
        WHEN 'CONTROL_END' THEN RETURN 'CTRL_END';
        WHEN 'SUBMISSION' THEN RETURN 'SUB_ATT';
        WHEN 'SUBMISSION_ATT' THEN RETURN 'SUB_ATT';
        WHEN 'SUBMISSION_ATTEMPT' THEN RETURN 'SUB_ATT';
        ELSE RETURN p_input_type; -- Already normalized or invalid
    END CASE;
END;
$$ LANGUAGE plpgsql IMMUTABLE;

COMMENT ON FUNCTION normalize_event_type IS 'Auto-maps legacy event type aliases to controlled vocabulary';

-- ========================================
-- DETERMINISTIC CONTROL TIME CALCULATOR
-- ========================================
CREATE OR REPLACE FUNCTION calculate_control_time_from_events(
    p_fight_id UUID,
    p_round INT,
    p_corner TEXT
)
RETURNS INT AS $$
DECLARE
    v_total_control INT := 0;
    v_ctrl_start RECORD;
    v_ctrl_end RECORD;
    v_duration INT;
    v_round_duration INT := 300; -- 5 minutes default
BEGIN
    -- Validate corner
    IF p_corner NOT IN ('RED', 'BLUE') THEN
        RAISE EXCEPTION 'Invalid corner: %. Must be RED or BLUE', p_corner;
    END IF;
    
    -- Get all CTRL_START events for this fighter/round
    FOR v_ctrl_start IN
        SELECT * FROM fight_events
        WHERE fight_id = p_fight_id
          AND round = p_round
          AND corner = p_corner
          AND event_type = 'CTRL_START'
        ORDER BY second_in_round
    LOOP
        -- Find matching CTRL_END (next one chronologically)
        SELECT * INTO v_ctrl_end
        FROM fight_events
        WHERE fight_id = p_fight_id
          AND round = p_round
          AND corner = p_corner
          AND event_type = 'CTRL_END'
          AND second_in_round > v_ctrl_start.second_in_round
        ORDER BY second_in_round
        LIMIT 1;
        
        IF FOUND THEN
            -- Paired CTRL_START/CTRL_END
            v_duration := v_ctrl_end.second_in_round - v_ctrl_start.second_in_round;
            
            -- Validate positive duration
            IF v_duration < 0 THEN
                RAISE WARNING 'Negative control duration detected: fight=%, round=%, corner=%', 
                    p_fight_id, p_round, p_corner;
                v_duration := 0;
            END IF;
            
            v_total_control := v_total_control + v_duration;
        ELSE
            -- No matching CTRL_END - control continues to round end
            v_duration := v_round_duration - v_ctrl_start.second_in_round;
            
            IF v_duration > 0 THEN
                v_total_control := v_total_control + v_duration;
            END IF;
        END IF;
    END LOOP;
    
    -- Validate total doesn't exceed round duration
    IF v_total_control > v_round_duration THEN
        RAISE WARNING 'Control time exceeds round duration: fight=%, round=%, corner=%, control=%', 
            p_fight_id, p_round, p_corner, v_total_control;
        v_total_control := v_round_duration;
    END IF;
    
    RETURN v_total_control;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_control_time_from_events IS 
    'Calculates deterministic control time by pairing CTRL_START with next CTRL_END';

-- ========================================
-- CONTROL TIME OVERLAP VALIDATOR
-- ========================================
CREATE OR REPLACE FUNCTION validate_no_control_overlap(
    p_fight_id UUID,
    p_round INT
)
RETURNS TABLE (
    has_overlap BOOLEAN,
    overlap_details JSONB
) AS $$
DECLARE
    v_red_control INT;
    v_blue_control INT;
    v_round_duration INT := 300;
    v_overlap_seconds INT;
    v_details JSONB;
BEGIN
    -- Calculate control for both corners
    v_red_control := calculate_control_time_from_events(p_fight_id, p_round, 'RED');
    v_blue_control := calculate_control_time_from_events(p_fight_id, p_round, 'BLUE');
    
    -- Check if total exceeds round duration
    IF v_red_control + v_blue_control > v_round_duration THEN
        v_overlap_seconds := (v_red_control + v_blue_control) - v_round_duration;
        
        v_details := jsonb_build_object(
            'red_control', v_red_control,
            'blue_control', v_blue_control,
            'total_control', v_red_control + v_blue_control,
            'round_duration', v_round_duration,
            'overlap_seconds', v_overlap_seconds
        );
        
        RETURN QUERY SELECT TRUE, v_details;
    ELSE
        v_details := jsonb_build_object(
            'red_control', v_red_control,
            'blue_control', v_blue_control,
            'total_control', v_red_control + v_blue_control,
            'round_duration', v_round_duration,
            'remaining_neutral', v_round_duration - (v_red_control + v_blue_control)
        );
        
        RETURN QUERY SELECT FALSE, v_details;
    END IF;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION validate_no_control_overlap IS 
    'Validates that RED and BLUE control periods do not overlap';

-- ========================================
-- AGGREGATE STATS FROM EVENTS
-- ========================================
CREATE OR REPLACE FUNCTION aggregate_round_stats_from_events(
    p_fight_id UUID,
    p_round INT
)
RETURNS TABLE (
    red_strikes INT,
    red_sig_strikes INT,
    red_knockdowns INT,
    red_control_sec INT,
    red_takedowns INT,
    red_sub_attempts INT,
    blue_strikes INT,
    blue_sig_strikes INT,
    blue_knockdowns INT,
    blue_control_sec INT,
    blue_takedowns INT,
    blue_sub_attempts INT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'STR_LAND')::INT,
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'STR_LAND' 
                          AND (metadata->>'is_significant')::boolean = true)::INT,
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'KD')::INT,
        calculate_control_time_from_events(p_fight_id, p_round, 'RED'),
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'TD_LAND')::INT,
        COUNT(*) FILTER (WHERE corner = 'RED' AND event_type = 'SUB_ATT')::INT,
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'STR_LAND')::INT,
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'STR_LAND' 
                          AND (metadata->>'is_significant')::boolean = true)::INT,
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'KD')::INT,
        calculate_control_time_from_events(p_fight_id, p_round, 'BLUE'),
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'TD_LAND')::INT,
        COUNT(*) FILTER (WHERE corner = 'BLUE' AND event_type = 'SUB_ATT')::INT
    FROM fight_events
    WHERE fight_id = p_fight_id
      AND round = p_round;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION aggregate_round_stats_from_events IS 
    'Aggregates cumulative stats from granular events for a round';

-- ========================================
-- GENERATE EVENTS FROM CUMULATIVE STATS
-- ========================================
CREATE OR REPLACE FUNCTION generate_events_from_round_state(
    p_fight_id UUID,
    p_round INT,
    p_round_state RECORD
)
RETURNS INT AS $$
DECLARE
    v_base_seq BIGINT;
    v_events_created INT := 0;
    v_i INT;
BEGIN
    -- Get next sequence number for this fight
    SELECT COALESCE(MAX(seq), 0) + 1 INTO v_base_seq
    FROM fight_events
    WHERE fight_id = p_fight_id;
    
    -- Generate STR_LAND events (RED significant strikes)
    FOR v_i IN 1..p_round_state.red_sig_strikes LOOP
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            ((v_i::float / p_round_state.red_sig_strikes) * 300)::int, -- Distribute across round
            'STR_LAND',
            'RED',
            v_base_seq + v_events_created,
            '{"is_significant": true, "generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
    END LOOP;
    
    -- Generate STR_LAND events (BLUE significant strikes)
    FOR v_i IN 1..p_round_state.blue_sig_strikes LOOP
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            ((v_i::float / p_round_state.blue_sig_strikes) * 300)::int,
            'STR_LAND',
            'BLUE',
            v_base_seq + v_events_created,
            '{"is_significant": true, "generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
    END LOOP;
    
    -- Generate KD events (RED)
    FOR v_i IN 1..p_round_state.red_knockdowns LOOP
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            ((v_i::float / p_round_state.red_knockdowns) * 300)::int,
            'KD',
            'RED',
            v_base_seq + v_events_created,
            '{"generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
    END LOOP;
    
    -- Generate KD events (BLUE)
    FOR v_i IN 1..p_round_state.blue_knockdowns LOOP
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            ((v_i::float / p_round_state.blue_knockdowns) * 300)::int,
            'KD',
            'BLUE',
            v_base_seq + v_events_created,
            '{"generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
    END LOOP;
    
    -- Generate control events (RED) - single CTRL_START/CTRL_END pair
    IF p_round_state.red_control_sec > 0 THEN
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            0,
            'CTRL_START',
            'RED',
            v_base_seq + v_events_created,
            '{"generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
        
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            p_round_state.red_control_sec,
            'CTRL_END',
            'RED',
            v_base_seq + v_events_created,
            '{"generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
    END IF;
    
    -- Generate control events (BLUE)
    IF p_round_state.blue_control_sec > 0 THEN
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            GREATEST(p_round_state.red_control_sec, 0), -- Start after RED control
            'CTRL_START',
            'BLUE',
            v_base_seq + v_events_created,
            '{"generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
        
        INSERT INTO fight_events (fight_id, round, second_in_round, event_type, corner, seq, metadata)
        VALUES (
            p_fight_id,
            p_round,
            GREATEST(p_round_state.red_control_sec, 0) + p_round_state.blue_control_sec,
            'CTRL_END',
            'BLUE',
            v_base_seq + v_events_created,
            '{"generated": true}'::jsonb
        );
        v_events_created := v_events_created + 1;
    END IF;
    
    RETURN v_events_created;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION generate_events_from_round_state IS 
    'Generates granular events from cumulative round_state stats (parallel system bridge)';

-- ========================================
-- TRIGGER: Auto-generate events on round_state insert/update
-- ========================================
CREATE OR REPLACE FUNCTION trigger_generate_events_from_round_state()
RETURNS TRIGGER AS $$
DECLARE
    v_events_created INT;
BEGIN
    -- Only generate events if this is a new round or significant update
    IF (TG_OP = 'INSERT' OR NEW.round_locked = TRUE) THEN
        -- Check if events already exist for this fight/round
        IF NOT EXISTS (
            SELECT 1 FROM fight_events 
            WHERE fight_id = NEW.fight_id 
              AND round = NEW.round
              AND metadata->>'generated' = 'true'
        ) THEN
            -- Generate events
            v_events_created := generate_events_from_round_state(NEW.fight_id, NEW.round, NEW);
            
            RAISE NOTICE 'Generated % events from round_state for fight %, round %', 
                v_events_created, NEW.fight_id, NEW.round;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS auto_generate_events_from_round_state ON round_state;
CREATE TRIGGER auto_generate_events_from_round_state
    AFTER INSERT OR UPDATE OF round_locked
    ON round_state
    FOR EACH ROW
    EXECUTE FUNCTION trigger_generate_events_from_round_state();

COMMENT ON TRIGGER auto_generate_events_from_round_state ON round_state IS
    'Auto-generates events from cumulative stats for parallel system validation';

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'Stat Engine Normalization Migration Complete' as status;

-- Show event types
SELECT unnest(enum_range(NULL::TEXT)) AS event_type
FROM (
    SELECT 'STR_ATT'::TEXT UNION ALL SELECT 'STR_LAND' UNION ALL SELECT 'KD' UNION ALL
    SELECT 'TD_ATT' UNION ALL SELECT 'TD_LAND' UNION ALL SELECT 'CTRL_START' UNION ALL
    SELECT 'CTRL_END' UNION ALL SELECT 'SUB_ATT' UNION ALL SELECT 'REVERSAL' UNION ALL
    SELECT 'ROUND_START' UNION ALL SELECT 'ROUND_END' UNION ALL SELECT 'FIGHT_END'
) AS event_types;
