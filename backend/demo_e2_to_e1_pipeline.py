"""
DEMO: Complete E2 → E1 Pipeline
Shows full flow from multi-camera CV → Analytics → Scoring → Output

Pipeline Flow:
Multi-Camera CV Feeds → E2 (CV Analytics) → Standardized Events → E1 (Scoring) → 10-Point Score
"""

import sys
sys.path.append('/app/backend')
import asyncio
from datetime import datetime

from cv_analytics.mock_generator import MockCVDataGenerator
from cv_analytics.analytics_engine import CVAnalyticsEngine
from fjai.round_manager import RoundManager
from fjai.scoring_engine import WeightedScoringEngine
from fjai.websocket_manager import fjai_ws_manager


class PipelineDemo:
    """Demonstrate complete E2 → E1 pipeline"""
    
    def __init__(self):
        self.bout_id = "PFC_50_MAIN_EVENT"
        self.round_num = 1
        self.round_id = None
        
        # Initialize engines
        self.cv_engine = CVAnalyticsEngine()
        self.scoring_engine = WeightedScoringEngine()
        
        print("\n" + "="*80)
        print("FIGHT JUDGE AI - E2 → E1 PIPELINE DEMONSTRATION")
        print("PFC 50 - Main Event Simulation")
        print("="*80 + "\n")
    
    def simulate_live_fight(self, scenario: str = "war"):
        """Simulate live fight with real-time event processing"""
        print(f"🥊 Scenario: {scenario.upper()}")
        print("-" * 80)
        
        # Step 1: Generate mock CV data from multiple cameras
        print("\n[STEP 1] Multi-Camera CV System")
        print("Cameras: cam_1 (front), cam_2 (side), cam_3 (overhead)")
        
        generator = MockCVDataGenerator(self.bout_id, f"round_{self.round_num}")
        mock_frames = generator.generate_event_sequence(scenario)
        
        print(f"✓ Generated {len(mock_frames)} CV frames")
        
        # Step 2: Process through CV Analytics Engine (E2)
        print("\n[STEP 2] CV Analytics Engine (E2) - Processing")
        print("Pipeline: Temporal smoothing → Deduplication → Classification")
        
        standardized_events = []
        for i, raw_frame in enumerate(mock_frames):
            events = self.cv_engine.process_raw_input(
                raw_frame,
                self.bout_id,
                f"round_{self.round_num}"
            )
            standardized_events.extend(events)
            
            if events and i % 5 == 0:  # Print sample
                event = events[0]
                print(f"  Frame {raw_frame.frame_id}: {raw_frame.action_type.value} "
                      f"→ {event.event_type.value} "
                      f"(confidence: {event.confidence:.2f}, severity: {event.severity:.2f})")
        
        print(f"\n✓ Generated {len(standardized_events)} standardized combat events")
        
        # Show event breakdown
        event_types = {}
        for event in standardized_events:
            event_types[event.event_type.value] = event_types.get(event.event_type.value, 0) + 1
        
        print("\n  Event Breakdown:")
        for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True):
            print(f"    • {event_type}: {count}")
        
        # Step 3: Calculate score through Scoring Engine (E1)
        print("\n[STEP 3] Fight Judge AI Scoring Engine (E1)")
        print("Weights: Damage 50% | Control 25% | Aggression 15% | Defense 10%")
        
        score = self.scoring_engine.calculate_round_score(
            standardized_events,
            self.bout_id,
            f"round_{self.round_num}",
            self.round_num
        )
        
        # Display results
        print("\n" + "="*80)
        print("ROUND SCORE CARD")
        print("="*80)
        
        print(f"\n🏆 Official Score: {score.score_card}")
        print(f"   Winner: {score.winner.upper()}")
        print(f"   Confidence: {score.confidence*100:.1f}%")
        
        if score.damage_override:
            print("   ⚠️  DAMAGE PRIMACY OVERRIDE APPLIED")
        
        print("\n📊 Category Breakdown:")
        print(f"\n   FIGHTER A:")
        print(f"     Damage:     {score.fighter_a_breakdown.damage:6.2f} ({self.scoring_engine.weights.damage*100:.0f}%)")
        print(f"     Control:    {score.fighter_a_breakdown.control:6.2f} ({self.scoring_engine.weights.control*100:.0f}%)")
        print(f"     Aggression: {score.fighter_a_breakdown.aggression:6.2f} ({self.scoring_engine.weights.aggression*100:.0f}%)")
        print(f"     Defense:    {score.fighter_a_breakdown.defense:6.2f} ({self.scoring_engine.weights.defense*100:.0f}%)")
        print(f"     ─────────────────")
        print(f"     TOTAL:      {score.fighter_a_score:6.2f}")
        
        print(f"\n   FIGHTER B:")
        print(f"     Damage:     {score.fighter_b_breakdown.damage:6.2f} ({self.scoring_engine.weights.damage*100:.0f}%)")
        print(f"     Control:    {score.fighter_b_breakdown.control:6.2f} ({self.scoring_engine.weights.control*100:.0f}%)")
        print(f"     Aggression: {score.fighter_b_breakdown.aggression:6.2f} ({self.scoring_engine.weights.aggression*100:.0f}%)")
        print(f"     Defense:    {score.fighter_b_breakdown.defense:6.2f} ({self.scoring_engine.weights.defense*100:.0f}%)")
        print(f"     ─────────────────")
        print(f"     TOTAL:      {score.fighter_b_score:6.2f}")
        
        print(f"\n📈 Event Sources:")
        print(f"   CV Events:     {score.cv_events}")
        print(f"   Manual Events: {score.manual_events}")
        print(f"   Total Events:  {score.total_events}")
        
        # Step 4: Generate Analytics
        print("\n[STEP 4] Fight Analytics")
        analytics = self.cv_engine.generate_analytics(standardized_events)
        
        print(f"   Control Time: {analytics.control_time_estimate:.1f}s")
        print(f"   Fight Pace: {analytics.pace_score*100:.0f}%")
        print(f"   Tempo Pattern: {analytics.tempo_pattern.upper()}")
        print(f"   Fighter Style: {analytics.fighter_style.upper()}")
        print(f"   Cumulative Damage: {analytics.cumulative_damage*100:.0f}%")
        print(f"   Rocked Probability: {analytics.rocked_probability*100:.0f}%")
        
        print("\n" + "="*80)
        print("✅ PIPELINE COMPLETE")
        print("="*80 + "\n")
        
        # Output destinations
        print("📡 Output Destinations:")
        print("   → Supervisor Dashboard (real-time scoring)")
        print("   → Judge Console (official scorecard)")
        print("   → Arena Jumbotron (live graphics overlay)")
        print("   → Broadcast Stream (TV graphics)")
        
        return score, analytics
    
    def run_multiple_scenarios(self):
        """Run all scenario demonstrations"""
        scenarios = ["balanced", "striker_dominance", "grappler_control", "war"]
        
        for scenario in scenarios:
            self.simulate_live_fight(scenario)
            print("\n" + "-"*80 + "\n")
            input("Press Enter to run next scenario...")


def main():
    """Run pipeline demonstration"""
    demo = PipelineDemo()
    
    # Interactive menu
    print("Select demonstration mode:")
    print("1. Run single scenario")
    print("2. Run all scenarios")
    print("3. Multi-camera fusion demo")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\nAvailable scenarios:")
        print("  • balanced - Mix of strikes and grappling")
        print("  • striker_dominance - Heavy striking with KDs")
        print("  • grappler_control - Takedowns and control")
        print("  • war - High-paced back-and-forth")
        
        scenario = input("\nEnter scenario name: ").strip() or "balanced"
        demo.simulate_live_fight(scenario)
        
    elif choice == "2":
        demo.run_multiple_scenarios()
        
    elif choice == "3":
        print("\n[MULTI-CAMERA FUSION DEMO]")
        print("Simulating same strike from 3 camera angles...\n")
        
        generator = MockCVDataGenerator("PFC_50", "round_1")
        multicam_frames = generator.generate_multicamera_frame(
            "fighter_a",
            "punch",
            "heavy",
            num_cameras=3
        )
        
        print(f"Camera Views Generated: {len(multicam_frames)}")
        for i, frame in enumerate(multicam_frames):
            print(f"\n  Camera {i+1}:")
            print(f"    Angle: {frame.camera_angle:.0f}°")
            print(f"    Confidence: {max(frame.action_logits.values()):.2f}")
            print(f"    Distance: {frame.camera_distance:.1f}m")
        
        # Process through pipeline
        cv_engine = CVAnalyticsEngine()
        all_events = cv_engine.process_multicamera_batch(
            multicam_frames,
            "PFC_50",
            "round_1"
        )
        
        print(f"\n✓ Fused into {len(all_events)} canonical event(s)")
        if all_events:
            event = all_events[0]
            print(f"  Event Type: {event.event_type.value}")
            print(f"  Confidence: {event.confidence:.2f} (averaged)")
            print(f"  Canonical: {event.canonical}")
    
    else:
        print("Invalid choice. Running balanced scenario...")
        demo.simulate_live_fight("balanced")


if __name__ == "__main__":
    main()
