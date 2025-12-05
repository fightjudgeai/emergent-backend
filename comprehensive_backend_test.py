#!/usr/bin/env python3
"""
Comprehensive Backend Testing for 25 Microservices
Testing Professional CV Analytics, Social Media Integration, Branding & Themes
"""

import requests
import sys
import json
import time
from datetime import datetime

class ComprehensiveBackendTester:
    def __init__(self, base_url="https://fightdata.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        if headers is None:
            headers = {'Content-Type': 'application/json'}

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            
            result = {
                'test': name,
                'success': success,
                'expected_status': expected_status,
                'actual_status': response.status_code,
                'url': url
            }
            
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    result['response'] = response.json()
                except:
                    result['response'] = response.text[:200]
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:200]}")
                result['error'] = response.text[:200]

            self.results.append(result)
            return success, response.json() if success and response.text else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {
                'test': name,
                'success': False,
                'error': str(e),
                'url': url
            }
            self.results.append(result)
            return False, {}

    def test_professional_cv_analytics(self):
        """Test Professional CV Analytics endpoints"""
        print("\n🎯 Testing Professional CV Analytics (CRITICAL)...")
        
        # Test data
        bout_id = "test_bout_001"
        fighter_id = "fighter_001"
        round_num = 1
        
        all_success = True
        
        # 1. GET /api/pro-cv/metrics/{bout_id}/fie - FIE metrics
        success1, response1 = self.run_test(
            "Pro CV - FIE Metrics", 
            "GET", 
            f"pro-cv/metrics/{bout_id}/fie?fighter_id={fighter_id}&round_num={round_num}", 
            200
        )
        
        if success1 and response1:
            print(f"   ✅ FIE Metrics: Strike accuracy {response1.get('strike_accuracy', 0)}%, Power {response1.get('avg_strike_power', 0)}")
        else:
            all_success = False
        
        # 2. POST /api/pro-cv/strikes/classify - Strike classification
        strike_data = {
            "video_frame_data": {"frame": "mock_frame_data"},
            "fighter_pose": {"pose": "mock_pose_data"}
        }
        success2, response2 = self.run_test(
            "Pro CV - Strike Classification", 
            "POST", 
            "pro-cv/strikes/classify", 
            200, 
            strike_data
        )
        
        if success2 and response2:
            print(f"   ✅ Strike Classification: Type {response2.get('strike_type', 'N/A')}, Power {response2.get('power_rating', 0)}")
        else:
            all_success = False
        
        # 3. POST /api/pro-cv/defense/detect - Defense detection
        defense_data = {
            "defender_pose": {"pose": "mock_defender_pose"},
            "incoming_strike": {"strike_type": "jab", "power_rating": 7.5}
        }
        success3, response3 = self.run_test(
            "Pro CV - Defense Detection", 
            "POST", 
            "pro-cv/defense/detect", 
            200, 
            defense_data
        )
        
        if success3 and response3:
            print(f"   ✅ Defense Detection: Type {response3.get('defense_type', 'N/A')}, Effectiveness {response3.get('effectiveness', 0)}%")
        else:
            all_success = False
        
        # 4. POST /api/pro-cv/ground/takedown - Takedown detection
        takedown_data = {
            "video_frames": [{"frame": "mock_frame"}],
            "fighter_poses": [{"pose": "mock_pose"}]
        }
        success4, response4 = self.run_test(
            "Pro CV - Takedown Detection", 
            "POST", 
            "pro-cv/ground/takedown", 
            200, 
            takedown_data
        )
        
        if success4 and response4:
            print(f"   ✅ Takedown Detection: {response4.get('message', 'Takedown analyzed')}")
        else:
            all_success = False
        
        # 5. GET /api/pro-cv/damage/{fighter_id}/heatmap - Damage heatmap
        success5, response5 = self.run_test(
            "Pro CV - Damage Heatmap", 
            "GET", 
            f"pro-cv/damage/{fighter_id}/heatmap", 
            200
        )
        
        if success5 and response5:
            print(f"   ✅ Damage Heatmap: Fighter {response5.get('fighter_id', 'N/A')}")
        else:
            all_success = False
        
        # 6. GET /api/pro-cv/momentum/{bout_id}/{round_num} - Momentum analysis
        success6, response6 = self.run_test(
            "Pro CV - Momentum Analysis", 
            "GET", 
            f"pro-cv/momentum/{bout_id}/{round_num}", 
            200
        )
        
        if success6 and response6:
            print(f"   ✅ Momentum Analysis: Dominant fighter {response6.get('dominant_fighter', 'N/A')}")
        else:
            all_success = False
        
        # 7. GET /api/pro-cv/live/{bout_id} - Live stats
        success7, response7 = self.run_test(
            "Pro CV - Live Stats", 
            "GET", 
            f"pro-cv/live/{bout_id}", 
            200
        )
        
        if success7 and response7:
            print(f"   ✅ Live Stats: Fighter 1 accuracy {response7.get('fighter_1', {}).get('strike_accuracy', 0)}%")
        else:
            all_success = False
        
        return all_success
    
    def test_social_media_integration(self):
        """Test Social Media Integration endpoints"""
        print("\n📱 Testing Social Media Integration...")
        
        all_success = True
        
        # 1. POST /api/social/twitter/post - Tweet posting
        success1, response1 = self.run_test(
            "Social Media - Twitter Post", 
            "POST", 
            "social/twitter/post?content=Test tweet from Combat Judging API", 
            200
        )
        
        if success1 and response1:
            print(f"   ✅ Twitter Post: {response1.get('content', 'Posted successfully')}")
        else:
            all_success = False
        
        # 2. POST /api/social/instagram/story - Instagram story
        story_data = {
            "story_type": "round_score",
            "fighter_1": "Connor McGregor",
            "fighter_2": "Dustin Poirier",
            "round": 1,
            "score": "10-9"
        }
        success2, response2 = self.run_test(
            "Social Media - Instagram Story", 
            "POST", 
            "social/instagram/story", 
            200, 
            story_data
        )
        
        if success2 and response2:
            print(f"   ✅ Instagram Story: {response2.get('story_type', 'Posted successfully')}")
        else:
            all_success = False
        
        # 3. POST /api/social/auto/round-score - Auto-post round scores
        round_score_data = {
            "bout_id": "test_bout_001",
            "round_num": 1,
            "fighter_1_name": "Connor McGregor",
            "fighter_2_name": "Dustin Poirier",
            "score": "10-9",
            "winner": "Connor McGregor"
        }
        success3, response3 = self.run_test(
            "Social Media - Auto Round Score", 
            "POST", 
            "social/auto/round-score", 
            200, 
            round_score_data
        )
        
        if success3 and response3:
            print(f"   ✅ Auto Round Score: Posted to {response3.get('platforms_posted', 0)} platforms")
        else:
            all_success = False
        
        # 4. GET /api/social/posts - Get posts
        success4, response4 = self.run_test(
            "Social Media - Get Posts", 
            "GET", 
            "social/posts", 
            200
        )
        
        if success4 and response4:
            posts_count = response4.get('count', 0)
            print(f"   ✅ Get Posts: Retrieved {posts_count} posts")
        else:
            all_success = False
        
        return all_success
    
    def test_branding_themes(self):
        """Test Branding & Themes endpoints"""
        print("\n🎨 Testing Branding & Themes...")
        
        all_success = True
        created_theme_id = None
        
        # 1. POST /api/branding/themes - Create theme
        theme_data = {
            "theme_id": "test_theme_001",
            "name": "UFC Test Theme",
            "primary_color": "#FF0000",
            "secondary_color": "#000000",
            "accent_color": "#FFFFFF",
            "logo_url": "https://example.com/logo.png",
            "font_family": "Arial, sans-serif",
            "created_by": "test_user"
        }
        success1, response1 = self.run_test(
            "Branding - Create Theme", 
            "POST", 
            "branding/themes", 
            201, 
            theme_data
        )
        
        if success1 and response1:
            created_theme_id = response1.get('theme_id', theme_data['theme_id'])
            print(f"   ✅ Create Theme: {response1.get('name', 'Theme created')} (ID: {created_theme_id})")
        else:
            all_success = False
        
        # 2. POST /api/branding/themes/{id}/activate - Activate theme
        if created_theme_id:
            success2, response2 = self.run_test(
                "Branding - Activate Theme", 
                "POST", 
                f"branding/themes/{created_theme_id}/activate", 
                200
            )
            
            if success2 and response2:
                print(f"   ✅ Activate Theme: {response2.get('success', False)}")
            else:
                all_success = False
        else:
            print("   ❌ Skipping activate theme test - no theme ID")
            all_success = False
        
        # 3. GET /api/branding/themes/active - Get active theme
        success3, response3 = self.run_test(
            "Branding - Get Active Theme", 
            "GET", 
            "branding/themes/active", 
            200
        )
        
        if success3 and response3:
            active_theme = response3.get('name', response3.get('message', 'Active theme retrieved'))
            print(f"   ✅ Get Active Theme: {active_theme}")
        else:
            all_success = False
        
        # 4. GET /api/branding/themes/{id}/css - Generate CSS
        if created_theme_id:
            success4, response4 = self.run_test(
                "Branding - Generate CSS", 
                "GET", 
                f"branding/themes/{created_theme_id}/css", 
                200
            )
            
            if success4 and response4:
                css_length = len(response4.get('css', ''))
                print(f"   ✅ Generate CSS: {css_length} characters generated")
            else:
                all_success = False
        else:
            print("   ❌ Skipping CSS generation test - no theme ID")
            all_success = False
        
        return all_success
    
    def test_previously_built_services(self):
        """Test previously built services are still working"""
        print("\n🔧 Testing Previously Built Services...")
        
        all_success = True
        
        # Test Fighter Analytics health
        success1, _ = self.run_test("Fighter Analytics Health", "GET", "fighter-analytics/health", 200)
        if success1:
            print("   ✅ Fighter Analytics - Operational")
        else:
            all_success = False
        
        # Test CV Moments AI health
        success2, _ = self.run_test("CV Moments AI Health", "GET", "cv-moments/health", 200)
        if success2:
            print("   ✅ CV Moments AI - Operational")
        else:
            all_success = False
        
        # Test Blockchain Audit health
        success3, _ = self.run_test("Blockchain Audit Health", "GET", "blockchain-audit/health", 200)
        if success3:
            print("   ✅ Blockchain Audit - Operational")
        else:
            all_success = False
        
        # Test Broadcast Control health
        success4, _ = self.run_test("Broadcast Control Health", "GET", "broadcast-control/health", 200)
        if success4:
            print("   ✅ Broadcast Control - Operational")
        else:
            all_success = False
        
        # Test Heartbeat Monitor health
        success5, _ = self.run_test("Heartbeat Monitor Health", "GET", "heartbeat/health", 200)
        if success5:
            print("   ✅ Heartbeat Monitor - Operational")
        else:
            all_success = False
        
        # Test Performance Profiler health
        success6, _ = self.run_test("Performance Profiler Health", "GET", "perf/health", 200)
        if success6:
            print("   ✅ Performance Profiler - Operational")
        else:
            all_success = False
        
        # Test Calibration API health
        success7, _ = self.run_test("Calibration API Health", "GET", "calibration/health", 200)
        if success7:
            print("   ✅ Calibration API - Operational")
        else:
            all_success = False
        
        return all_success
    
    def run_comprehensive_tests(self):
        """Test all 25 microservices comprehensively"""
        print("\n🚀 COMPREHENSIVE BACKEND TESTING - All 25 Microservices")
        print("="*70)
        
        all_tests_passed = True
        
        # PRIORITY 1: Professional CV Analytics (CRITICAL)
        print("\n🎯 PRIORITY 1: Professional CV Analytics (CRITICAL)")
        if not self.test_professional_cv_analytics():
            all_tests_passed = False
        
        # PRIORITY 2: Social Media Integration
        print("\n📱 PRIORITY 2: Social Media Integration")
        if not self.test_social_media_integration():
            all_tests_passed = False
        
        # PRIORITY 3: Branding & Themes
        print("\n🎨 PRIORITY 3: Branding & Themes")
        if not self.test_branding_themes():
            all_tests_passed = False
        
        # PRIORITY 4: Previously Built Services
        print("\n🔧 PRIORITY 4: Previously Built Services")
        if not self.test_previously_built_services():
            all_tests_passed = False
        
        # Print final results
        print(f"\n{'='*60}")
        print(f"🏁 COMPREHENSIVE BACKEND TEST COMPLETE")
        print(f"{'='*60}")
        print(f"✅ Tests Passed: {self.tests_passed}")
        print(f"❌ Tests Failed: {self.tests_run - self.tests_passed}")
        print(f"📊 Total Tests: {self.tests_run}")
        print(f"🎯 Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if all_tests_passed:
            print("🎉 ALL COMPREHENSIVE BACKEND TESTS PASSED!")
        else:
            print("⚠️  Some comprehensive backend tests failed.")
        
        return all_tests_passed

if __name__ == "__main__":
    import os
    base_url = os.environ.get('BACKEND_URL', 'https://fightdata.preview.emergentagent.com')
    
    tester = ComprehensiveBackendTester(base_url)
    success = tester.run_comprehensive_tests()
    sys.exit(0 if success else 1)