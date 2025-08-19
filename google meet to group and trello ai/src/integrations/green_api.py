"""
Green API WhatsApp Integration

Handles WhatsApp message sending, group management, and formatting
using the Green API service.
"""

import asyncio
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from agent import MeetingSummary, ActionItem

logger = logging.getLogger(__name__)

# Green API base URL
GREEN_API_BASE_URL = "https://api.green-api.com"

# Message formatting templates
SUMMARY_TEMPLATE = """
🎯 *Meeting Summary - {date}*

👥 *Attendees:* {attendees}

📝 *Meeting Summary:*
{summary}

✅ *Key Decisions & Outcomes:*
{decisions}

📋 *Action Items Identified:* ({action_count})
{action_items}

🔗 *Resources:*
• Meeting Transcript: {transcript_link}
• Cards Updated: {card_count}
{card_links}

⏰ *Generated:* {timestamp}
"""

# Template for card assignee messages
ASSIGNEE_TEMPLATE = """
👋 Hi {name}!

📋 *Card Update from Today's Meeting*

{card_updates}

🔗 *Quick Links:*
{card_links}

💬 Need help? Just reply to this message!

---
*JGV EEsystems AI Team Tracker*
"""

CARD_UPDATE_TEMPLATE = """
📝 *{card_name}*
{discussion_summary}

💬 *What was discussed:*
{quotes}

✅ *Action needed:*
{actions}
"""

ACTION_ITEM_TEMPLATE = """
📌 *{index}.* {description}
👤 *Assigned:* {assignee}
🔥 *Priority:* {priority}
📅 *Due:* {due_date}
"""


class WhatsAppClient:
    """
    Green API WhatsApp client for sending meeting summaries and notifications.
    
    Supports message formatting, group management, and rate limiting.
    """
    
    def __init__(self, 
                 instance_id: Optional[str] = None,
                 api_token: Optional[str] = None):
        """
        Initialize WhatsApp client.
        
        Args:
            instance_id: Green API instance ID
            api_token: Green API token
        """
        self.instance_id = instance_id or os.getenv('GREEN_API_INSTANCE_ID')
        self.api_token = api_token or os.getenv('GREEN_API_TOKEN')
        
        if not self.instance_id or not self.api_token:
            raise ValueError("Green API credentials not provided")
        
        self.base_url = f"{GREEN_API_BASE_URL}/waInstance{self.instance_id}"
        self.session = None
        
        # Rate limiting configuration
        self.rate_limit_delay = 3  # seconds between messages
        self.max_retries = 5
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if not self.session:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def _make_request(self, 
                           endpoint: str, 
                           method: str = 'POST',
                           data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make HTTP request to Green API.
        
        Args:
            endpoint: API endpoint
            method: HTTP method
            data: Request data
            
        Returns:
            Response data
        """
        session = await self._get_session()
        url = f"{self.base_url}/{endpoint}/{self.api_token}"
        
        try:
            if method.upper() == 'POST':
                async with session.post(url, json=data) as response:
                    response.raise_for_status()
                    return await response.json()
            else:
                async with session.get(url) as response:
                    response.raise_for_status()
                    return await response.json()
                    
        except aiohttp.ClientError as e:
            logger.error(f"Green API request failed: {e}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test connection to Green API.
        
        Returns:
            Instance state information
        """
        try:
            response = await self._make_request('getStateInstance', 'GET')
            logger.info(f"Green API connection successful: {response}")
            return response
        except Exception as e:
            logger.error(f"Green API connection test failed: {e}")
            raise
    
    async def get_account_info(self) -> Dict[str, Any]:
        """
        Get WhatsApp account information.
        
        Returns:
            Account details
        """
        return await self._make_request('getSettings', 'GET')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    async def send_message(self, 
                          chat_id: str, 
                          message: str,
                          quoted_message_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a text message to a chat.
        
        Args:
            chat_id: Chat ID (phone number or group ID)
            message: Message text
            quoted_message_id: ID of message to quote (optional)
            
        Returns:
            Message send response
        """
        data = {
            'chatId': chat_id,
            'message': message
        }
        
        if quoted_message_id:
            data['quotedMessageId'] = quoted_message_id
        
        try:
            response = await self._make_request('sendMessage', 'POST', data)
            logger.info(f"Message sent to {chat_id}: {response}")
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send message to {chat_id}: {e}")
            raise
    
    async def send_file(self, 
                       chat_id: str, 
                       file_path: str,
                       caption: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a file to a chat.
        
        Args:
            chat_id: Chat ID
            file_path: Path to file to send
            caption: File caption (optional)
            
        Returns:
            File send response
        """
        # For Green API, we need to upload file first or use URL
        # This is a simplified implementation
        data = {
            'chatId': chat_id,
            'urlFile': file_path,  # Should be a URL in production
            'fileName': os.path.basename(file_path)
        }
        
        if caption:
            data['caption'] = caption
        
        try:
            response = await self._make_request('sendFileByUrl', 'POST', data)
            logger.info(f"File sent to {chat_id}: {response}")
            
            # Rate limiting
            await asyncio.sleep(self.rate_limit_delay)
            
            return response
            
        except Exception as e:
            logger.error(f"Failed to send file to {chat_id}: {e}")
            raise
    
    async def get_chats(self) -> List[Dict[str, Any]]:
        """
        Get list of chats.
        
        Returns:
            List of chat information
        """
        return await self._make_request('getChats', 'GET')
    
    async def get_group_data(self, group_id: str) -> Dict[str, Any]:
        """
        Get group information.
        
        Args:
            group_id: Group chat ID
            
        Returns:
            Group information
        """
        data = {'groupId': group_id}
        return await self._make_request('getGroupData', 'POST', data)
    
    async def send_summary(self, 
                          meeting_summary: MeetingSummary,
                          chat_ids: Optional[List[str]] = None,
                          group_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Send formatted meeting summary to WhatsApp chats.
        
        Args:
            meeting_summary: MeetingSummary object
            chat_ids: List of chat IDs to send to
            group_name: Group name to find and send to
            
        Returns:
            List of send responses
        """
        # Get target chats
        targets = []
        
        if chat_ids:
            targets.extend(chat_ids)
        
        if group_name:
            group_chat = await self._find_group_by_name(group_name)
            if group_chat:
                targets.append(group_chat['id'])
        
        if not targets:
            # Use default chat from environment
            default_chat = os.getenv('WHATSAPP_DEFAULT_CHAT')
            if default_chat:
                targets.append(default_chat)
            else:
                raise ValueError("No target chats specified")
        
        # Format message
        formatted_message = self._format_summary(meeting_summary)
        
        # Send to all targets
        responses = []
        for chat_id in targets:
            try:
                response = await self.send_message(chat_id, formatted_message)
                responses.append(response)
                
                # Send action items as separate messages if many
                if len(meeting_summary.action_items) > 5:
                    await self._send_action_items_separately(chat_id, meeting_summary.action_items)
                
            except Exception as e:
                logger.error(f"Failed to send summary to {chat_id}: {e}")
                responses.append({'error': str(e), 'chat_id': chat_id})
        
        return responses
    
    async def _find_group_by_name(self, group_name: str) -> Optional[Dict[str, Any]]:
        """
        Find a group chat by name.
        
        Args:
            group_name: Name of the group to find
            
        Returns:
            Group information if found
        """
        try:
            chats = await self.get_chats()
            
            for chat in chats:
                if (chat.get('name', '').lower() == group_name.lower() and 
                    chat.get('id', '').endswith('@g.us')):
                    return chat
            
            return None
            
        except Exception as e:
            logger.error(f"Error finding group {group_name}: {e}")
            return None
    
    def _format_summary(self, meeting_summary: MeetingSummary, 
                       transcript_link: str = "", 
                       card_links: List[Dict[str, str]] = None) -> str:
        """
        Format meeting summary for WhatsApp.
        
        Args:
            meeting_summary: MeetingSummary object
            transcript_link: Link to Google Doc transcript
            card_links: List of card info with names and URLs
            
        Returns:
            Formatted message string
        """
        # Format attendees (participants)
        attendees = ", ".join(meeting_summary.participants) if meeting_summary.participants else "Not specified"
        
        # Format decisions
        decisions = ""
        if meeting_summary.key_decisions:
            decisions = "\n".join([f"• {decision}" for decision in meeting_summary.key_decisions])
        else:
            decisions = "No specific decisions recorded"
        
        # Format action items (first 5)
        action_items = ""
        displayed_items = meeting_summary.action_items[:5]
        
        for i, item in enumerate(displayed_items, 1):
            assignee = item.assignee or "Unassigned"
            due_date = item.due_date.strftime("%Y-%m-%d") if item.due_date else "No deadline"
            
            action_items += ACTION_ITEM_TEMPLATE.format(
                index=i,
                description=item.description,
                assignee=assignee,
                priority=item.priority.upper(),
                due_date=due_date
            ) + "\n"
        
        if len(meeting_summary.action_items) > 5:
            action_items += f"\n... and {len(meeting_summary.action_items) - 5} more items"
        
        if not action_items.strip():
            action_items = "No action items identified"
        
        # Format card links
        card_links_text = ""
        if card_links:
            for card in card_links:
                card_links_text += f"• {card['name']}: {card['url']}\n"
        else:
            card_links_text = "No cards were updated"
        
        # Prepare transcript link
        transcript_display = transcript_link if transcript_link else "Not available"
        
        # Format main message
        message = SUMMARY_TEMPLATE.format(
            date=meeting_summary.date.strftime("%Y-%m-%d %H:%M"),
            attendees=attendees,
            summary=meeting_summary.summary[:500] + "..." if len(meeting_summary.summary) > 500 else meeting_summary.summary,
            decisions=decisions,
            action_count=len(meeting_summary.action_items),
            action_items=action_items.strip(),
            transcript_link=transcript_display,
            card_count=len(card_links) if card_links else 0,
            card_links=card_links_text.strip(),
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        return message
    
    def format_assignee_message(self, assignee_name: str, 
                               card_updates: List[Dict[str, Any]]) -> str:
        """
        Format personalized message for card assignees.
        
        Args:
            assignee_name: Name of the assignee
            card_updates: List of card update information
            
        Returns:
            Formatted message string
        """
        # Format card updates
        updates_text = ""
        card_links_text = ""
        
        for update in card_updates:
            card_name = update.get('card_name', 'Unknown Card')
            discussion = update.get('discussion_summary', 'Updates from today\'s meeting')
            quotes = update.get('quotes', ['No specific quotes recorded'])
            actions = update.get('actions', ['Please check the card for details'])
            card_url = update.get('card_url', '#')
            
            # Format quotes
            quotes_text = "\n".join([f"  \"{quote}\"" for quote in quotes[:3]])
            
            # Format actions
            actions_text = "\n".join([f"• {action}" for action in actions[:3]])
            
            updates_text += CARD_UPDATE_TEMPLATE.format(
                card_name=card_name,
                discussion_summary=discussion,
                quotes=quotes_text,
                actions=actions_text
            ) + "\n\n"
            
            card_links_text += f"• {card_name}: {card_url}\n"
        
        # Format final message
        message = ASSIGNEE_TEMPLATE.format(
            name=assignee_name,
            card_updates=updates_text.strip(),
            card_links=card_links_text.strip()
        )
        
        return message
    
    async def _send_action_items_separately(self, 
                                          chat_id: str, 
                                          action_items: List[ActionItem]):
        """
        Send action items as separate messages for better readability.
        
        Args:
            chat_id: Chat ID to send to
            action_items: List of action items
        """
        if len(action_items) <= 5:
            return
        
        # Send remaining action items
        remaining_items = action_items[5:]
        
        for i, item in enumerate(remaining_items, 6):
            assignee = item.assignee or "Unassigned"
            due_date = item.due_date.strftime("%Y-%m-%d") if item.due_date else "No deadline"
            
            message = ACTION_ITEM_TEMPLATE.format(
                index=i,
                description=item.description,
                assignee=assignee,
                priority=item.priority.upper(),
                due_date=due_date
            )
            
            try:
                await self.send_message(chat_id, message)
            except Exception as e:
                logger.error(f"Failed to send action item {i}: {e}")
    
    async def send_notification(self, 
                               message: str,
                               chat_ids: Optional[List[str]] = None,
                               priority: str = "normal") -> List[Dict[str, Any]]:
        """
        Send a notification message.
        
        Args:
            message: Notification message
            chat_ids: Target chat IDs
            priority: Message priority (normal, high, urgent)
            
        Returns:
            List of send responses
        """
        # Add priority indicators
        if priority == "high":
            message = f"🔸 *HIGH PRIORITY* 🔸\n\n{message}"
        elif priority == "urgent":
            message = f"🚨 *URGENT* 🚨\n\n{message}"
        
        # Get target chats
        targets = chat_ids or [os.getenv('WHATSAPP_DEFAULT_CHAT')]
        targets = [chat for chat in targets if chat]
        
        if not targets:
            raise ValueError("No target chats specified")
        
        # Send notifications
        responses = []
        for chat_id in targets:
            try:
                response = await self.send_message(chat_id, message)
                responses.append(response)
            except Exception as e:
                logger.error(f"Failed to send notification to {chat_id}: {e}")
                responses.append({'error': str(e), 'chat_id': chat_id})
        
        return responses
    
    async def get_message_status(self, message_id: str) -> Dict[str, Any]:
        """
        Get message delivery status.
        
        Args:
            message_id: Message ID to check
            
        Returns:
            Message status information
        """
        data = {'idMessage': message_id}
        return await self._make_request('getStatusMessage', 'POST', data)


# Utility functions
async def setup_whatsapp_client() -> WhatsAppClient:
    """
    Set up and test WhatsApp client.
    
    Returns:
        Configured WhatsAppClient instance
    """
    async with WhatsAppClient() as client:
        # Test connection
        status = await client.test_connection()
        logger.info(f"WhatsApp instance status: {status}")
        
        # Get account info
        account_info = await client.get_account_info()
        logger.info(f"WhatsApp account: {account_info.get('wid', 'unknown')}")
        
        return client


def format_quick_summary(title: str, 
                        key_points: List[str], 
                        action_count: int = 0) -> str:
    """
    Format a quick summary message.
    
    Args:
        title: Meeting title
        key_points: List of key points
        action_count: Number of action items
        
    Returns:
        Formatted message string
    """
    points_text = "\n".join([f"• {point}" for point in key_points[:5]])
    
    message = f"""
📋 *{title}*

🔑 *Key Points:*
{points_text}

📌 *Action Items:* {action_count}

⏰ *{datetime.now().strftime('%H:%M')}*
"""
    
    return message.strip()


if __name__ == "__main__":
    # Test the WhatsApp client
    async def test_client():
        async with WhatsAppClient() as client:
            status = await client.test_connection()
            print(f"Connection test: {status}")
            
            # Test quick message
            test_message = "🤖 Test message from Meeting Automation Tool"
            # Uncomment to send test message:
            # await client.send_notification(test_message)
    
    asyncio.run(test_client())