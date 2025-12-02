-- ========================================
-- METHOD 2: SQL INSERT STATEMENTS
-- ========================================
-- Copy and paste this entire file into Supabase SQL Editor
-- This is faster than using the Table UI

-- Step 1: Insert Event
INSERT INTO events (code, name, venue, promotion, start_time_utc)
VALUES ('PFC50', 'PFC 50: Frisco', 'Comerica Center', 'PFC', '2026-01-24 01:00:00+00')
RETURNING id;
-- Note the returned ID (let's call it EVENT_ID)

-- Step 2: Insert 6 Fighters
INSERT INTO fighters (first_name, last_name, nickname, country) VALUES
('John', 'Strike', 'The Blade', 'USA'),
('Mike', 'Iron', 'The Hammer', 'USA'),
('Carlos', 'Rivera', 'El Fuego', 'MEX'),
('Alex', 'Stone', 'The Wall', 'USA'),
('David', 'Lee', 'Dragon', 'USA'),
('Mark', 'Torres', 'The Tank', 'USA');

-- Verify fighters
SELECT id, first_name, last_name, nickname FROM fighters ORDER BY created_at DESC LIMIT 6;

-- Step 3: Insert 3 Fights
-- Replace the UUIDs below with your actual event_id and fighter IDs from above
-- Or use this smarter approach with subqueries:

WITH event AS (
    SELECT id FROM events WHERE code = 'PFC50'
),
fighter_ids AS (
    SELECT 
        id,
        first_name,
        last_name,
        ROW_NUMBER() OVER (ORDER BY created_at DESC) as rn
    FROM fighters
    WHERE first_name IN ('John', 'Mike', 'Carlos', 'Alex', 'David', 'Mark')
    ORDER BY created_at DESC
    LIMIT 6
)
INSERT INTO fights (event_id, bout_order, code, red_fighter_id, blue_fighter_id, scheduled_rounds, weight_class, rule_set)
SELECT 
    (SELECT id FROM event),
    3,
    'PFC50-F1',
    (SELECT id FROM fighter_ids WHERE first_name = 'John' AND last_name = 'Strike'),
    (SELECT id FROM fighter_ids WHERE first_name = 'Mike' AND last_name = 'Iron'),
    3,
    'Lightweight',
    'MMA Unified'
UNION ALL
SELECT 
    (SELECT id FROM event),
    2,
    'PFC50-F2',
    (SELECT id FROM fighter_ids WHERE first_name = 'Carlos' AND last_name = 'Rivera'),
    (SELECT id FROM fighter_ids WHERE first_name = 'Alex' AND last_name = 'Stone'),
    3,
    'Featherweight',
    'MMA Unified'
UNION ALL
SELECT 
    (SELECT id FROM event),
    1,
    'PFC50-F3',
    (SELECT id FROM fighter_ids WHERE first_name = 'David' AND last_name = 'Lee'),
    (SELECT id FROM fighter_ids WHERE first_name = 'Mark' AND last_name = 'Torres'),
    3,
    'Welterweight',
    'MMA Unified';

-- Verify fights
SELECT code, bout_order, weight_class FROM fights WHERE code LIKE 'PFC50-%' ORDER BY bout_order DESC;

-- Step 4: Insert Round States (2 per fight = 6 total)

-- Fight 1 Round States
INSERT INTO round_state (
    fight_id, round, ts_ms, seq,
    red_strikes, blue_strikes, red_sig_strikes, blue_sig_strikes,
    red_knockdowns, blue_knockdowns, red_control_sec, blue_control_sec,
    red_ai_damage, blue_ai_damage, red_ai_win_prob, blue_ai_win_prob,
    round_locked
) VALUES
-- PFC50-F1 Round 1 (Locked)
(
    (SELECT id FROM fights WHERE code = 'PFC50-F1'),
    1, 1737761000000, 1,
    25, 18, 15, 10,
    0, 0, 60, 30,
    6.3, 5.0, 0.62, 0.38,
    true
),
-- PFC50-F1 Round 2 (Live)
(
    (SELECT id FROM fights WHERE code = 'PFC50-F1'),
    2, 1737761100000, 2,
    40, 30, 24, 18,
    1, 0, 80, 40,
    8.1, 5.4, 0.78, 0.22,
    false
);

-- Fight 2 Round States
INSERT INTO round_state (
    fight_id, round, ts_ms, seq,
    red_strikes, blue_strikes, red_sig_strikes, blue_sig_strikes,
    red_knockdowns, blue_knockdowns, red_control_sec, blue_control_sec,
    red_ai_damage, blue_ai_damage, red_ai_win_prob, blue_ai_win_prob,
    round_locked
) VALUES
-- PFC50-F2 Round 1 (Locked)
(
    (SELECT id FROM fights WHERE code = 'PFC50-F2'),
    1, 1737762000000, 1,
    22, 20, 13, 12,
    0, 0, 55, 35,
    5.8, 6.2, 0.48, 0.52,
    true
),
-- PFC50-F2 Round 2 (Live)
(
    (SELECT id FROM fights WHERE code = 'PFC50-F2'),
    2, 1737762100000, 2,
    35, 38, 20, 22,
    0, 1, 70, 50,
    7.2, 8.8, 0.35, 0.65,
    false
);

-- Fight 3 Round States
INSERT INTO round_state (
    fight_id, round, ts_ms, seq,
    red_strikes, blue_strikes, red_sig_strikes, blue_sig_strikes,
    red_knockdowns, blue_knockdowns, red_control_sec, blue_control_sec,
    red_ai_damage, blue_ai_damage, red_ai_win_prob, blue_ai_win_prob,
    round_locked
) VALUES
-- PFC50-F3 Round 1 (Locked)
(
    (SELECT id FROM fights WHERE code = 'PFC50-F3'),
    1, 1737763000000, 1,
    28, 15, 18, 8,
    1, 0, 75, 25,
    9.5, 3.2, 0.85, 0.15,
    true
),
-- PFC50-F3 Round 2 (Live)
(
    (SELECT id FROM fights WHERE code = 'PFC50-F3'),
    2, 1737763100000, 2,
    42, 20, 28, 12,
    2, 0, 95, 25,
    12.8, 4.1, 0.92, 0.08,
    false
);

-- Verify round states
SELECT 
    f.code,
    rs.round,
    rs.seq,
    rs.red_strikes,
    rs.blue_strikes,
    rs.round_locked
FROM round_state rs
JOIN fights f ON rs.fight_id = f.id
ORDER BY f.code, rs.seq;

-- Step 5: Insert Fight Results (Optional)
INSERT INTO fight_results (fight_id, winner_side, method, round, time) VALUES
(
    (SELECT id FROM fights WHERE code = 'PFC50-F1'),
    'RED',
    'UD',
    3,
    '5:00'
),
(
    (SELECT id FROM fights WHERE code = 'PFC50-F2'),
    'BLUE',
    'TKO',
    2,
    '4:32'
),
(
    (SELECT id FROM fights WHERE code = 'PFC50-F3'),
    'RED',
    'KO',
    2,
    '3:15'
);

-- Verify results
SELECT 
    f.code,
    fr.winner_side,
    fr.method,
    fr.round,
    fr.time
FROM fight_results fr
JOIN fights f ON fr.fight_id = f.id
ORDER BY f.code;

-- ========================================
-- FINAL VERIFICATION
-- ========================================

SELECT 'Events' as table_name, COUNT(*) as count FROM events WHERE code = 'PFC50'
UNION ALL
SELECT 'Fighters', COUNT(*) FROM fighters WHERE first_name IN ('John', 'Mike', 'Carlos', 'Alex', 'David', 'Mark')
UNION ALL
SELECT 'Fights', COUNT(*) FROM fights WHERE code LIKE 'PFC50-%'
UNION ALL
SELECT 'Round States', COUNT(*) FROM round_state WHERE fight_id IN (SELECT id FROM fights WHERE code LIKE 'PFC50-%')
UNION ALL
SELECT 'Fight Results', COUNT(*) FROM fight_results WHERE fight_id IN (SELECT id FROM fights WHERE code LIKE 'PFC50-%');

-- Expected output:
-- Events: 1
-- Fighters: 6
-- Fights: 3
-- Round States: 6
-- Fight Results: 3

-- ========================================
-- GET API KEYS (if you ran the migration with seed function)
-- ========================================
SELECT name, api_key, scope FROM api_clients ORDER BY scope;

-- Done! 🎉
