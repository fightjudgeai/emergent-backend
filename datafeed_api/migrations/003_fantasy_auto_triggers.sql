-- ========================================
-- FANTASY AUTO-RECOMPUTATION TRIGGERS
-- ========================================
-- Migration: 003_fantasy_auto_triggers
-- Auto-recomputes fantasy stats when round_state changes or locks

-- ========================================
-- TRIGGER FUNCTION: Recompute Fantasy Stats
-- ========================================
CREATE OR REPLACE FUNCTION trigger_recompute_fantasy_stats()
RETURNS TRIGGER AS $$
DECLARE
    v_fight RECORD;
    v_profiles TEXT[];
    v_profile_id TEXT;
    v_red_result JSONB;
    v_blue_result JSONB;
BEGIN
    -- Only recompute when round_state is inserted or updated
    -- AND when round is locked OR it's the latest state
    IF (TG_OP = 'INSERT' OR TG_OP = 'UPDATE') THEN
        -- Get fight details
        SELECT * INTO v_fight
        FROM fights
        WHERE id = NEW.fight_id;
        
        IF NOT FOUND THEN
            RETURN NEW;
        END IF;
        
        -- Get all active profiles
        SELECT array_agg(id) INTO v_profiles
        FROM fantasy_scoring_profiles;
        
        -- Recompute for each profile
        FOREACH v_profile_id IN ARRAY v_profiles
        LOOP
            -- Recompute for RED corner
            BEGIN
                SELECT * INTO v_red_result
                FROM calculate_fantasy_points(
                    NEW.fight_id,
                    v_fight.red_fighter_id,
                    v_profile_id
                );
                
                -- Upsert fantasy stats
                INSERT INTO fantasy_fight_stats (
                    fight_id,
                    fighter_id,
                    profile_id,
                    fantasy_points,
                    breakdown
                ) VALUES (
                    NEW.fight_id,
                    v_fight.red_fighter_id,
                    v_profile_id,
                    (v_red_result->>'fantasy_points')::numeric,
                    v_red_result->'breakdown'
                )
                ON CONFLICT (fight_id, fighter_id, profile_id)
                DO UPDATE SET
                    fantasy_points = EXCLUDED.fantasy_points,
                    breakdown = EXCLUDED.breakdown,
                    updated_at = NOW();
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Error computing RED fantasy stats for profile %: %', v_profile_id, SQLERRM;
            END;
            
            -- Recompute for BLUE corner
            BEGIN
                SELECT * INTO v_blue_result
                FROM calculate_fantasy_points(
                    NEW.fight_id,
                    v_fight.blue_fighter_id,
                    v_profile_id
                );
                
                -- Upsert fantasy stats
                INSERT INTO fantasy_fight_stats (
                    fight_id,
                    fighter_id,
                    profile_id,
                    fantasy_points,
                    breakdown
                ) VALUES (
                    NEW.fight_id,
                    v_fight.blue_fighter_id,
                    v_profile_id,
                    (v_blue_result->>'fantasy_points')::numeric,
                    v_blue_result->'breakdown'
                )
                ON CONFLICT (fight_id, fighter_id, profile_id)
                DO UPDATE SET
                    fantasy_points = EXCLUDED.fantasy_points,
                    breakdown = EXCLUDED.breakdown,
                    updated_at = NOW();
            EXCEPTION WHEN OTHERS THEN
                RAISE NOTICE 'Error computing BLUE fantasy stats for profile %: %', v_profile_id, SQLERRM;
            END;
        END LOOP;
        
        RAISE NOTICE 'Auto-recomputed fantasy stats for fight %', NEW.fight_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION trigger_recompute_fantasy_stats IS 'Auto-recomputes fantasy stats when round_state changes';

-- ========================================
-- TRIGGER: On round_state INSERT/UPDATE
-- ========================================
DROP TRIGGER IF EXISTS auto_recompute_fantasy_on_round_state ON round_state;

CREATE TRIGGER auto_recompute_fantasy_on_round_state
    AFTER INSERT OR UPDATE OF round_locked, red_strikes, blue_strikes, 
                              red_sig_strikes, blue_sig_strikes,
                              red_knockdowns, blue_knockdowns,
                              red_control_sec, blue_control_sec
    ON round_state
    FOR EACH ROW
    WHEN (NEW.round_locked = TRUE OR NEW.seq = (
        SELECT MAX(seq) FROM round_state WHERE fight_id = NEW.fight_id
    ))
    EXECUTE FUNCTION trigger_recompute_fantasy_stats();

COMMENT ON TRIGGER auto_recompute_fantasy_on_round_state ON round_state IS 
    'Auto-recomputes fantasy stats when round locks or latest state updates';

-- ========================================
-- TRIGGER FUNCTION: Recompute on Fight Result
-- ========================================
CREATE OR REPLACE FUNCTION trigger_recompute_fantasy_on_result()
RETURNS TRIGGER AS $$
DECLARE
    v_fight RECORD;
    v_profiles TEXT[];
    v_profile_id TEXT;
    v_red_result JSONB;
    v_blue_result JSONB;
BEGIN
    -- Get fight details
    SELECT * INTO v_fight
    FROM fights
    WHERE id = NEW.fight_id;
    
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;
    
    -- Get all active profiles
    SELECT array_agg(id) INTO v_profiles
    FROM fantasy_scoring_profiles;
    
    -- Recompute for each profile (fight result affects bonuses)
    FOREACH v_profile_id IN ARRAY v_profiles
    LOOP
        -- Recompute for RED corner
        BEGIN
            SELECT * INTO v_red_result
            FROM calculate_fantasy_points(
                NEW.fight_id,
                v_fight.red_fighter_id,
                v_profile_id
            );
            
            INSERT INTO fantasy_fight_stats (
                fight_id,
                fighter_id,
                profile_id,
                fantasy_points,
                breakdown
            ) VALUES (
                NEW.fight_id,
                v_fight.red_fighter_id,
                v_profile_id,
                (v_red_result->>'fantasy_points')::numeric,
                v_red_result->'breakdown'
            )
            ON CONFLICT (fight_id, fighter_id, profile_id)
            DO UPDATE SET
                fantasy_points = EXCLUDED.fantasy_points,
                breakdown = EXCLUDED.breakdown,
                updated_at = NOW();
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error computing RED fantasy stats on result: %', SQLERRM;
        END;
        
        -- Recompute for BLUE corner
        BEGIN
            SELECT * INTO v_blue_result
            FROM calculate_fantasy_points(
                NEW.fight_id,
                v_fight.blue_fighter_id,
                v_profile_id
            );
            
            INSERT INTO fantasy_fight_stats (
                fight_id,
                fighter_id,
                profile_id,
                fantasy_points,
                breakdown
            ) VALUES (
                NEW.fight_id,
                v_fight.blue_fighter_id,
                v_profile_id,
                (v_blue_result->>'fantasy_points')::numeric,
                v_blue_result->'breakdown'
            )
            ON CONFLICT (fight_id, fighter_id, profile_id)
            DO UPDATE SET
                fantasy_points = EXCLUDED.fantasy_points,
                breakdown = EXCLUDED.breakdown,
                updated_at = NOW();
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Error computing BLUE fantasy stats on result: %', SQLERRM;
        END;
    END LOOP;
    
    RAISE NOTICE 'Auto-recomputed fantasy stats on fight result for fight %', NEW.fight_id;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION trigger_recompute_fantasy_on_result IS 'Auto-recomputes fantasy stats when fight result changes';

-- ========================================
-- TRIGGER: On fight_results INSERT/UPDATE
-- ========================================
DROP TRIGGER IF EXISTS auto_recompute_fantasy_on_result ON fight_results;

CREATE TRIGGER auto_recompute_fantasy_on_result
    AFTER INSERT OR UPDATE
    ON fight_results
    FOR EACH ROW
    EXECUTE FUNCTION trigger_recompute_fantasy_on_result();

COMMENT ON TRIGGER auto_recompute_fantasy_on_result ON fight_results IS 
    'Auto-recomputes fantasy stats when fight result is added or updated';

-- ========================================
-- MANUAL RECOMPUTATION FUNCTION
-- ========================================
CREATE OR REPLACE FUNCTION recompute_all_fantasy_stats(
    p_fight_id UUID DEFAULT NULL,
    p_event_code TEXT DEFAULT NULL
)
RETURNS TABLE (
    fight_id UUID,
    fighter_id UUID,
    profile_id TEXT,
    fantasy_points NUMERIC,
    status TEXT
) AS $$
DECLARE
    v_fight_ids UUID[];
    v_fight_id UUID;
    v_fight RECORD;
    v_profiles TEXT[];
    v_profile_id TEXT;
    v_result JSONB;
BEGIN
    -- Determine which fights to recompute
    IF p_fight_id IS NOT NULL THEN
        v_fight_ids := ARRAY[p_fight_id];
    ELSIF p_event_code IS NOT NULL THEN
        SELECT array_agg(f.id) INTO v_fight_ids
        FROM fights f
        JOIN events e ON f.event_id = e.id
        WHERE e.code = p_event_code;
    ELSE
        -- Recompute all fights
        SELECT array_agg(id) INTO v_fight_ids FROM fights;
    END IF;
    
    -- Get all profiles
    SELECT array_agg(id) INTO v_profiles FROM fantasy_scoring_profiles;
    
    -- Recompute for each fight
    FOREACH v_fight_id IN ARRAY v_fight_ids
    LOOP
        -- Get fight details
        SELECT * INTO v_fight FROM fights WHERE id = v_fight_id;
        
        IF NOT FOUND THEN
            CONTINUE;
        END IF;
        
        -- Recompute for each profile
        FOREACH v_profile_id IN ARRAY v_profiles
        LOOP
            -- RED corner
            BEGIN
                SELECT * INTO v_result
                FROM calculate_fantasy_points(v_fight_id, v_fight.red_fighter_id, v_profile_id);
                
                INSERT INTO fantasy_fight_stats (
                    fight_id, fighter_id, profile_id, fantasy_points, breakdown
                ) VALUES (
                    v_fight_id,
                    v_fight.red_fighter_id,
                    v_profile_id,
                    (v_result->>'fantasy_points')::numeric,
                    v_result->'breakdown'
                )
                ON CONFLICT (fight_id, fighter_id, profile_id)
                DO UPDATE SET
                    fantasy_points = EXCLUDED.fantasy_points,
                    breakdown = EXCLUDED.breakdown,
                    updated_at = NOW();
                
                RETURN QUERY SELECT 
                    v_fight_id,
                    v_fight.red_fighter_id,
                    v_profile_id,
                    (v_result->>'fantasy_points')::numeric,
                    'success'::TEXT;
            EXCEPTION WHEN OTHERS THEN
                RETURN QUERY SELECT 
                    v_fight_id,
                    v_fight.red_fighter_id,
                    v_profile_id,
                    0.0::NUMERIC,
                    ('error: ' || SQLERRM)::TEXT;
            END;
            
            -- BLUE corner
            BEGIN
                SELECT * INTO v_result
                FROM calculate_fantasy_points(v_fight_id, v_fight.blue_fighter_id, v_profile_id);
                
                INSERT INTO fantasy_fight_stats (
                    fight_id, fighter_id, profile_id, fantasy_points, breakdown
                ) VALUES (
                    v_fight_id,
                    v_fight.blue_fighter_id,
                    v_profile_id,
                    (v_result->>'fantasy_points')::numeric,
                    v_result->'breakdown'
                )
                ON CONFLICT (fight_id, fighter_id, profile_id)
                DO UPDATE SET
                    fantasy_points = EXCLUDED.fantasy_points,
                    breakdown = EXCLUDED.breakdown,
                    updated_at = NOW();
                
                RETURN QUERY SELECT 
                    v_fight_id,
                    v_fight.blue_fighter_id,
                    v_profile_id,
                    (v_result->>'fantasy_points')::numeric,
                    'success'::TEXT;
            EXCEPTION WHEN OTHERS THEN
                RETURN QUERY SELECT 
                    v_fight_id,
                    v_fight.blue_fighter_id,
                    v_profile_id,
                    0.0::NUMERIC,
                    ('error: ' || SQLERRM)::TEXT;
            END;
        END LOOP;
    END LOOP;
    
    RETURN;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION recompute_all_fantasy_stats IS 
    'Manually recompute fantasy stats for specified fight(s) or event. Usage: SELECT * FROM recompute_all_fantasy_stats();';

-- ========================================
-- VERIFICATION
-- ========================================
SELECT 'Fantasy Auto-Trigger Migration Complete' as status;

-- Show created triggers
SELECT 
    trigger_name,
    event_manipulation,
    action_statement
FROM information_schema.triggers
WHERE trigger_name LIKE '%fantasy%'
ORDER BY trigger_name;
