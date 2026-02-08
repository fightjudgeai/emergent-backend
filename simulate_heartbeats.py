"""
Simulate Heartbeats from FJAIPOS Modules

This script simulates heartbeats from all FJAIPOS components
to test the Heartbeat Monitor service.

Run this in the background to generate realistic heartbeat traffic.
"""

import asyncio
import httpx
import random
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

# Backend URL
API_URL = os.getenv("REACT_APP_BACKEND_URL", "http://localhost:8001")

# Services that send heartbeats
SERVICES = [
    "CV Router",
    "CV Analytics",
    "Scoring Engine",
    "Replay Worker",
    "Highlight Worker",
    "Storage Manager",
    "Supervisor Console"
]


def generate_metrics(service_name: str) -> dict:
    """Generate realistic metrics for a service"""
    base_metrics = {
        "event_count": random.randint(100, 5000),
        "error_count": random.randint(0, 10),
        "latency_ms": round(random.uniform(10, 100), 2),
        "uptime_seconds": random.randint(3600, 86400)
    }
    
    # Add service-specific metrics
    if "Storage" in service_name:
        base_metrics["storage_used_gb"] = round(random.uniform(20, 100), 2)
        base_metrics["storage_available_gb"] = round(random.uniform(100, 500), 2)
    
    if "CV" in service_name or "Analytics" in service_name:
        base_metrics["fps"] = random.randint(25, 30)
        base_metrics["inference_time_ms"] = round(random.uniform(30, 80), 2)
    
    if "Scoring" in service_name:
        base_metrics["calculations_per_sec"] = random.randint(50, 200)
    
    if "Worker" in service_name:
        base_metrics["queue_size"] = random.randint(0, 50)
        base_metrics["processed_items"] = random.randint(1000, 10000)
    
    return base_metrics


async def send_heartbeat(client: httpx.AsyncClient, service_name: str):
    """Send a single heartbeat"""
    # Randomly assign status (mostly ok, occasionally warning/error)
    status_weights = [0.85, 0.10, 0.05]  # ok, warning, error
    status = random.choices(["ok", "warning", "error"], weights=status_weights)[0]
    
    heartbeat_data = {
        "service_name": service_name,
        "status": status,
        "metrics": generate_metrics(service_name)
    }
    
    try:
        response = await client.post(
            f"{API_URL}/api/heartbeat",
            json=heartbeat_data,
            timeout=5.0
        )
        
        if response.status_code == 201:
            print(f"✓ {service_name}: [{status.upper()}] - Heartbeat sent")
        else:
            print(f"✗ {service_name}: Error {response.status_code}")
    
    except Exception as e:
        print(f"✗ {service_name}: Failed to send heartbeat - {e}")


async def heartbeat_loop():
    """Main loop to send heartbeats every 5 seconds"""
    print("=" * 80)
    print("FJAIPOS HEARTBEAT SIMULATOR")
    print("=" * 80)
    print(f"Backend URL: {API_URL}")
    print(f"Services: {len(SERVICES)}")
    print(f"Interval: 5 seconds")
    print("=" * 80)
    print("\nStarting heartbeat simulation...\n")
    
    async with httpx.AsyncClient() as client:
        iteration = 0
        
        while True:
            iteration += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Heartbeat Round #{iteration}")
            print("-" * 80)
            
            # Send heartbeats from all services
            tasks = [send_heartbeat(client, service) for service in SERVICES]
            await asyncio.gather(*tasks)
            
            print(f"\n✓ Sent {len(SERVICES)} heartbeats")
            
            # Wait 5 seconds before next round
            await asyncio.sleep(5)


if __name__ == "__main__":
    try:
        asyncio.run(heartbeat_loop())
    except KeyboardInterrupt:
        print("\n\n✓ Heartbeat simulator stopped")
