"""
CV Analytics Engine - Mock CV Data Generator
Simulate realistic CV model outputs for testing
"""

import random
import time
from typing import List, Dict
import logging
from .models import RawCVInput, ActionType, ImpactLevel

logger = logging.getLogger(__name__)


class MockCVDataGenerator:
    """Generate realistic mock CV data"""
    
    def __init__(self, bout_id: str, round_id: str):
        self.bout_id = bout_id
        self.round_id = round_id
        self.frame_counter = 0
        self.base_timestamp = int(time.time() * 1000)
    
    def generate_event_sequence(self, scenario: str = "balanced") -> List[RawCVInput]:
        """
        Generate realistic event sequence
        
        Scenarios:
        - balanced: Mix of strikes and grappling
        - striker_dominance: Heavy striking with KDs
        - grappler_control: Lots of takedowns and control
        - war: High-paced back-and-forth
        """
        if scenario == "balanced":
            return self._generate_balanced_fight()
        elif scenario == "striker_dominance":
            return self._generate_striker_dominance()
        elif scenario == "grappler_control":
            return self._generate_grappler_control()
        elif scenario == "war":
            return self._generate_war()
        else:
            return self._generate_balanced_fight()
    
    def _generate_balanced_fight(self) -> List[RawCVInput]:
        """Generate balanced fight sequence"""
        events = []
        
        # 20 events over ~60 seconds
        for i in range(20):
            fighter = "fighter_a" if random.random() > 0.5 else "fighter_b"
            
            # Random action
            action = random.choice([
                ActionType.PUNCH, ActionType.PUNCH, ActionType.KICK,
                ActionType.KNEE, ActionType.TAKEDOWN
            ])
            
            # Random impact
            impact = random.choice([
                ImpactLevel.LIGHT, ImpactLevel.MEDIUM,
                ImpactLevel.MEDIUM, ImpactLevel.HEAVY
            ])
            
            event = self._create_raw_input(fighter, action, impact)
            events.append(event)
            
            time.sleep(0.1)  # Small delay for timestamp variation
        
        return events
    
    def _generate_striker_dominance(self) -> List[RawCVInput]:
        """Generate striker dominance scenario"""
        events = []
        
        # Fighter A dominates with strikes
        for i in range(15):
            fighter = "fighter_a" if i < 12 else "fighter_b"
            
            if fighter == "fighter_a":
                action = random.choice([ActionType.PUNCH, ActionType.KICK, ActionType.KNEE])
                impact = random.choice([ImpactLevel.MEDIUM, ImpactLevel.HEAVY, ImpactLevel.CRITICAL])
            else:
                action = ActionType.PUNCH
                impact = ImpactLevel.LIGHT
            
            event = self._create_raw_input(fighter, action, impact)
            events.append(event)
            
            time.sleep(0.1)
        
        # Add knockdown
        kd_event = self._create_raw_input(
            "fighter_a",
            ActionType.KNOCKDOWN,
            ImpactLevel.CRITICAL
        )
        events.append(kd_event)
        
        return events
    
    def _generate_grappler_control(self) -> List[RawCVInput]:
        """Generate grappler control scenario"""
        events = []
        
        # Takedown
        td = self._create_raw_input("fighter_a", ActionType.TAKEDOWN, ImpactLevel.MEDIUM)
        events.append(td)
        time.sleep(0.1)
        
        # Control period (30 seconds)
        control_start = self._create_raw_input("fighter_a", ActionType.GROUND_CONTROL, ImpactLevel.MEDIUM)
        events.append(control_start)
        time.sleep(3.0)
        
        # Submission attempts
        for _ in range(3):
            sub = self._create_raw_input("fighter_a", ActionType.SUBMISSION, ImpactLevel.HEAVY)
            events.append(sub)
            time.sleep(1.0)
        
        # Standup
        standup = self._create_raw_input("fighter_b", ActionType.STANDUP, ImpactLevel.MEDIUM)
        events.append(standup)
        
        return events
    
    def _generate_war(self) -> List[RawCVInput]:
        """Generate high-paced war scenario"""
        events = []
        
        # Rapid exchanges - 30 strikes in 30 seconds
        for i in range(30):
            fighter = "fighter_a" if i % 2 == 0 else "fighter_b"
            action = random.choice([ActionType.PUNCH, ActionType.KICK, ActionType.KNEE, ActionType.ELBOW])
            impact = random.choice([ImpactLevel.MEDIUM, ImpactLevel.HEAVY])
            
            event = self._create_raw_input(fighter, action, impact)
            events.append(event)
            
            time.sleep(0.05)  # Very fast pace
        
        return events
    
    def _create_raw_input(
        self,
        fighter_id: str,
        action_type: ActionType,
        impact_level: ImpactLevel,
        camera_id: str = "cam_1"
    ) -> RawCVInput:
        """Create single raw CV input"""
        self.frame_counter += 1
        timestamp = self.base_timestamp + (self.frame_counter * 100)  # ~30fps
        
        # Generate action logits
        logits = {at.value: random.uniform(0.1, 0.3) for at in ActionType}
        logits[action_type.value] = random.uniform(0.7, 0.95)  # High confidence for actual action
        
        # Generate keypoints (simplified)
        keypoints = [(random.uniform(0, 1), random.uniform(0, 1), random.uniform(0.6, 0.95)) for _ in range(17)]
        
        # Motion vectors
        magnitude = {
            ImpactLevel.LIGHT: random.uniform(1, 3),
            ImpactLevel.MEDIUM: random.uniform(3, 6),
            ImpactLevel.HEAVY: random.uniform(6, 9),
            ImpactLevel.CRITICAL: random.uniform(9, 12)
        }[impact_level]
        
        return RawCVInput(
            frame_id=self.frame_counter,
            timestamp_ms=timestamp,
            camera_id=camera_id,
            fighter_id=fighter_id,
            action_type=action_type,
            action_logits=logits,
            fighter_bbox=[random.uniform(0.2, 0.8), random.uniform(0.2, 0.8), 0.15, 0.4],
            impact_point=(random.uniform(0, 1), random.uniform(0, 1)) if action_type != ActionType.GROUND_CONTROL else None,
            keypoints=keypoints,
            impact_detected=True if impact_level in [ImpactLevel.HEAVY, ImpactLevel.CRITICAL] else False,
            impact_level=impact_level,
            motion_vectors={
                "vx": random.uniform(-5, 5),
                "vy": random.uniform(-5, 5),
                "magnitude": magnitude
            },
            camera_angle=random.uniform(0, 360),
            camera_distance=random.uniform(3, 8)
        )
    
    def generate_multicamera_frame(
        self,
        fighter_id: str,
        action_type: ActionType,
        impact_level: ImpactLevel,
        num_cameras: int = 3
    ) -> List[RawCVInput]:
        """Generate multi-camera views of same event"""
        frames = []
        
        for i in range(num_cameras):
            camera_id = f"cam_{i+1}"
            
            # Vary confidence and angle per camera
            frame = self._create_raw_input(fighter_id, action_type, impact_level, camera_id)
            frame.camera_angle = (120 * i) % 360  # Spread cameras around octagon
            frame.confidence = random.uniform(0.7, 0.95)
            
            frames.append(frame)
        
        return frames
