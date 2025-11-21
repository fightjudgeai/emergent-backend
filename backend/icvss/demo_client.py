"""
ICVSS Demo Client
Demonstrates how to use ICVSS API endpoints
"""

import requests
import json
import time
from datetime import datetime

# Backend URL
BASE_URL = "https://combatjudge.preview.emergentagent.com/api/icvss"

def demo_round_lifecycle():
    """Demonstrate a complete round with CV and judge events"""
    print("=" * 80)
    print("ICVSS DEMO - Round Lifecycle")
    print("=" * 80)
    
    # 1. Open Round
    print("\n[1/5] Opening Round...")
    bout_id = f"demo-bout-{int(time.time())}"
    
    response = requests.post(f"{BASE_URL}/round/open", params={
        "bout_id": bout_id,
        "round_num": 1
    })
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return
    
    round_data = response.json()
    round_id = round_data["round_id"]
    print(f"✓ Round opened: {round_id}")
    
    # 2. Add CV Events (Fighter 1 - Multiple strikes and a knockdown)
    print("\n[2/5] Adding CV Events...")
    
    cv_events = [
        # Fighter 1 strikes
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "strike_jab",
            "severity": 0.6,
            "confidence": 0.92,
            "position": "distance",
            "timestamp_ms": 1000,
            "source": "cv_system",
            "vendor_id": "demo_cv"
        },
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "strike_cross",
            "severity": 0.8,
            "confidence": 0.95,
            "position": "distance",
            "timestamp_ms": 2500,
            "source": "cv_system",
            "vendor_id": "demo_cv"
        },
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "kick_head",
            "severity": 0.9,
            "confidence": 0.98,
            "position": "distance",
            "timestamp_ms": 5000,
            "source": "cv_system",
            "vendor_id": "demo_cv"
        },
        # Fighter 1 KNOCKDOWN!
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "KD_hard",
            "severity": 1.0,
            "confidence": 0.99,
            "position": "distance",
            "timestamp_ms": 7500,
            "source": "cv_system",
            "vendor_id": "demo_cv"
        },
        # Fighter 2 - Some jabs
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter2",
            "event_type": "strike_jab",
            "severity": 0.5,
            "confidence": 0.88,
            "position": "distance",
            "timestamp_ms": 3000,
            "source": "cv_system",
            "vendor_id": "demo_cv"
        },
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter2",
            "event_type": "strike_jab",
            "severity": 0.5,
            "confidence": 0.85,
            "position": "distance",
            "timestamp_ms": 4000,
            "source": "cv_system",
            "vendor_id": "demo_cv"
        }
    ]
    
    accepted_count = 0
    for event in cv_events:
        response = requests.post(f"{BASE_URL}/round/event", params={"round_id": round_id}, json={"event": event})
        if response.status_code == 200 and response.json().get("success"):
            accepted_count += 1
    
    print(f"✓ Added {accepted_count}/{len(cv_events)} CV events")
    
    # 3. Add Judge Manual Events
    print("\n[3/5] Adding Judge Manual Events...")
    
    judge_events = [
        {
            "bout_id": bout_id,
            "round_id": round_id,
            "fighter_id": "fighter1",
            "event_type": "td_landed",
            "severity": 0.8,
            "confidence": 1.0,
            "position": "ground",
            "timestamp_ms": 10000,
            "source": "judge_manual"
        }
    ]
    
    for event in judge_events:
        response = requests.post(f"{BASE_URL}/round/event", params={"round_id": round_id}, json={"event": event})
    
    print(f"✓ Added {len(judge_events)} judge events")
    
    # 4. Calculate Score
    print("\n[4/5] Calculating Score...")
    
    response = requests.get(f"{BASE_URL}/round/score/{round_id}")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return
    
    score_data = response.json()
    
    print("\n" + "=" * 80)
    print("SCORE BREAKDOWN")
    print("=" * 80)
    print(f"\n🥊 FINAL SCORE: {score_data['score_card']}")
    print(f"🏆 WINNER: {score_data['winner'].upper()}")
    print(f"\n📊 Fighter 1:")
    print(f"   Total Score: {score_data['fighter1_breakdown']['cv_score'] + score_data['fighter1_breakdown']['judge_score']:.2f}")
    print(f"   CV Score: {score_data['fighter1_breakdown']['cv_score']:.2f}")
    print(f"   Judge Score: {score_data['fighter1_breakdown']['judge_score']:.2f}")
    print(f"   Striking: {score_data['fighter1_breakdown']['striking']:.2f}")
    print(f"   Grappling: {score_data['fighter1_breakdown']['grappling']:.2f}")
    print(f"   Control: {score_data['fighter1_breakdown']['control']:.2f}")
    
    print(f"\n📊 Fighter 2:")
    print(f"   Total Score: {score_data['fighter2_breakdown']['cv_score'] + score_data['fighter2_breakdown']['judge_score']:.2f}")
    print(f"   CV Score: {score_data['fighter2_breakdown']['cv_score']:.2f}")
    print(f"   Judge Score: {score_data['fighter2_breakdown']['judge_score']:.2f}")
    print(f"   Striking: {score_data['fighter2_breakdown']['striking']:.2f}")
    print(f"   Grappling: {score_data['fighter2_breakdown']['grappling']:.2f}")
    print(f"   Control: {score_data['fighter2_breakdown']['control']:.2f}")
    
    print(f"\n📈 Metadata:")
    print(f"   Confidence: {score_data['confidence']:.1%}")
    print(f"   CV Events: {score_data['cv_event_count']}")
    print(f"   Judge Events: {score_data['judge_event_count']}")
    print(f"   CV Contribution: {score_data['cv_contribution']:.1%}")
    print(f"   Judge Contribution: {score_data['judge_contribution']:.1%}")
    
    # 5. Lock Round
    print("\n[5/5] Locking Round...")
    
    response = requests.post(f"{BASE_URL}/round/lock/{round_id}")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return
    
    lock_data = response.json()
    print(f"✓ Round locked with hash: {lock_data['event_hash'][:16]}...")
    
    print("\n" + "=" * 80)
    print("DEMO COMPLETE ✓")
    print("=" * 80)


def demo_deduplication():
    """Demonstrate event deduplication"""
    print("\n" + "=" * 80)
    print("ICVSS DEMO - Event Deduplication (80-150ms window)")
    print("=" * 80)
    
    bout_id = f"dedup-test-{int(time.time())}"
    
    # Open round
    response = requests.post(f"{BASE_URL}/round/open", params={
        "bout_id": bout_id,
        "round_num": 1
    })
    round_id = response.json()["round_id"]
    
    print(f"\n✓ Round opened: {round_id}")
    print("\nSending 3 identical events within 100ms window...")
    
    # Send 3 duplicate events quickly
    base_event = {
        "bout_id": bout_id,
        "round_id": round_id,
        "fighter_id": "fighter1",
        "event_type": "strike_jab",
        "severity": 0.8,
        "confidence": 0.95,
        "position": "distance",
        "source": "cv_system",
        "vendor_id": "demo_cv"
    }
    
    results = []
    for i in range(3):
        event = base_event.copy()
        event["timestamp_ms"] = 1000 + (i * 30)  # 30ms apart
        
        response = requests.post(f"{BASE_URL}/round/event", params={"round_id": round_id}, json={"event": event})
        result = response.json()
        results.append(result)
        print(f"  Event {i+1} at {event['timestamp_ms']}ms: {result['message']}")
    
    # Check score (should only count 1 event)
    response = requests.get(f"{BASE_URL}/round/score/{round_id}")
    score_data = response.json()
    
    print(f"\n✓ Deduplication worked! Only {score_data['cv_event_count']} event counted (expected 1)")


def demo_stats():
    """Get ICVSS system statistics"""
    print("\n" + "=" * 80)
    print("ICVSS DEMO - System Statistics")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/stats")
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return
    
    stats = response.json()
    
    print("\n📊 Event Processor:")
    print(f"   Total Processed: {stats['event_processor']['total_processed']}")
    print(f"   Dedup Window: {stats['event_processor']['dedup_window_ms']}ms")
    print(f"   Confidence Threshold: {stats['event_processor']['confidence_threshold']:.1%}")
    
    print("\n📡 WebSocket Connections:")
    print(f"   CV Feed: {stats['websocket_connections']['total_cv_feed']}")
    print(f"   Judge Feed: {stats['websocket_connections']['total_judge_feed']}")
    print(f"   Score Feed: {stats['websocket_connections']['total_score_feed']}")
    print(f"   Broadcast Feed: {stats['websocket_connections']['total_broadcast_feed']}")
    
    print(f"\n🎯 Active Rounds: {stats['active_rounds']}")


if __name__ == "__main__":
    print("\n🚀 Starting ICVSS Demo Client...\n")
    
    # Check health
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("✓ ICVSS Backend is healthy\n")
        else:
            print("❌ ICVSS Backend health check failed")
            exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to ICVSS backend: {e}")
        print(f"   Make sure backend is running on http://localhost:8001")
        exit(1)
    
    # Run demos
    demo_round_lifecycle()
    time.sleep(1)
    
    demo_deduplication()
    time.sleep(1)
    
    demo_stats()
    
    print("\n✅ All demos completed successfully!")
