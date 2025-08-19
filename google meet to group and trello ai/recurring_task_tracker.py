#!/usr/bin/env python3
"""
Recurring Task Tracker Module
Tracks tasks and topics that keep being mentioned across meetings but remain unfinished
"""

import os
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple
from collections import defaultdict, Counter
from dotenv import load_dotenv

load_dotenv()

class RecurringTaskTracker:
    """Tracks recurring themes and unfinished tasks across multiple meetings."""
    
    def __init__(self, storage_file: str = "recurring_tasks.json"):
        self.storage_file = storage_file
        self.task_patterns = self._load_patterns()
        self.historical_data = self._load_historical_data()
    
    def _load_patterns(self) -> Dict[str, List[str]]:
        """Load common task patterns and keywords."""
        return {
            'action_verbs': [
                'need to', 'should', 'must', 'have to', 'will', 'going to',
                'plan to', 'want to', 'trying to', 'working on', 'finishing',
                'completing', 'reviewing', 'updating', 'fixing', 'creating'
            ],
            'status_indicators': [
                'still', 'not yet', 'pending', 'waiting', 'blocked', 'stuck',
                'delayed', 'almost done', 'in progress', 'working on',
                'need approval', 'waiting for'
            ],
            'urgency_markers': [
                'urgent', 'asap', 'priority', 'important', 'critical',
                'deadline', 'due', 'overdue', 'rush', 'quickly'
            ],
            'task_types': {
                'approval': ['approval', 'approve', 'sign off', 'review', 'check'],
                'communication': ['call', 'email', 'message', 'contact', 'reach out'],
                'documentation': ['document', 'write', 'create', 'update', 'draft'],
                'technical': ['fix', 'bug', 'issue', 'code', 'develop', 'build'],
                'design': ['design', 'mockup', 'layout', 'visual', 'graphic'],
                'meeting': ['schedule', 'meet', 'discuss', 'call', 'presentation']
            }
        }
    
    def _load_historical_data(self) -> Dict:
        """Load historical recurring task data."""
        try:
            if os.path.exists(self.storage_file):
                with open(self.storage_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading historical data: {e}")
        
        return {
            'tasks': {},
            'meetings': [],
            'patterns': {},
            'last_updated': None
        }
    
    def _save_historical_data(self):
        """Save historical data to file."""
        try:
            self.historical_data['last_updated'] = datetime.now().isoformat()
            with open(self.storage_file, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
        except Exception as e:
            print(f"Error saving historical data: {e}")
    
    def extract_potential_tasks(self, transcript: str) -> List[Dict]:
        """Extract potential task mentions from transcript."""
        potential_tasks = []
        lines = transcript.split('\n')
        
        for line_num, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Extract speaker if present
            speaker = None
            content = line
            speaker_match = re.match(r'^([A-Za-z][A-Za-z\s]+?)\s*[-:]\s*(.+)$', line)
            if speaker_match:
                speaker = speaker_match.group(1).strip().title()
                content = speaker_match.group(2).strip()
            
            # Look for task-like patterns
            task_signals = self._identify_task_signals(content)
            
            if task_signals['is_likely_task']:
                task_data = {
                    'line_number': line_num + 1,
                    'speaker': speaker,
                    'content': content,
                    'full_line': line,
                    'signals': task_signals,
                    'extracted_at': datetime.now().isoformat(),
                    'confidence': task_signals['confidence']
                }
                
                # Extract key phrases and entities
                task_data['key_phrases'] = self._extract_key_phrases(content)
                task_data['entities'] = self._extract_entities(content)
                
                potential_tasks.append(task_data)
        
        return potential_tasks
    
    def _identify_task_signals(self, content: str) -> Dict:
        """Identify signals that indicate this might be a task or action item."""
        content_lower = content.lower()
        signals = {
            'is_likely_task': False,
            'confidence': 0.0,
            'indicators': [],
            'task_type': None,
            'urgency': 'normal',
            'status': 'unknown'
        }
        
        # Check for action verbs
        action_score = 0
        for verb in self.task_patterns['action_verbs']:
            if verb in content_lower:
                action_score += 1
                signals['indicators'].append(f'action_verb: {verb}')
        
        # Check for status indicators
        status_score = 0
        for status in self.task_patterns['status_indicators']:
            if status in content_lower:
                status_score += 1
                signals['indicators'].append(f'status: {status}')
                if status in ['still', 'not yet', 'pending', 'waiting', 'blocked']:
                    signals['status'] = 'incomplete'
        
        # Check for urgency markers
        urgency_score = 0
        for urgency in self.task_patterns['urgency_markers']:
            if urgency in content_lower:
                urgency_score += 1
                signals['urgency'] = 'high'
                signals['indicators'].append(f'urgency: {urgency}')
        
        # Determine task type
        for task_type, keywords in self.task_patterns['task_types'].items():
            for keyword in keywords:
                if keyword in content_lower:
                    signals['task_type'] = task_type
                    signals['indicators'].append(f'type: {task_type}')
                    break
            if signals['task_type']:
                break
        
        # Calculate confidence score
        base_confidence = 0
        if action_score > 0:
            base_confidence += 30
        if status_score > 0:
            base_confidence += 25
        if urgency_score > 0:
            base_confidence += 20
        if signals['task_type']:
            base_confidence += 15
        
        # Additional patterns
        if re.search(r'\b(todo|to do|action item|next step)\b', content_lower):
            base_confidence += 25
            signals['indicators'].append('explicit_task_mention')
        
        if '?' in content and any(word in content_lower for word in ['when', 'who', 'how', 'what']):
            base_confidence += 15
            signals['indicators'].append('task_question')
        
        signals['confidence'] = min(100, base_confidence) / 100.0
        signals['is_likely_task'] = signals['confidence'] >= 0.4
        
        return signals
    
    def _extract_key_phrases(self, content: str) -> List[str]:
        """Extract key phrases that might identify the task."""
        phrases = []
        
        # Look for quoted text
        quoted = re.findall(r'["\']([^"\']*?)["\']', content)
        phrases.extend(quoted)
        
        # Look for specific project/task names (capitalized phrases)
        capitalized = re.findall(r'\b[A-Z][A-Za-z\s]{2,20}\b', content)
        phrases.extend([cap.strip() for cap in capitalized if len(cap.split()) <= 4])
        
        # Look for common task patterns
        task_patterns = [
            r'\b(\w+\s+\w+)\s+project\b',
            r'\b(\w+\s+\w+)\s+task\b',
            r'\bfor\s+(\w+(?:\s+\w+){0,2})\b',
            r'\bthe\s+(\w+(?:\s+\w+){0,2})\s+(?:project|task|item)\b'
        ]
        
        for pattern in task_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            phrases.extend(matches)
        
        # Clean and deduplicate
        cleaned_phrases = []
        for phrase in phrases:
            if isinstance(phrase, tuple):
                phrase = ' '.join(phrase)
            phrase = phrase.strip()
            if len(phrase) > 2 and phrase.lower() not in ['the', 'and', 'for', 'with']:
                cleaned_phrases.append(phrase)
        
        return list(set(cleaned_phrases))
    
    def _extract_entities(self, content: str) -> Dict[str, List[str]]:
        """Extract entities like names, dates, etc."""
        entities = {
            'names': [],
            'dates': [],
            'projects': [],
            'tools': []
        }
        
        # Extract potential names (capitalized words)
        names = re.findall(r'\b[A-Z][a-z]+\b', content)
        entities['names'] = [name for name in names if len(name) > 2]
        
        # Extract date-like patterns
        date_patterns = [
            r'\b(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
            r'\b(?:today|tomorrow|yesterday|next week|this week)\b',
            r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\b',
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            entities['dates'].extend(matches)
        
        # Extract tool/platform names
        tools = ['trello', 'slack', 'email', 'wordpress', 'github', 'figma', 'excel']
        for tool in tools:
            if tool.lower() in content.lower():
                entities['tools'].append(tool)
        
        return entities
    
    def analyze_recurring_patterns(self, new_transcript: str, meeting_id: str = None) -> Dict:
        """Analyze transcript for recurring task patterns."""
        if not meeting_id:
            meeting_id = f"meeting_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Extract potential tasks from new transcript
        new_tasks = self.extract_potential_tasks(new_transcript)
        
        # Store this meeting's data
        meeting_data = {
            'id': meeting_id,
            'date': datetime.now().isoformat(),
            'tasks_found': len(new_tasks),
            'tasks': new_tasks
        }
        
        self.historical_data['meetings'].append(meeting_data)
        
        # Analyze patterns across all meetings
        recurring_tasks = self._find_recurring_tasks()
        
        # Update historical data
        self.historical_data['patterns'] = recurring_tasks
        self._save_historical_data()
        
        return {
            'meeting_id': meeting_id,
            'new_tasks_found': len(new_tasks),
            'recurring_tasks': recurring_tasks,
            'analysis_summary': self._generate_analysis_summary(recurring_tasks)
        }
    
    def _find_recurring_tasks(self) -> Dict:
        """Find tasks that appear across multiple meetings."""
        all_tasks = []
        for meeting in self.historical_data['meetings']:
            all_tasks.extend(meeting['tasks'])
        
        if len(all_tasks) < 2:
            return {}
        
        # Group similar tasks
        task_groups = defaultdict(list)
        
        for task in all_tasks:
            # Create a signature for the task based on key phrases
            signature = self._create_task_signature(task)
            task_groups[signature].append(task)
        
        # Find recurring patterns
        recurring = {}
        
        for signature, tasks in task_groups.items():
            if len(tasks) >= 2:  # Mentioned at least twice
                # Calculate time span
                dates = [datetime.fromisoformat(task['extracted_at']) for task in tasks]
                first_mention = min(dates)
                last_mention = max(dates)
                
                # Determine status
                status = self._determine_recurring_status(tasks)
                
                recurring[signature] = {
                    'task_signature': signature,
                    'mention_count': len(tasks),
                    'first_mentioned': first_mention.isoformat(),
                    'last_mentioned': last_mention.isoformat(),
                    'days_recurring': (last_mention - first_mention).days,
                    'status': status,
                    'speakers': list(set(task.get('speaker') for task in tasks if task.get('speaker'))),
                    'urgency': self._calculate_urgency_trend(tasks),
                    'sample_mentions': [task['content'] for task in tasks[:3]],
                    'key_phrases': self._consolidate_key_phrases(tasks),
                    'recommended_action': self._suggest_action(tasks, status)
                }
        
        return recurring
    
    def _create_task_signature(self, task: Dict) -> str:
        """Create a signature to identify similar tasks."""
        # Use key phrases and content similarity
        key_phrases = task.get('key_phrases', [])
        content = task.get('content', '').lower()
        
        # Create signature from most significant phrases
        if key_phrases:
            primary_phrase = max(key_phrases, key=len)
            return primary_phrase.lower()
        else:
            # Fallback to first significant words
            words = re.findall(r'\b\w{3,}\b', content)
            if words:
                return ' '.join(words[:3])
            return content[:30]
    
    def _determine_recurring_status(self, tasks: List[Dict]) -> str:
        """Determine the status of a recurring task."""
        recent_tasks = sorted(tasks, key=lambda x: x['extracted_at'], reverse=True)[:2]
        
        status_indicators = []
        for task in recent_tasks:
            if task['signals']['status'] == 'incomplete':
                status_indicators.append('incomplete')
            elif any('complete' in indicator for indicator in task['signals']['indicators']):
                status_indicators.append('complete')
            else:
                status_indicators.append('unknown')
        
        if 'complete' in status_indicators:
            return 'resolved'
        elif 'incomplete' in status_indicators:
            return 'blocked'
        else:
            return 'ongoing'
    
    def _calculate_urgency_trend(self, tasks: List[Dict]) -> str:
        """Calculate if urgency is increasing over time."""
        urgency_scores = []
        for task in sorted(tasks, key=lambda x: x['extracted_at']):
            if task['signals']['urgency'] == 'high':
                urgency_scores.append(1)
            else:
                urgency_scores.append(0)
        
        if len(urgency_scores) >= 2:
            if urgency_scores[-1] > urgency_scores[0]:
                return 'increasing'
            elif urgency_scores[-1] < urgency_scores[0]:
                return 'decreasing'
        
        return 'stable'
    
    def _consolidate_key_phrases(self, tasks: List[Dict]) -> List[str]:
        """Consolidate key phrases from all task mentions."""
        all_phrases = []
        for task in tasks:
            all_phrases.extend(task.get('key_phrases', []))
        
        # Count frequency and return most common
        phrase_counts = Counter(all_phrases)
        return [phrase for phrase, count in phrase_counts.most_common(5)]
    
    def _suggest_action(self, tasks: List[Dict], status: str) -> str:
        """Suggest action based on recurring pattern."""
        mention_count = len(tasks)
        days_recurring = (datetime.fromisoformat(tasks[-1]['extracted_at']) - 
                         datetime.fromisoformat(tasks[0]['extracted_at'])).days
        
        if mention_count >= 3 and status == 'blocked':
            return 'URGENT: This task has been blocked for multiple meetings. Immediate intervention needed.'
        elif mention_count >= 2 and days_recurring >= 7:
            return 'Schedule dedicated time to resolve this recurring item.'
        elif status == 'ongoing' and mention_count >= 2:
            return 'Consider breaking this task into smaller, actionable items.'
        else:
            return 'Monitor for continued mentions in future meetings.'
    
    def _generate_analysis_summary(self, recurring_tasks: Dict) -> Dict:
        """Generate a summary of the recurring task analysis."""
        if not recurring_tasks:
            return {
                'total_recurring': 0,
                'urgent_items': 0,
                'blocked_items': 0,
                'recommendations': ['No recurring tasks detected yet. Continue monitoring future meetings.']
            }
        
        urgent_count = sum(1 for task in recurring_tasks.values() 
                          if 'URGENT' in task['recommended_action'])
        blocked_count = sum(1 for task in recurring_tasks.values() 
                           if task['status'] == 'blocked')
        
        recommendations = []
        if urgent_count > 0:
            recommendations.append(f'{urgent_count} task(s) require immediate attention.')
        if blocked_count > 0:
            recommendations.append(f'{blocked_count} task(s) appear to be blocked and need resolution.')
        
        if len(recurring_tasks) >= 3:
            recommendations.append('Consider implementing a formal task tracking system.')
        
        return {
            'total_recurring': len(recurring_tasks),
            'urgent_items': urgent_count,
            'blocked_items': blocked_count,
            'recommendations': recommendations or ['All recurring tasks appear to be progressing normally.']
        }

def test_recurring_tracker():
    """Test the recurring task tracker."""
    tracker = RecurringTaskTracker('test_recurring.json')
    
    # Test with sample transcripts
    transcript1 = """
John: We still need to get approval for the logo design. This is the third week we're waiting.
Sarah: I'll follow up with the client today. Also, we need to finish the WordPress site.
Mike: The WordPress site is almost done, just need final review.
"""
    
    transcript2 = """
John: Any update on the logo approval? We're still blocked on that.
Sarah: Still waiting for client response. Meanwhile, WordPress site is ready for launch.
Mike: Great! What about the presentation materials we discussed?
"""
    
    result1 = tracker.analyze_recurring_patterns(transcript1, 'meeting_1')
    result2 = tracker.analyze_recurring_patterns(transcript2, 'meeting_2')
    
    print(f"Test Results:")
    print(f"Meeting 1 tasks: {result1['new_tasks_found']}")
    print(f"Meeting 2 tasks: {result2['new_tasks_found']}")
    print(f"Recurring patterns: {len(result2['recurring_tasks'])}")
    
    return len(result2['recurring_tasks']) > 0

if __name__ == "__main__":
    if test_recurring_tracker():
        print("Recurring task tracker test passed!")
    else:
        print("Recurring task tracker test failed!")