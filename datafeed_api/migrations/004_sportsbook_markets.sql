-- ========================================
-- SPORTSBOOK MARKETS SYSTEM
-- ========================================
-- Migration: 004_sportsbook_markets
-- Adds market management and auto-settlement

-- ========================================
-- MARKETS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS markets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL REFERENCES fights(id) ON DELETE CASCADE,
    market_type TEXT NOT NULL,
    params JSONB NOT NULL DEFAULT '{}',
    status TEXT NOT NULL DEFAULT 'OPEN' CHECK (status IN ('OPEN', 'SUSPENDED', 'SETTLED', 'CANCELLED')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure unique market type per fight
    CONSTRAINT unique_market_per_fight UNIQUE (fight_id, market_type)
);

CREATE INDEX IF NOT EXISTS idx_markets_fight ON markets(fight_id);
CREATE INDEX IF NOT EXISTS idx_markets_type ON markets(market_type);
CREATE INDEX IF NOT EXISTS idx_markets_status ON markets(status);

COMMENT ON TABLE markets IS 'Sportsbook markets for betting on fight outcomes';
COMMENT ON COLUMN markets.market_type IS 'Type of market: WINNER, TOTAL_SIG_STRIKES, KD_OVER_UNDER, SUB_ATT_OVER_UNDER, etc.';
COMMENT ON COLUMN markets.params IS 'Market-specific parameters (e.g., over/under line, odds)';
COMMENT ON COLUMN markets.status IS 'OPEN=accepting bets, SUSPENDED=temporarily closed, SETTLED=result determined, CANCELLED=void';

-- ========================================
-- MARKET_SETTLEMENTS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS market_settlements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    market_id UUID NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    result_payload JSONB NOT NULL,
    settled_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- One settlement per market
    CONSTRAINT one_settlement_per_market UNIQUE (market_id)
);

CREATE INDEX IF NOT EXISTS idx_settlements_market ON market_settlements(market_id);
CREATE INDEX IF NOT EXISTS idx_settlements_time ON market_settlements(settled_at);

COMMENT ON TABLE market_settlements IS 'Settlement results for sportsbook markets';
COMMENT ON COLUMN market_settlements.result_payload IS 'Settlement data including winning outcomes and statistics';

-- ========================================
-- AUTO-UPDATE TRIGGER
-- ========================================
CREATE OR REPLACE FUNCTION update_markets_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_markets_updated_at ON markets;
CREATE TRIGGER update_markets_updated_at 
    BEFORE UPDATE ON markets
    FOR EACH ROW 
    EXECUTE FUNCTION update_markets_timestamp();

-- ========================================
-- MARKET SETTLEMENT FUNCTIONS
-- ========================================

-- Function: Settle WINNER market
CREATE OR REPLACE FUNCTION settle_winner_market(p_market_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_market RECORD;
    v_fight_result RECORD;
    v_result JSONB;
BEGIN
    -- Get market
    SELECT * INTO v_market FROM markets WHERE id = p_market_id;
    
    IF NOT FOUND OR v_market.market_type != 'WINNER' THEN
        RAISE EXCEPTION 'Market % not found or not a WINNER market', p_market_id;
    END IF;
    
    -- Get fight result
    SELECT * INTO v_fight_result 
    FROM fight_results 
    WHERE fight_id = v_market.fight_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Fight result not found for market %', p_market_id;
    END IF;
    
    -- Build settlement result
    v_result := jsonb_build_object(
        'market_type', 'WINNER',
        'winner_side', v_fight_result.winner_side,
        'method', v_fight_result.method,
        'round', v_fight_result.round,
        'time', v_fight_result.time,
        'settled_at', NOW()
    );
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Function: Settle TOTAL_SIG_STRIKES market
CREATE OR REPLACE FUNCTION settle_total_sig_strikes_market(p_market_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_market RECORD;
    v_latest_round RECORD;
    v_total_sig_strikes INT;
    v_line NUMERIC;
    v_over_wins BOOLEAN;
    v_result JSONB;
BEGIN
    -- Get market
    SELECT * INTO v_market FROM markets WHERE id = p_market_id;
    
    IF NOT FOUND OR v_market.market_type != 'TOTAL_SIG_STRIKES' THEN
        RAISE EXCEPTION 'Market % not found or not a TOTAL_SIG_STRIKES market', p_market_id;
    END IF;
    
    -- Get line from params
    v_line := (v_market.params->>'line')::numeric;
    
    IF v_line IS NULL THEN
        RAISE EXCEPTION 'No line specified in market params';
    END IF;
    
    -- Get latest round state (cumulative stats)
    SELECT * INTO v_latest_round
    FROM round_state
    WHERE fight_id = v_market.fight_id
    ORDER BY seq DESC
    LIMIT 1;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No round state found for fight';
    END IF;
    
    -- Calculate total sig strikes
    v_total_sig_strikes := v_latest_round.red_sig_strikes + v_latest_round.blue_sig_strikes;
    
    -- Determine winner
    v_over_wins := v_total_sig_strikes > v_line;
    
    -- Build settlement result
    v_result := jsonb_build_object(
        'market_type', 'TOTAL_SIG_STRIKES',
        'line', v_line,
        'actual_total', v_total_sig_strikes,
        'red_sig_strikes', v_latest_round.red_sig_strikes,
        'blue_sig_strikes', v_latest_round.blue_sig_strikes,
        'winning_side', CASE WHEN v_over_wins THEN 'OVER' ELSE 'UNDER' END,
        'settled_at', NOW()
    );
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Function: Settle KD_OVER_UNDER market
CREATE OR REPLACE FUNCTION settle_kd_over_under_market(p_market_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_market RECORD;
    v_latest_round RECORD;
    v_total_knockdowns INT;
    v_line NUMERIC;
    v_over_wins BOOLEAN;
    v_result JSONB;
BEGIN
    -- Get market
    SELECT * INTO v_market FROM markets WHERE id = p_market_id;
    
    IF NOT FOUND OR v_market.market_type != 'KD_OVER_UNDER' THEN
        RAISE EXCEPTION 'Market % not found or not a KD_OVER_UNDER market', p_market_id;
    END IF;
    
    -- Get line from params
    v_line := (v_market.params->>'line')::numeric;
    
    IF v_line IS NULL THEN
        RAISE EXCEPTION 'No line specified in market params';
    END IF;
    
    -- Get latest round state
    SELECT * INTO v_latest_round
    FROM round_state
    WHERE fight_id = v_market.fight_id
    ORDER BY seq DESC
    LIMIT 1;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'No round state found for fight';
    END IF;
    
    -- Calculate total knockdowns
    v_total_knockdowns := v_latest_round.red_knockdowns + v_latest_round.blue_knockdowns;
    
    -- Determine winner
    v_over_wins := v_total_knockdowns > v_line;
    
    -- Build settlement result
    v_result := jsonb_build_object(
        'market_type', 'KD_OVER_UNDER',
        'line', v_line,
        'actual_total', v_total_knockdowns,
        'red_knockdowns', v_latest_round.red_knockdowns,
        'blue_knockdowns', v_latest_round.blue_knockdowns,
        'winning_side', CASE WHEN v_over_wins THEN 'OVER' ELSE 'UNDER' END,
        'settled_at', NOW()
    );
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- Function: Settle SUB_ATT_OVER_UNDER market
-- Note: submission_attempts not in round_state schema yet, using placeholder
CREATE OR REPLACE FUNCTION settle_sub_att_over_under_market(p_market_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_market RECORD;
    v_latest_round RECORD;
    v_total_sub_attempts INT;
    v_line NUMERIC;
    v_over_wins BOOLEAN;
    v_result JSONB;
BEGIN
    -- Get market
    SELECT * INTO v_market FROM markets WHERE id = p_market_id;
    
    IF NOT FOUND OR v_market.market_type != 'SUB_ATT_OVER_UNDER' THEN
        RAISE EXCEPTION 'Market % not found or not a SUB_ATT_OVER_UNDER market', p_market_id;
    END IF;
    
    -- Get line from params
    v_line := (v_market.params->>'line')::numeric;
    
    IF v_line IS NULL THEN
        RAISE EXCEPTION 'No line specified in market params';
    END IF;
    
    -- TODO: Add submission_attempts to round_state schema
    -- For now, using 0 as placeholder
    v_total_sub_attempts := 0;
    
    -- Determine winner
    v_over_wins := v_total_sub_attempts > v_line;
    
    -- Build settlement result
    v_result := jsonb_build_object(
        'market_type', 'SUB_ATT_OVER_UNDER',
        'line', v_line,
        'actual_total', v_total_sub_attempts,
        'winning_side', CASE WHEN v_over_wins THEN 'OVER' ELSE 'UNDER' END,
        'settled_at', NOW(),
        'note', 'submission_attempts not yet tracked in round_state'
    );
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- UNIFIED SETTLEMENT FUNCTION
-- ========================================
CREATE OR REPLACE FUNCTION settle_market(p_market_id UUID)
RETURNS JSONB AS $$
DECLARE
    v_market RECORD;
    v_result JSONB;
BEGIN
    -- Get market
    SELECT * INTO v_market FROM markets WHERE id = p_market_id;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Market % not found', p_market_id;
    END IF;
    
    -- Check if already settled
    IF v_market.status = 'SETTLED' THEN
        RAISE EXCEPTION 'Market % already settled', p_market_id;
    END IF;
    
    -- Route to appropriate settlement function
    CASE v_market.market_type
        WHEN 'WINNER' THEN
            v_result := settle_winner_market(p_market_id);
        WHEN 'TOTAL_SIG_STRIKES' THEN
            v_result := settle_total_sig_strikes_market(p_market_id);
        WHEN 'KD_OVER_UNDER' THEN
            v_result := settle_kd_over_under_market(p_market_id);
        WHEN 'SUB_ATT_OVER_UNDER' THEN
            v_result := settle_sub_att_over_under_market(p_market_id);
        ELSE
            RAISE EXCEPTION 'Unknown market type: %', v_market.market_type;
    END CASE;
    
    -- Insert settlement
    INSERT INTO market_settlements (market_id, result_payload)
    VALUES (p_market_id, v_result);
    
    -- Update market status
    UPDATE markets 
    SET status = 'SETTLED', updated_at = NOW()
    WHERE id = p_market_id;
    
    RETURN v_result;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION settle_market IS 'Settle a market based on fight result and stats';

-- ========================================
-- AUTO-SETTLEMENT TRIGGER
-- ========================================
CREATE OR REPLACE FUNCTION trigger_auto_settle_markets()
RETURNS TRIGGER AS $$
DECLARE
    v_market RECORD;
    v_result JSONB;
BEGIN
    -- Auto-settle all open markets for this fight
    FOR v_market IN 
        SELECT * FROM markets 
        WHERE fight_id = NEW.fight_id 
        AND status = 'OPEN'
    LOOP
        BEGIN
            -- Attempt to settle market
            v_result := settle_market(v_market.id);
            
            RAISE NOTICE 'Auto-settled market % (%) for fight %: %', 
                v_market.id, v_market.market_type, NEW.fight_id, v_result;
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Failed to auto-settle market % (%) for fight %: %', 
                v_market.id, v_market.market_type, NEW.fight_id, SQLERRM;
            
            -- Mark market as suspended on error
            UPDATE markets 
            SET status = 'SUSPENDED', updated_at = NOW()
            WHERE id = v_market.id;
        END;
    END LOOP;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION trigger_auto_settle_markets IS 'Auto-settle markets when fight result is added';

DROP TRIGGER IF EXISTS auto_settle_markets_on_result ON fight_results;
CREATE TRIGGER auto_settle_markets_on_result
    AFTER INSERT OR UPDATE
    ON fight_results
    FOR EACH ROW
    EXECUTE FUNCTION trigger_auto_settle_markets();

COMMENT ON TRIGGER auto_settle_markets_on_result ON fight_results IS
    'Auto-settles all open markets when fight result is finalized';

-- ========================================
-- SEED SAMPLE MARKETS FOR PFC50
-- ========================================

-- Create markets for PFC50-F1
DO $$
DECLARE
    v_fight_id UUID;
BEGIN
    -- Get fight ID
    SELECT id INTO v_fight_id FROM fights WHERE code = 'PFC50-F1';
    
    IF v_fight_id IS NOT NULL THEN
        -- WINNER market
        INSERT INTO markets (fight_id, market_type, params, status)
        VALUES (
            v_fight_id,
            'WINNER',
            '{"red_odds": 1.75, "blue_odds": 2.10}'::jsonb,
            'OPEN'
        ) ON CONFLICT DO NOTHING;
        
        -- TOTAL_SIG_STRIKES market
        INSERT INTO markets (fight_id, market_type, params, status)
        VALUES (
            v_fight_id,
            'TOTAL_SIG_STRIKES',
            '{"line": 50.5, "over_odds": 1.91, "under_odds": 1.91}'::jsonb,
            'OPEN'
        ) ON CONFLICT DO NOTHING;
        
        -- KD_OVER_UNDER market
        INSERT INTO markets (fight_id, market_type, params, status)
        VALUES (
            v_fight_id,
            'KD_OVER_UNDER',
            '{"line": 0.5, "over_odds": 2.50, "under_odds": 1.50}'::jsonb,
            'OPEN'
        ) ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Created sample markets for PFC50-F1';
    END IF;
END $$;

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'Sportsbook Markets Migration Complete' as status;

-- Show created markets
SELECT 
    m.id,
    f.code as fight_code,
    m.market_type,
    m.params,
    m.status
FROM markets m
JOIN fights f ON m.fight_id = f.id
ORDER BY f.code, m.market_type;
