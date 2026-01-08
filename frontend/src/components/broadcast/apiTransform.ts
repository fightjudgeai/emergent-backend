import { RoundScore, UnifiedTotal, Winner } from "./types";

interface APIRoundCompleteMessage { type: "round_complete"; round: number; scores: { red: { unified: number }; blue: { unified: number } }; fighters: { red: { name: string }; blue: { name: string } }; }
interface APIFinalResultMessage { type: "final_result"; winner: "red" | "blue" | "draw"; totals: { red: number; blue: number }; fighters: { red: { name: string }; blue: { name: string } }; }

export function transformRoundComplete(message: APIRoundCompleteMessage): { round: RoundScore; roundNumber: number; redName: string; blueName: string } {
  return { round: { round: message.round, unified_red: message.scores.red.unified, unified_blue: message.scores.blue.unified }, roundNumber: message.round, redName: message.fighters.red.name, blueName: message.fighters.blue.name };
}

export function transformFinalResult(message: APIFinalResultMessage): { total: UnifiedTotal; winner: Winner; redName: string; blueName: string } {
  return { total: { red: message.totals.red, blue: message.totals.blue }, winner: message.winner, redName: message.fighters.red.name, blueName: message.fighters.blue.name };
}