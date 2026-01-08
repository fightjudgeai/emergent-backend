export interface Fighter { name: string; }
export interface RoundScore { round: number; unified_red: number; unified_blue: number; }
export interface UnifiedTotal { red: number; blue: number; }
export type FightStatus = "pending" | "in_progress" | "completed";
export type Winner = "red" | "blue" | "draw" | null;
export interface BroadcastData { event: string; fight_id: string; division: string; red: Fighter; blue: Fighter; rounds: RoundScore[]; unified_total: UnifiedTotal; winner: Winner; status: FightStatus; }
export type ConnectionStatus = "connected" | "disconnected" | "error";

export interface APIRoundCompleteMessage { type: "round_complete"; round: number; scores: { red: { unified: number }; blue: { unified: number } }; fighters: { red: { name: string }; blue: { name: string } }; }
export interface APIFinalResultMessage { type: "final_result"; winner: "red" | "blue" | "draw"; totals: { red: number; blue: number }; fighters: { red: { name: string }; blue: { name: string } }; }