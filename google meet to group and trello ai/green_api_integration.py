#!/usr/bin/env python3
"""
Green API WhatsApp Integration Module
Handles all WhatsApp messaging functionality via Green API
"""

import os
import requests
import json
import time
from typing import Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

class GreenAPIClient:
    """Client for Green API WhatsApp integration."""
    
    def __init__(self, instance_id: str = None, api_token: str = None):
        """Initialize Green API client with credentials."""
        self.instance_id = instance_id or os.environ.get('GREEN_API_INSTANCE_ID', '7105263120')
        self.api_token = api_token or os.environ.get('GREEN_API_TOKEN')
        self.base_url = f"https://api.green-api.com/waInstance{self.instance_id}"
        
        print(f"[GREEN_API] Initializing with instance_id: {self.instance_id}")
        print(f"[GREEN_API] Token present: {'Yes' if self.api_token else 'No'}")
        print(f"[GREEN_API] Token length: {len(self.api_token) if self.api_token else 0}")
        
        if not self.api_token:
            raise ValueError("GREEN_API_TOKEN environment variable is required")
        
        if self.api_token == "your_green_api_token_here":
            raise ValueError("GREEN_API_TOKEN is still set to default placeholder value")
    
    def send_message(self, chat_id: str, message: str, quote_message_id: str = None) -> Dict:
        """
        Send WhatsApp message to specified chat.
        
        Args:
            chat_id: WhatsApp chat ID (phone number with @c.us)
            message: Message text to send
            quote_message_id: Optional message ID to quote/reply to
            
        Returns:
            Dict with response data from Green API
        """
        url = f"{self.base_url}/sendMessage/{self.api_token}"
        
        payload = {
            "chatId": chat_id,
            "message": message,
            "linkPreview": True
        }
        
        if quote_message_id:
            payload["quotedMessageId"] = quote_message_id
        
        try:
            print(f"[GREEN_API] Sending request to: {url}")
            print(f"[GREEN_API] Payload: {json.dumps(payload, indent=2)}")
            
            response = requests.post(url, json=payload, timeout=30)
            
            print(f"[GREEN_API] Response status: {response.status_code}")
            print(f"[GREEN_API] Response headers: {dict(response.headers)}")
            
            if response.status_code != 200:
                print(f"[GREEN_API] Response text: {response.text}")
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"[GREEN_API] Error sending WhatsApp message: {e}")
            return {"error": str(e)}
    
    def send_bulk_messages(self, messages: List[Dict]) -> List[Dict]:
        """
        Send multiple WhatsApp messages.
        
        Args:
            messages: List of message dicts with 'chat_id' and 'message' keys
            
        Returns:
            List of response dicts from Green API
        """
        results = []
        
        for msg in messages:
            result = self.send_message(msg['chat_id'], msg['message'])
            results.append({
                'chat_id': msg['chat_id'],
                'success': 'error' not in result,
                'response': result
            })
            
            # Add delay between messages to avoid rate limiting
            time.sleep(1)
        
        return results
    
    def get_account_info(self) -> Dict:
        """Get Green API account information."""
        url = f"{self.base_url}/getStateInstance/{self.api_token}"
        
        try:
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error getting account info: {e}")
            return {"error": str(e)}

class TeamUpdateMessenger:
    """Handles team update messaging logic."""
    
    def __init__(self):
        self.green_api = GreenAPIClient()
        
        # Team member mapping (from blueprint)
        self.team_members = {
            'Criselle': '639494048499@c.us',
            'Lancey': '639264438378@c.us',
            'Ezechiel': '23754071907@c.us',
            'Levy': '237659250977@c.us',
            'Wendy': '237677079267@c.us',
            'Forka': '237652275097@c.us',
            'Breyden': '13179979692@c.us',
            'Brayan': '237676267420@c.us'
        }
        
        self.group_chat = '447916991875@c.us'
    
    def create_update_request_message(self, member_name: str, cards: List[Dict]) -> str:
        """Create personalized update request message."""
        card_list = "\n".join([f"• {card['name']}\n{card['url']}" for card in cards])
        
        message = f"""Hello {member_name}, This is the JGV EEsystems AI Trello bot

Here are the tasks today that you are assigned to and have not had a comment recently:

{card_list}

Please click the links to open Trello and write a comment. If there is an issue, please contact James in the EEsystems group chat.

Thanks"""
        
        return message
    
    def create_unassigned_cards_message(self, cards: List[Dict]) -> str:
        """Create message for unassigned cards."""
        card_list = "\n".join([f"• {card['name']}: {card['url']}" for card in cards])
        
        message = f"""⚠️ URGENT: Unassigned Tasks Requiring Attention

The following cards need to be assigned immediately:
{card_list}

Please assign these tasks as soon as possible."""
        
        return message
    
    def create_escalation_message(self, member_name: str, cards: List[Dict]) -> str:
        """Create escalation message for persistent non-responders."""
        card_list = "\n".join([f"• {card['name']}: {card['url']}" for card in cards])
        
        message = f"""🚨 ESCALATION NOTICE

{member_name} has not responded to 3 update requests for the following tasks:
{card_list}

Immediate action required for task completion."""
        
        return message
    
    def send_individual_updates(self, cards_by_member: Dict[str, List[Dict]]) -> Dict:
        """Send update requests to individual team members."""
        results = {
            'messages_sent': 0,
            'failed_messages': 0,
            'responses': []
        }
        
        for member_name, cards in cards_by_member.items():
            if member_name not in self.team_members:
                print(f"Warning: No phone number found for {member_name}")
                continue
            
            chat_id = self.team_members[member_name]
            message = self.create_update_request_message(member_name, cards)
            
            response = self.green_api.send_message(chat_id, message)
            
            if 'error' not in response:
                results['messages_sent'] += 1
            else:
                results['failed_messages'] += 1
            
            results['responses'].append({
                'member': member_name,
                'chat_id': chat_id,
                'success': 'error' not in response,
                'response': response
            })
        
        return results
    
    def send_unassigned_notification(self, unassigned_cards: List[Dict]) -> Dict:
        """Send notification about unassigned cards to group."""
        if not unassigned_cards:
            return {'success': True, 'message': 'No unassigned cards'}
        
        message = self.create_unassigned_cards_message(unassigned_cards)
        response = self.green_api.send_message(self.group_chat, message)
        
        return {
            'success': 'error' not in response,
            'response': response
        }
    
    def send_escalation_notification(self, member_name: str, cards: List[Dict]) -> Dict:
        """Send escalation notification to group."""
        message = self.create_escalation_message(member_name, cards)
        response = self.green_api.send_message(self.group_chat, message)
        
        return {
            'success': 'error' not in response,
            'response': response
        }

def test_green_api():
    """Test Green API connection and functionality."""
    try:
        client = GreenAPIClient()
        
        # Test account info
        account_info = client.get_account_info()
        print("Account Info:", json.dumps(account_info, indent=2))
        
        # Test message (uncomment to actually send)
        # test_response = client.send_message(
        #     "447916991875@c.us",  # Group chat
        #     "🤖 Test message from JGV EEsystems AI Team Update Tracker"
        # )
        # print("Test Message Response:", json.dumps(test_response, indent=2))
        
        return True
        
    except Exception as e:
        print(f"Green API test failed: {e}")
        return False

if __name__ == "__main__":
    # Run tests
    print("Testing Green API integration...")
    if test_green_api():
        print("✅ Green API integration test passed")
    else:
        print("❌ Green API integration test failed")