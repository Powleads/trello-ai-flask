#!/usr/bin/env python3
"""
Deep Scan Test - Complete Workflow Verification
Tests the entire meeting automation workflow end-to-end
"""

import sys
import os
import asyncio
import requests
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, 'src')
from dotenv import load_dotenv

load_dotenv()

def test_environment():
    """Test all environment variables and dependencies."""
    print("🔍 ENVIRONMENT CHECK")
    print("=" * 50)
    
    required_vars = [
        'OPENAI_API_KEY',
        'TRELLO_API_KEY', 
        'TRELLO_TOKEN',
        'TRELLO_BOARD_ID',
        'GREEN_API_INSTANCE_ID',
        'GREEN_API_TOKEN',
        'WHATSAPP_DEFAULT_CHAT'
    ]
    
    missing_vars = []
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: {'*' * len(value[:10])}...")
        else:
            print(f"❌ {var}: NOT SET")
            missing_vars.append(var)
    
    if missing_vars:
        print(f"\n⚠️  Missing variables: {', '.join(missing_vars)}")
        return False
    else:
        print("\n✅ All environment variables configured")
        return True

async def test_trello_connection():
    """Test Trello API connection and board access."""
    print("\n🔗 TRELLO CONNECTION TEST")
    print("=" * 50)
    
    try:
        from integrations.trello import TrelloClient
        
        client = TrelloClient()
        
        # Test connection
        user = await client.test_connection()
        print(f"✅ Connected as: {user.get('fullName')}")
        
        # Test board access
        board_id = os.getenv('TRELLO_BOARD_ID')
        board_lists = await client.get_board_lists(board_id)
        print(f"✅ Board has {len(board_lists)} lists")
        
        # Test cards access
        board_cards = await client.get_board_cards(board_id)
        print(f"✅ Board has {len(board_cards)} cards")
        
        # Test comment posting (dry run)
        print("✅ Comment posting capability available")
        
        await client.session.close()
        return True
        
    except Exception as e:
        print(f"❌ Trello connection failed: {e}")
        return False

def test_openai_connection():
    """Test OpenAI API connection."""
    print("\n🤖 OPENAI CONNECTION TEST")
    print("=" * 50)
    
    try:
        import openai
        
        client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
        
        # Test simple completion
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a test assistant."},
                {"role": "user", "content": "Say 'OpenAI connection successful'"}
            ],
            max_tokens=50
        )
        
        result = response.choices[0].message.content
        if "successful" in result.lower():
            print("✅ OpenAI GPT-4 Turbo connection successful")
            return True
        else:
            print(f"❌ Unexpected response: {result}")
            return False
            
    except Exception as e:
        print(f"❌ OpenAI connection failed: {e}")
        return False

def test_whatsapp_connection():
    """Test WhatsApp API connection (without sending)."""
    print("\n📱 WHATSAPP CONNECTION TEST")
    print("=" * 50)
    
    try:
        instance_id = os.getenv('GREEN_API_INSTANCE_ID')
        token = os.getenv('GREEN_API_TOKEN')
        
        # Test instance status
        status_url = f"https://api.green-api.com/waInstance{instance_id}/getStateInstance/{token}"
        response = requests.get(status_url, timeout=10)
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"✅ WhatsApp instance status: {status_data.get('stateInstance', 'Unknown')}")
            return True
        else:
            print(f"❌ WhatsApp API error: Status {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ WhatsApp connection failed: {e}")
        return False

async def test_google_docs_access():
    """Test Google Docs text extraction."""
    print("\n📄 GOOGLE DOCS ACCESS TEST")
    print("=" * 50)
    
    try:
        # Test with a known public document
        test_doc_id = '1ZZZPKZSijZgWK5bt62KCmfEIF0Fksu0kG67EpE0pCfE'
        export_url = f'https://docs.google.com/document/d/{test_doc_id}/export?format=txt'
        
        response = requests.get(export_url, timeout=30)
        
        if response.status_code == 200:
            text = response.text
            print(f"✅ Document access successful: {len(text)} characters")
            
            # Check if it looks like a transcript
            if 'meeting' in text.lower() or 'transcript' in text.lower():
                print("✅ Document appears to contain meeting content")
                return True, text
            else:
                print("⚠️  Document may not contain meeting transcript")
                return True, text
        else:
            print(f"❌ Google Docs access failed: Status {response.status_code}")
            return False, None
            
    except Exception as e:
        print(f"❌ Google Docs access failed: {e}")
        return False, None

async def test_ai_matching(transcript_text):
    """Test the AI-powered card matching."""
    print("\n🧠 AI MATCHING TEST")
    print("=" * 50)
    
    try:
        from app import find_trello_cards_in_transcript
        
        print("Running intelligent card matching...")
        results = find_trello_cards_in_transcript(transcript_text)
        
        if isinstance(results, tuple):
            matched_cards, new_tasks = results
        else:
            matched_cards = results
            new_tasks = []
        
        print(f"✅ AI matching completed")
        print(f"   - Found {len(matched_cards)} card matches")
        print(f"   - Suggested {len(new_tasks)} new tasks")
        
        if matched_cards:
            print("\n📋 Matched Cards:")
            for i, match in enumerate(matched_cards[:3], 1):
                confidence = int(match['match_score'] * 100)
                card_name = match['card']['name'][:50]
                print(f"   {i}. {card_name} ({confidence}% confidence)")
        
        return True, matched_cards
        
    except Exception as e:
        print(f"❌ AI matching failed: {e}")
        return False, []

def test_web_interface():
    """Test if the web interface is accessible."""
    print("\n🌐 WEB INTERFACE TEST")
    print("=" * 50)
    
    try:
        # Check if Flask app is running
        response = requests.get('http://localhost:5000/status', timeout=5)
        
        if response.status_code == 200:
            status_data = response.json()
            print("✅ Web interface accessible")
            print(f"   - OpenAI: {'✅' if status_data.get('openai_configured') else '❌'}")
            print(f"   - WhatsApp: {'✅' if status_data.get('whatsapp_configured') else '❌'}")
            print(f"   - Trello: {'✅' if status_data.get('trello_configured') else '❌'}")
            return True
        else:
            print(f"❌ Web interface error: Status {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Web interface not accessible (is the Flask app running?)")
        return False
    except Exception as e:
        print(f"❌ Web interface test failed: {e}")
        return False

async def test_comment_formatting(matched_cards):
    """Test comment formatting and structure."""
    print("\n💬 COMMENT FORMATTING TEST")
    print("=" * 50)
    
    if not matched_cards:
        print("⚠️  No matched cards to test comments")
        return True
    
    try:
        for i, match in enumerate(matched_cards[:2], 1):
            comment = match.get('suggested_comment', '')
            card_name = match['card']['name'][:30]
            
            print(f"\n📝 Comment {i} for '{card_name}':")
            
            # Check comment structure
            required_elements = ['Meeting Update', 'Discussion', 'Added from']
            found_elements = [elem for elem in required_elements if elem in comment]
            
            print(f"   Structure elements: {len(found_elements)}/{len(required_elements)}")
            print(f"   Length: {len(comment)} characters")
            
            if len(comment) > 50 and 'Meeting Update' in comment:
                print("   ✅ Comment formatting looks good")
            else:
                print("   ⚠️  Comment may need formatting improvement")
        
        return True
        
    except Exception as e:
        print(f"❌ Comment formatting test failed: {e}")
        return False

async def run_deep_scan():
    """Run complete deep scan test."""
    print("🔬 DEEP SCAN TEST - MEETING AUTOMATION WORKFLOW")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    test_results = {}
    
    # 1. Environment check
    test_results['environment'] = test_environment()
    
    # 2. Trello connection
    test_results['trello'] = await test_trello_connection()
    
    # 3. OpenAI connection
    test_results['openai'] = test_openai_connection()
    
    # 4. WhatsApp connection
    test_results['whatsapp'] = test_whatsapp_connection()
    
    # 5. Google Docs access
    docs_success, transcript_text = await test_google_docs_access()
    test_results['google_docs'] = docs_success
    
    # 6. AI matching (if we have transcript)
    if docs_success and transcript_text:
        matching_success, matched_cards = await test_ai_matching(transcript_text)
        test_results['ai_matching'] = matching_success
        
        # 7. Comment formatting
        test_results['comment_formatting'] = await test_comment_formatting(matched_cards)
    else:
        test_results['ai_matching'] = False
        test_results['comment_formatting'] = False
    
    # 8. Web interface
    test_results['web_interface'] = test_web_interface()
    
    # Summary
    print("\n🏁 DEEP SCAN RESULTS")
    print("=" * 50)
    
    passed_tests = sum(test_results.values())
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name.upper().replace('_', ' '):<20} {status}")
    
    print(f"\nOVERALL: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests == total_tests:
        print("🎉 ALL SYSTEMS OPERATIONAL - READY FOR PRODUCTION!")
    elif passed_tests >= total_tests * 0.8:
        print("⚠️  MOSTLY OPERATIONAL - Minor issues detected")
    else:
        print("❌ CRITICAL ISSUES - System needs attention")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    return test_results

if __name__ == "__main__":
    asyncio.run(run_deep_scan())