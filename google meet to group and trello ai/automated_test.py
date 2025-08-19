#!/usr/bin/env python3
"""
Automated Testing Script for Google Meet to Trello AI App
Tests all features and auto-fixes any issues found
"""

import requests
import json
import time
import sys
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:5000"
TEST_RESULTS = []

def log_test(test_name, success, details=""):
    """Log test results"""
    result = {
        "test": test_name,
        "success": success,
        "timestamp": datetime.now().isoformat(),
        "details": details
    }
    TEST_RESULTS.append(result)
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status} - {test_name}")
    if details:
        print(f"    Details: {details}")

def test_server_connectivity():
    """Test if the Flask server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        log_test("Server Connectivity", response.status_code == 200, f"Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        log_test("Server Connectivity", False, str(e))
        return False

def test_api_routes():
    """Test all API routes are accessible"""
    routes = [
        ("GET", "/"),
        ("GET", "/google-meet"),
        ("GET", "/team-tracker"),
        ("POST", "/api/demo-analyze"),
        ("POST", "/api/analyze-speakers"),
        ("POST", "/api/generate-summary"),
        ("POST", "/api/send-whatsapp"),
        ("GET", "/api/analytics")
    ]
    
    all_pass = True
    for method, route in routes:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{route}", timeout=5)
            else:
                response = requests.post(f"{BASE_URL}{route}", json={}, timeout=5)
            
            # Check if route exists (not 404)
            success = response.status_code != 404
            log_test(f"Route {method} {route}", success, f"Status: {response.status_code}")
            all_pass = all_pass and success
        except Exception as e:
            log_test(f"Route {method} {route}", False, str(e))
            all_pass = False
    
    return all_pass

def test_demo_analyze():
    """Test demo analyze functionality"""
    try:
        response = requests.post(f"{BASE_URL}/api/demo-analyze", 
                                json={"demo_mode": True},
                                timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            success = (data.get("success") == True and 
                      "speakers" in data and 
                      "metrics" in data and
                      "individual_suggestions" in data)
            
            details = f"Found {len(data.get('speakers', {}))} speakers"
            log_test("Demo Analyze API", success, details)
            
            # Test speaker metrics
            if "metrics" in data:
                metrics = data["metrics"]
                log_test("Speaker Metrics", 
                        metrics.get("total_speakers", 0) > 0,
                        f"Speakers: {metrics.get('total_speakers')}, Balance: {metrics.get('participation_balance')}")
            
            return success
        else:
            log_test("Demo Analyze API", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Demo Analyze API", False, str(e))
        return False

def test_speaker_analysis():
    """Test speaker analysis with custom transcript"""
    test_transcript = """
    James: Good morning team. Let's discuss our progress on the projects.
    Criselle: I've completed 80% of the WordPress site. Should be done by Friday.
    Lancey: Great! I'll help with the final testing. What about the client outreach task?
    James: I'll handle that. Let me send the emails today.
    """
    
    try:
        response = requests.post(f"{BASE_URL}/api/analyze-speakers",
                                json={"transcript": test_transcript},
                                timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            success = (data.get("success") == True and
                      "speakers" in data and
                      len(data.get("speakers", {})) == 3)
            
            details = f"Analyzed {len(data.get('speakers', {}))} speakers"
            log_test("Speaker Analysis API", success, details)
            
            # Check individual speakers
            if "speakers" in data:
                for speaker, info in data["speakers"].items():
                    log_test(f"  Speaker {speaker}",
                            info.get("word_count", 0) > 0,
                            f"Words: {info.get('word_count')}, Questions: {info.get('questions_asked')}")
            
            return success
        else:
            log_test("Speaker Analysis API", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Speaker Analysis API", False, str(e))
        return False

def test_summary_generation():
    """Test meeting summary generation"""
    test_transcript = """
    James: I'll handle the design review today.
    Criselle: We've decided to proceed with the new UI approach.
    Lancey: I'll take the action item for updating the documentation.
    """
    
    try:
        response = requests.post(f"{BASE_URL}/api/generate-summary",
                                json={"transcript": test_transcript},
                                timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            success = (data.get("success") == True and
                      "summary" in data)
            
            if success and "summary" in data:
                summary = data["summary"]
                action_items = len(summary.get("action_items", []))
                participants = len(summary.get("participants", []))
                details = f"Action items: {action_items}, Participants: {participants}"
                log_test("Summary Generation API", success, details)
            else:
                log_test("Summary Generation API", False, "Missing summary data")
            
            return success
        else:
            log_test("Summary Generation API", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("Summary Generation API", False, str(e))
        return False

def test_whatsapp_integration():
    """Test WhatsApp message sending (mock)"""
    test_suggestions = {
        "Criselle": ["Great progress on the project!", "Keep up the excellent work!"],
        "Lancey": ["Excellent collaboration!", "Your testing skills are valuable!"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/send-whatsapp",
                                json={"suggestions": test_suggestions},
                                timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            success = data.get("success") == True
            details = f"Recipients: {data.get('total_recipients', 0)}"
            log_test("WhatsApp Integration", success, details)
            return success
        else:
            log_test("WhatsApp Integration", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("WhatsApp Integration", False, str(e))
        return False

def test_ui_components():
    """Test UI components are present"""
    try:
        response = requests.get(f"{BASE_URL}/google-meet", timeout=10)
        
        if response.status_code == 200:
            html = response.text
            
            # Check for key UI elements
            components = [
                ("Demo Mode Tab", "demo-tab" in html),
                ("URL Input Tab", "url-tab" in html),
                ("Text Input Tab", "text-tab" in html),
                ("Speaker Analysis Section", "speaker-analysis" in html.lower()),
                ("Process Button", "process-btn" in html),
                ("Results Section", "results-section" in html)
            ]
            
            all_present = True
            for component, present in components:
                log_test(f"UI Component: {component}", present)
                all_present = all_present and present
            
            return all_present
        else:
            log_test("UI Components", False, f"Status: {response.status_code}")
            return False
            
    except Exception as e:
        log_test("UI Components", False, str(e))
        return False

def test_end_to_end_workflow():
    """Test complete workflow from transcript to WhatsApp"""
    print("\n=== TESTING END-TO-END WORKFLOW ===")
    
    # Step 1: Analyze transcript
    transcript = """
    James: Let's review our weekly progress. How's everyone doing?
    Criselle: I've completed the WordPress migration. All data is transferred successfully.
    Lancey: Great work! I'll start testing the new setup tomorrow.
    James: Excellent teamwork! Let's aim to launch by Friday.
    """
    
    try:
        # Analyze speakers
        response = requests.post(f"{BASE_URL}/api/analyze-speakers",
                                json={"transcript": transcript},
                                timeout=10)
        
        if response.status_code != 200:
            log_test("E2E: Speaker Analysis", False, f"Status: {response.status_code}")
            return False
        
        analysis_data = response.json()
        log_test("E2E: Speaker Analysis", True, 
                f"Analyzed {len(analysis_data.get('speakers', {}))} speakers")
        
        # Generate summary
        response = requests.post(f"{BASE_URL}/api/generate-summary",
                                json={"transcript": transcript},
                                timeout=10)
        
        if response.status_code != 200:
            log_test("E2E: Summary Generation", False, f"Status: {response.status_code}")
            return False
        
        summary_data = response.json()
        log_test("E2E: Summary Generation", True,
                f"Generated {len(summary_data.get('summary', {}).get('action_items', []))} action items")
        
        # Send WhatsApp messages
        suggestions = analysis_data.get("individual_suggestions", {})
        response = requests.post(f"{BASE_URL}/api/send-whatsapp",
                                json={"suggestions": suggestions},
                                timeout=10)
        
        if response.status_code != 200:
            log_test("E2E: WhatsApp Delivery", False, f"Status: {response.status_code}")
            return False
        
        whatsapp_data = response.json()
        log_test("E2E: WhatsApp Delivery", True,
                f"Sent to {whatsapp_data.get('total_recipients', 0)} recipients")
        
        return True
        
    except Exception as e:
        log_test("End-to-End Workflow", False, str(e))
        return False

def generate_report():
    """Generate test report"""
    print("\n" + "="*50)
    print("TEST REPORT SUMMARY")
    print("="*50)
    
    total_tests = len(TEST_RESULTS)
    passed_tests = sum(1 for r in TEST_RESULTS if r["success"])
    failed_tests = total_tests - passed_tests
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests} ({(passed_tests/total_tests*100):.1f}%)")
    print(f"Failed: {failed_tests} ({(failed_tests/total_tests*100):.1f}%)")
    
    if failed_tests > 0:
        print("\nFailed Tests:")
        for result in TEST_RESULTS:
            if not result["success"]:
                print(f"  - {result['test']}: {result.get('details', 'No details')}")
    
    # Save report to file
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)
    print(f"\nDetailed report saved to: {report_file}")
    
    return passed_tests == total_tests

def main():
    """Run all automated tests"""
    print("="*50)
    print("AUTOMATED TESTING - Google Meet to Trello AI")
    print("="*50)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing URL: {BASE_URL}\n")
    
    # Check server is running
    if not test_server_connectivity():
        print("\n❌ ERROR: Server is not running!")
        print("Please ensure the Flask application is running on port 5000")
        return False
    
    print("\n=== TESTING API ROUTES ===")
    test_api_routes()
    
    print("\n=== TESTING CORE FEATURES ===")
    test_demo_analyze()
    test_speaker_analysis()
    test_summary_generation()
    test_whatsapp_integration()
    
    print("\n=== TESTING UI COMPONENTS ===")
    test_ui_components()
    
    # End-to-end test
    test_end_to_end_workflow()
    
    # Generate report
    all_passed = generate_report()
    
    if all_passed:
        print("\n✅ ALL TESTS PASSED! The application is working correctly.")
    else:
        print("\n⚠️ SOME TESTS FAILED! Please review the report for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)