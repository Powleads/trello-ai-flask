#!/usr/bin/env python3
"""
Automated Testing Script for Google Meet to Trello AI App
"""

import requests
import json
import sys
from datetime import datetime

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
    status = "[PASS]" if success else "[FAIL]"
    print(f"{status} - {test_name}")
    if details:
        print(f"    Details: {details}")

def test_server():
    """Test if server is running"""
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        log_test("Server Running", response.status_code == 200, f"Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        log_test("Server Running", False, str(e))
        return False

def test_demo_mode():
    """Test demo analyze functionality"""
    try:
        response = requests.post(f"{BASE_URL}/api/demo-analyze", json={}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            success = data.get("success") == True and "speakers" in data
            speakers = len(data.get("speakers", {}))
            log_test("Demo Mode API", success, f"Found {speakers} speakers")
            return success
        else:
            log_test("Demo Mode API", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Demo Mode API", False, str(e))
        return False

def test_speaker_analysis():
    """Test speaker analysis"""
    transcript = """
    James: Let's review our progress.
    Criselle: The WordPress site is 80% complete.
    Lancey: I'll help with testing.
    """
    
    try:
        response = requests.post(f"{BASE_URL}/api/analyze-speakers",
                                json={"transcript": transcript}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            success = data.get("success") == True
            speakers = len(data.get("speakers", {}))
            log_test("Speaker Analysis", success, f"Analyzed {speakers} speakers")
            
            # Check metrics
            if "metrics" in data:
                balance = data["metrics"].get("participation_balance", "unknown")
                log_test("  Participation Balance", True, balance)
            
            return success
        else:
            log_test("Speaker Analysis", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Speaker Analysis", False, str(e))
        return False

def test_summary():
    """Test summary generation"""
    transcript = """
    James: I'll handle the design review.
    Criselle: We decided to use the new approach.
    Lancey: I'll update the documentation.
    """
    
    try:
        response = requests.post(f"{BASE_URL}/api/generate-summary",
                                json={"transcript": transcript}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            if data.get("success") and "summary" in data:
                summary = data["summary"]
                actions = len(summary.get("action_items", []))
                log_test("Summary Generation", True, f"{actions} action items found")
                return True
            else:
                log_test("Summary Generation", False, "No summary data")
                return False
        else:
            log_test("Summary Generation", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Summary Generation", False, str(e))
        return False

def test_whatsapp():
    """Test WhatsApp integration"""
    suggestions = {
        "Criselle": ["Great work!", "Keep it up!"],
        "Lancey": ["Excellent collaboration!"]
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/send-whatsapp",
                                json={"suggestions": suggestions}, timeout=10)
        if response.status_code == 200:
            data = response.json()
            success = data.get("success") == True
            recipients = data.get("total_recipients", 0)
            log_test("WhatsApp API", success, f"{recipients} recipients")
            return success
        else:
            log_test("WhatsApp API", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("WhatsApp API", False, str(e))
        return False

def test_ui():
    """Test UI components"""
    try:
        response = requests.get(f"{BASE_URL}/google-meet", timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # Check for key components
            components = {
                "Demo Tab": "demo-tab" in html,
                "URL Tab": "url-tab" in html,
                "Text Tab": "text-tab" in html,
                "Process Button": "process-btn" in html,
                "Results Section": "results-section" in html
            }
            
            all_present = True
            for name, present in components.items():
                log_test(f"  UI: {name}", present)
                all_present = all_present and present
            
            log_test("UI Components", all_present, f"{sum(components.values())}/{len(components)} found")
            return all_present
        else:
            log_test("UI Components", False, f"Status: {response.status_code}")
            return False
    except Exception as e:
        log_test("UI Components", False, str(e))
        return False

def test_all_routes():
    """Test all API routes"""
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
    
    print("\n--- Testing All Routes ---")
    all_pass = True
    for method, route in routes:
        try:
            if method == "GET":
                response = requests.get(f"{BASE_URL}{route}", timeout=5)
            else:
                response = requests.post(f"{BASE_URL}{route}", json={}, timeout=5)
            
            success = response.status_code != 404
            log_test(f"  {method} {route}", success, f"Status: {response.status_code}")
            all_pass = all_pass and success
        except Exception as e:
            log_test(f"  {method} {route}", False, str(e))
            all_pass = False
    
    return all_pass

def test_end_to_end():
    """Test complete workflow"""
    print("\n--- End-to-End Workflow Test ---")
    
    transcript = """
    James: Let's review our weekly progress.
    Criselle: WordPress migration is complete.
    Lancey: I'll test everything tomorrow.
    James: Great teamwork everyone!
    """
    
    try:
        # Step 1: Analyze
        response = requests.post(f"{BASE_URL}/api/analyze-speakers",
                                json={"transcript": transcript}, timeout=10)
        if response.status_code != 200:
            log_test("E2E: Analysis", False, f"Status: {response.status_code}")
            return False
        
        analysis = response.json()
        speakers = len(analysis.get("speakers", {}))
        log_test("E2E: Analysis", True, f"{speakers} speakers analyzed")
        
        # Step 2: Summary
        response = requests.post(f"{BASE_URL}/api/generate-summary",
                                json={"transcript": transcript}, timeout=10)
        if response.status_code != 200:
            log_test("E2E: Summary", False, f"Status: {response.status_code}")
            return False
        
        summary = response.json()
        log_test("E2E: Summary", True, "Summary generated")
        
        # Step 3: WhatsApp
        suggestions = analysis.get("individual_suggestions", {})
        response = requests.post(f"{BASE_URL}/api/send-whatsapp",
                                json={"suggestions": suggestions}, timeout=10)
        if response.status_code != 200:
            log_test("E2E: WhatsApp", False, f"Status: {response.status_code}")
            return False
        
        whatsapp = response.json()
        log_test("E2E: WhatsApp", True, f"Messages prepared for {whatsapp.get('total_recipients', 0)} recipients")
        
        return True
        
    except Exception as e:
        log_test("End-to-End Workflow", False, str(e))
        return False

def generate_report():
    """Generate test report"""
    print("\n" + "="*50)
    print("TEST REPORT SUMMARY")
    print("="*50)
    
    total = len(TEST_RESULTS)
    passed = sum(1 for r in TEST_RESULTS if r["success"])
    failed = total - passed
    
    print(f"Total Tests: {total}")
    print(f"Passed: {passed} ({(passed/total*100):.1f}%)" if total > 0 else "Passed: 0")
    print(f"Failed: {failed}")
    
    if failed > 0:
        print("\nFailed Tests:")
        for result in TEST_RESULTS:
            if not result["success"]:
                print(f"  - {result['test']}: {result.get('details', 'No details')}")
    
    # Save report
    report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_file, 'w') as f:
        json.dump(TEST_RESULTS, f, indent=2)
    print(f"\nDetailed report saved to: {report_file}")
    
    return passed == total

def main():
    """Run all tests"""
    print("="*50)
    print("AUTOMATED TESTING - Google Meet to Trello AI")
    print("="*50)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Testing: {BASE_URL}\n")
    
    # Check server
    if not test_server():
        print("\n[ERROR] Server is not running!")
        print("Please start the Flask application first.")
        return False
    
    print("\n--- Core Features ---")
    test_demo_mode()
    test_speaker_analysis()
    test_summary()
    test_whatsapp()
    
    print("\n--- UI Testing ---")
    test_ui()
    
    # All routes
    test_all_routes()
    
    # End-to-end
    test_end_to_end()
    
    # Report
    all_passed = generate_report()
    
    if all_passed:
        print("\n[SUCCESS] ALL TESTS PASSED!")
        print("The application is working correctly.")
    else:
        print("\n[WARNING] SOME TESTS FAILED!")
        print("Please review the report for details.")
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)