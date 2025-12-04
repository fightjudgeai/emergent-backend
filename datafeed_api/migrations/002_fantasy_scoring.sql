-- ========================================
-- FANTASY SCORING SYSTEM
-- ========================================
-- Migration: 002_fantasy_scoring
-- Adds fantasy league scoring and sportsbook market support

-- ========================================
-- FANTASY_SCORING_PROFILES TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS fantasy_scoring_profiles (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    config JSONB NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE fantasy_scoring_profiles IS 'Fantasy scoring profile configurations';
COMMENT ON COLUMN fantasy_scoring_profiles.id IS 'Profile ID (e.g., fantasy.basic, sportsbook.pro)';
COMMENT ON COLUMN fantasy_scoring_profiles.config IS 'Scoring weights and rules as JSON';

-- ========================================
-- FANTASY_FIGHT_STATS TABLE
-- ========================================
CREATE TABLE IF NOT EXISTS fantasy_fight_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    fight_id UUID NOT NULL REFERENCES fights(id) ON DELETE CASCADE,
    fighter_id UUID NOT NULL REFERENCES fighters(id) ON DELETE CASCADE,
    profile_id TEXT NOT NULL REFERENCES fantasy_scoring_profiles(id),
    fantasy_points NUMERIC(10,2) NOT NULL DEFAULT 0.0,
    breakdown JSONB NOT NULL DEFAULT '{}',
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Ensure one stats record per fighter per profile per fight
    CONSTRAINT unique_fighter_profile_per_fight UNIQUE (fight_id, fighter_id, profile_id)
);

CREATE INDEX IF NOT EXISTS idx_fantasy_stats_fight ON fantasy_fight_stats(fight_id);
CREATE INDEX IF NOT EXISTS idx_fantasy_stats_fighter ON fantasy_fight_stats(fighter_id);
CREATE INDEX IF NOT EXISTS idx_fantasy_stats_profile ON fantasy_fight_stats(profile_id);

COMMENT ON TABLE fantasy_fight_stats IS 'Computed fantasy points per fighter per fight per profile';
COMMENT ON COLUMN fantasy_fight_stats.fantasy_points IS 'Total fantasy points scored';
COMMENT ON COLUMN fantasy_fight_stats.breakdown IS 'Point breakdown by stat type';

-- ========================================
-- AUTO-UPDATE TRIGGER
-- ========================================
CREATE OR REPLACE FUNCTION update_fantasy_stats_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_fantasy_stats_updated_at ON fantasy_fight_stats;
CREATE TRIGGER update_fantasy_stats_updated_at 
    BEFORE UPDATE ON fantasy_fight_stats
    FOR EACH ROW 
    EXECUTE FUNCTION update_fantasy_stats_timestamp();

-- ========================================
-- SEED FANTASY SCORING PROFILES
-- ========================================

-- Profile 1: fantasy.basic
-- Simple scoring for casual fantasy leagues
INSERT INTO fantasy_scoring_profiles (id, name, config) 
VALUES (
    'fantasy.basic',
    'Fantasy Basic',
    '{
        "description": "Basic fantasy scoring for casual leagues",
        "weights": {
            "sig_strike": 0.5,
            "knockdown": 5.0,
            "takedown": 2.0,
            "control_minute": 1.0,
            "submission_attempt": 3.0
        },
        "bonuses": {
            "win_bonus": 10.0,
            "finish_bonus": 15.0,
            "ko_bonus": 5.0,
            "submission_bonus": 5.0
        },
        "version": "1.0"
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- Profile 2: fantasy.advanced
-- Advanced scoring with AI metrics
INSERT INTO fantasy_scoring_profiles (id, name, config) 
VALUES (
    'fantasy.advanced',
    'Fantasy Advanced',
    '{
        "description": "Advanced fantasy scoring with AI-weighted metrics",
        "weights": {
            "sig_strike": 0.6,
            "knockdown": 6.0,
            "takedown": 2.5,
            "control_minute": 1.5,
            "submission_attempt": 4.0,
            "ai_damage_multiplier": 0.1,
            "ai_control_multiplier": 0.05
        },
        "bonuses": {
            "win_bonus": 15.0,
            "finish_bonus": 20.0,
            "ko_bonus": 8.0,
            "submission_bonus": 8.0,
            "dominant_round_bonus": 3.0
        },
        "thresholds": {
            "dominant_damage_threshold": 15.0,
            "dominant_control_threshold": 180
        },
        "version": "1.0"
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- Profile 3: sportsbook.pro
-- Sportsbook-grade scoring with strict accounting
INSERT INTO fantasy_scoring_profiles (id, name, config) 
VALUES (
    'sportsbook.pro',
    'Sportsbook Pro',
    '{
        "description": "Sportsbook-grade scoring for market settlement",
        "weights": {
            "sig_strike": 0.8,
            "knockdown": 10.0,
            "takedown": 3.0,
            "control_minute": 2.0,
            "submission_attempt": 5.0,
            "strike_accuracy_multiplier": 0.02,
            "defense_multiplier": 0.01
        },
        "bonuses": {
            "win_bonus": 25.0,
            "finish_bonus": 35.0,
            "ko_bonus": 15.0,
            "submission_bonus": 15.0,
            "dominant_round_bonus": 5.0,
            "clean_sweep_bonus": 10.0
        },
        "penalties": {
            "point_deduction": -5.0,
            "foul": -3.0
        },
        "thresholds": {
            "dominant_damage_threshold": 20.0,
            "dominant_control_threshold": 240,
            "clean_sweep_rounds": 3
        },
        "market_settlement": {
            "min_rounds_for_decision": 3,
            "judge_score_weight": 0.3
        },
        "version": "1.0"
    }'::jsonb
) ON CONFLICT (id) DO NOTHING;

-- ========================================
-- HELPER FUNCTION: Calculate Fantasy Points
-- ========================================
CREATE OR REPLACE FUNCTION calculate_fantasy_points(
    p_fight_id UUID,
    p_fighter_id UUID,
    p_profile_id TEXT
)
RETURNS TABLE (
    fantasy_points NUMERIC,
    breakdown JSONB
) AS $$
DECLARE
    v_profile JSONB;
    v_weights JSONB;
    v_bonuses JSONB;
    v_total_points NUMERIC := 0.0;
    v_breakdown JSONB := '{}';
    v_sig_strikes INT := 0;
    v_knockdowns INT := 0;
    v_control_sec INT := 0;
    v_is_winner BOOLEAN := FALSE;
    v_fight_result RECORD;
    v_corner TEXT;
BEGIN
    -- Get profile config
    SELECT config INTO v_profile 
    FROM fantasy_scoring_profiles 
    WHERE id = p_profile_id;
    
    IF v_profile IS NULL THEN
        RAISE EXCEPTION 'Profile % not found', p_profile_id;
    END IF;
    
    v_weights := v_profile->'weights';
    v_bonuses := v_profile->'bonuses';
    
    -- Determine fighter corner (RED or BLUE)
    SELECT 
        CASE 
            WHEN red_fighter_id = p_fighter_id THEN 'RED'
            WHEN blue_fighter_id = p_fighter_id THEN 'BLUE'
            ELSE NULL
        END INTO v_corner
    FROM fights
    WHERE id = p_fight_id;
    
    IF v_corner IS NULL THEN
        RAISE EXCEPTION 'Fighter % not in fight %', p_fighter_id, p_fight_id;
    END IF;
    
    -- Aggregate stats from all rounds
    SELECT 
        COALESCE(SUM(CASE WHEN v_corner = 'RED' THEN red_sig_strikes ELSE blue_sig_strikes END), 0),
        COALESCE(SUM(CASE WHEN v_corner = 'RED' THEN red_knockdowns ELSE blue_knockdowns END), 0),
        COALESCE(SUM(CASE WHEN v_corner = 'RED' THEN red_control_sec ELSE blue_control_sec END), 0)
    INTO v_sig_strikes, v_knockdowns, v_control_sec
    FROM round_state
    WHERE fight_id = p_fight_id;
    
    -- Calculate base points
    v_total_points := v_total_points + (v_sig_strikes * (v_weights->>'sig_strike')::numeric);
    v_breakdown := jsonb_set(v_breakdown, '{sig_strikes}', to_jsonb(v_sig_strikes * (v_weights->>'sig_strike')::numeric));
    
    v_total_points := v_total_points + (v_knockdowns * (v_weights->>'knockdown')::numeric);
    v_breakdown := jsonb_set(v_breakdown, '{knockdowns}', to_jsonb(v_knockdowns * (v_weights->>'knockdown')::numeric));
    
    v_total_points := v_total_points + ((v_control_sec / 60.0) * (v_weights->>'control_minute')::numeric);
    v_breakdown := jsonb_set(v_breakdown, '{control}', to_jsonb((v_control_sec / 60.0) * (v_weights->>'control_minute')::numeric));
    
    -- Check for win
    SELECT * INTO v_fight_result
    FROM fight_results
    WHERE fight_id = p_fight_id;
    
    IF FOUND THEN
        v_is_winner := (v_fight_result.winner_side = v_corner);
        
        IF v_is_winner THEN
            v_total_points := v_total_points + (v_bonuses->>'win_bonus')::numeric;
            v_breakdown := jsonb_set(v_breakdown, '{win_bonus}', to_jsonb((v_bonuses->>'win_bonus')::numeric));
            
            -- Finish bonus
            IF v_fight_result.method IN ('KO', 'TKO', 'SUB', 'Submission') THEN
                v_total_points := v_total_points + (v_bonuses->>'finish_bonus')::numeric;
                v_breakdown := jsonb_set(v_breakdown, '{finish_bonus}', to_jsonb((v_bonuses->>'finish_bonus')::numeric));
                
                -- Specific finish bonuses
                IF v_fight_result.method IN ('KO', 'TKO') AND v_bonuses ? 'ko_bonus' THEN
                    v_total_points := v_total_points + (v_bonuses->>'ko_bonus')::numeric;
                    v_breakdown := jsonb_set(v_breakdown, '{ko_bonus}', to_jsonb((v_bonuses->>'ko_bonus')::numeric));
                END IF;
                
                IF v_fight_result.method IN ('SUB', 'Submission') AND v_bonuses ? 'submission_bonus' THEN
                    v_total_points := v_total_points + (v_bonuses->>'submission_bonus')::numeric;
                    v_breakdown := jsonb_set(v_breakdown, '{submission_bonus}', to_jsonb((v_bonuses->>'submission_bonus')::numeric));
                END IF;
            END IF;
        END IF;
    END IF;
    
    -- Add summary stats to breakdown
    v_breakdown := jsonb_set(v_breakdown, '{raw_stats}', jsonb_build_object(
        'sig_strikes', v_sig_strikes,
        'knockdowns', v_knockdowns,
        'control_seconds', v_control_sec,
        'is_winner', v_is_winner
    ));
    
    RETURN QUERY SELECT v_total_points, v_breakdown;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION calculate_fantasy_points IS 'Calculate fantasy points for a fighter in a fight using a specific profile';

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'Fantasy Scoring Migration Complete' as status;
SELECT id, name FROM fantasy_scoring_profiles ORDER BY id;
