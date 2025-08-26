#!/usr/bin/env python3
"""
Enhanced AI Module with Robust Error Handling and Exponential Backoff
Provides resilient AI capabilities with automatic retry logic
"""

import os
import json
import re
import time
import random
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
from functools import wraps
import logging
from openai import OpenAI, RateLimitError, APIError, APIConnectionError, Timeout
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AIProvider(Enum):
    """Supported AI providers."""
    OPENAI = "openai"
    CLAUDE = "claude"
    LOCAL = "local"

@dataclass
class AnalysisResult:
    """Structured result from AI analysis."""
    confidence: float
    summary: str
    insights: List[str]
    metadata: Dict[str, Any]
    processing_time: float
    retry_count: int = 0
    error_handled: bool = False

class RetryConfig:
    """Configuration for retry logic."""
    def __init__(
        self,
        max_retries: int = 5,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter

def exponential_backoff_retry(
    func: Optional[Callable] = None,
    config: Optional[RetryConfig] = None
):
    """
    Decorator for exponential backoff retry logic.
    
    Args:
        func: Function to wrap
        config: Retry configuration
    """
    if config is None:
        config = RetryConfig()
    
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_retries):
                try:
                    # Log attempt
                    if attempt > 0:
                        logger.info(f"Retry attempt {attempt}/{config.max_retries} for {f.__name__}")
                    
                    # Try to execute the function
                    result = f(*args, **kwargs)
                    
                    # If successful and we had retries, update the result
                    if attempt > 0 and hasattr(result, 'retry_count'):
                        result.retry_count = attempt
                        result.error_handled = True
                    
                    return result
                    
                except (RateLimitError, APIError, APIConnectionError, Timeout) as e:
                    last_exception = e
                    
                    # Calculate delay with exponential backoff
                    delay = min(
                        config.initial_delay * (config.exponential_base ** attempt),
                        config.max_delay
                    )
                    
                    # Add jitter to prevent thundering herd
                    if config.jitter:
                        delay *= (0.5 + random.random())
                    
                    logger.warning(
                        f"API error in {f.__name__}: {str(e)}. "
                        f"Retrying in {delay:.2f} seconds..."
                    )
                    
                    # Check if we should continue retrying
                    if attempt < config.max_retries - 1:
                        time.sleep(delay)
                    else:
                        logger.error(f"Max retries exceeded for {f.__name__}")
                        
                except json.JSONDecodeError as e:
                    logger.warning(f"JSON parsing error in {f.__name__}: {str(e)}")
                    # For JSON errors, try fallback immediately
                    if hasattr(args[0], '_get_fallback_method'):
                        fallback_method = args[0]._get_fallback_method(f.__name__)
                        if fallback_method:
                            logger.info(f"Using fallback method for {f.__name__}")
                            return fallback_method(*args[1:], **kwargs)
                    raise
                    
                except Exception as e:
                    logger.error(f"Unexpected error in {f.__name__}: {str(e)}")
                    raise
            
            # If all retries failed, raise the last exception
            if last_exception:
                raise last_exception
                
        return wrapper
    
    if func is None:
        return decorator
    else:
        return decorator(func)

class EnhancedAI:
    """Enhanced AI module with robust error handling and retry logic."""
    
    def __init__(
        self,
        preferred_provider: AIProvider = AIProvider.OPENAI,
        retry_config: Optional[RetryConfig] = None
    ):
        self.preferred_provider = preferred_provider
        self.openai_client = None
        self.retry_config = retry_config or RetryConfig()
        self.setup_providers()
        
        # Track API usage for monitoring
        self.api_calls = 0
        self.api_errors = 0
        self.total_retry_count = 0
    
    def setup_providers(self):
        """Initialize AI providers with error handling."""
        try:
            if os.environ.get('OPENAI_API_KEY'):
                self.openai_client = OpenAI(
                    api_key=os.environ.get('OPENAI_API_KEY'),
                    timeout=30.0,  # Add timeout
                    max_retries=0  # We handle retries ourselves
                )
                logger.info("OpenAI client initialized successfully")
            else:
                logger.warning("OPENAI_API_KEY not found - AI features will be limited")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            self.openai_client = None
    
    @exponential_backoff_retry
    def analyze_meeting_sentiment(self, transcript: str) -> AnalysisResult:
        """Analyze overall meeting sentiment with retry logic."""
        start_time = datetime.now()
        self.api_calls += 1
        
        prompt = f"""
        Analyze the sentiment and mood of this meeting transcript. Provide:
        
        1. Overall sentiment score (1-10, where 1 is very negative, 10 is very positive)
        2. Mood indicators (enthusiastic, frustrated, confused, focused, etc.)
        3. Energy level (low, medium, high)
        4. Collaboration quality (poor, fair, good, excellent)
        5. Key emotional moments or tone shifts
        
        Transcript (first 3000 chars):
        {transcript[:3000]}
        
        Respond in valid JSON format only.
        """
        
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, using fallback")
                return self._fallback_sentiment_analysis(transcript, start_time)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",  # Using gpt-4o instead of gpt-5
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=1000,
                response_format={"type": "json_object"}  # Force JSON response
            )
            
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AnalysisResult(
                confidence=0.85,
                summary=f"Meeting sentiment: {analysis_data.get('overall_sentiment', 'neutral')}",
                insights=[
                    f"Sentiment score: {analysis_data.get('sentiment_score', 'N/A')}/10",
                    f"Mood: {analysis_data.get('mood', 'neutral')}",
                    f"Energy level: {analysis_data.get('energy_level', 'medium')}",
                    f"Collaboration: {analysis_data.get('collaboration_quality', 'fair')}"
                ],
                metadata=analysis_data,
                processing_time=processing_time
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error, using fallback: {str(e)}")
            return self._fallback_sentiment_analysis(transcript, start_time)
        except Exception as e:
            self.api_errors += 1
            logger.error(f"Error in sentiment analysis: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def analyze_decision_points(self, transcript: str) -> AnalysisResult:
        """Extract and analyze decision points with retry logic."""
        start_time = datetime.now()
        self.api_calls += 1
        
        prompt = f"""
        Analyze this meeting transcript and identify:
        
        1. Key decisions made (with decision owner if mentioned)
        2. Pending decisions requiring follow-up
        3. Decision criteria discussed
        4. Risks or concerns raised about decisions
        5. Timeline for decision implementation
        
        Format each decision as:
        - Decision: [description]
        - Owner: [person/team]
        - Timeline: [when]
        - Status: [made/pending/deferred]
        
        Transcript (first 3000 chars):
        {transcript[:3000]}
        
        Respond in valid JSON format only.
        """
        
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, using fallback")
                return self._fallback_decision_analysis(transcript, start_time)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.2,
                max_tokens=1500,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            decisions = analysis_data.get('decisions', [])
            insights = []
            
            for decision in decisions[:5]:  # Top 5 decisions
                insights.append(
                    f"• {decision.get('decision', 'Unknown')}: "
                    f"{decision.get('status', 'pending')} "
                    f"({decision.get('owner', 'unassigned')})"
                )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AnalysisResult(
                confidence=0.8,
                summary=f"Identified {len(decisions)} decision points",
                insights=insights,
                metadata=analysis_data,
                processing_time=processing_time
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error, using fallback: {str(e)}")
            return self._fallback_decision_analysis(transcript, start_time)
        except Exception as e:
            self.api_errors += 1
            logger.error(f"Error in decision analysis: {str(e)}")
            raise
    
    @exponential_backoff_retry
    def generate_executive_summary(
        self,
        transcript: str,
        target_audience: str = "management"
    ) -> AnalysisResult:
        """Generate executive summary with retry logic."""
        start_time = datetime.now()
        self.api_calls += 1
        
        audience_prompts = {
            "management": "Focus on strategic decisions, risks, and resource needs",
            "technical": "Emphasize technical details, architecture decisions, and implementation challenges",
            "client": "Highlight deliverables, timelines, and value proposition",
            "team": "Cover action items, responsibilities, and next steps"
        }
        
        audience_focus = audience_prompts.get(target_audience, audience_prompts["management"])
        
        prompt = f"""
        Create an executive summary of this meeting for {target_audience}.
        {audience_focus}
        
        Include:
        1. Meeting purpose and outcome
        2. Key decisions and agreements
        3. Action items with owners
        4. Risks and mitigation strategies
        5. Next steps and timeline
        
        Keep it concise (max 5 bullet points per section).
        
        Transcript (first 3000 chars):
        {transcript[:3000]}
        
        Respond in valid JSON format only.
        """
        
        try:
            if not self.openai_client:
                logger.warning("OpenAI client not available, using fallback")
                return self._fallback_summary_analysis(transcript, target_audience, start_time)
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            analysis_data = json.loads(content)
            
            # Extract key points for insights
            insights = []
            
            if 'key_decisions' in analysis_data:
                insights.extend([f"Decision: {d}" for d in analysis_data['key_decisions'][:3]])
            
            if 'action_items' in analysis_data:
                insights.extend([f"Action: {a}" for a in analysis_data['action_items'][:3]])
            
            if 'risks' in analysis_data:
                insights.extend([f"Risk: {r}" for r in analysis_data['risks'][:2]])
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return AnalysisResult(
                confidence=0.9,
                summary=analysis_data.get('summary', 'Meeting summary generated'),
                insights=insights[:8],  # Limit to 8 insights
                metadata=analysis_data,
                processing_time=processing_time
            )
            
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error, using fallback: {str(e)}")
            return self._fallback_summary_analysis(transcript, target_audience, start_time)
        except Exception as e:
            self.api_errors += 1
            logger.error(f"Error in executive summary: {str(e)}")
            raise
    
    def _get_fallback_method(self, method_name: str):
        """Get fallback method for a given AI method."""
        fallback_map = {
            'analyze_meeting_sentiment': self._fallback_sentiment_analysis,
            'analyze_decision_points': self._fallback_decision_analysis,
            'generate_executive_summary': self._fallback_summary_analysis
        }
        return fallback_map.get(method_name)
    
    def _fallback_sentiment_analysis(self, transcript: str, start_time: datetime) -> AnalysisResult:
        """Fallback sentiment analysis using rule-based approach."""
        logger.info("Using fallback sentiment analysis")
        
        # Simple keyword-based sentiment analysis
        positive_keywords = ['great', 'excellent', 'good', 'perfect', 'wonderful', 'fantastic', 'agreed', 'yes']
        negative_keywords = ['bad', 'poor', 'issue', 'problem', 'concern', 'worried', 'difficult', 'no']
        
        text_lower = transcript.lower()
        positive_count = sum(1 for word in positive_keywords if word in text_lower)
        negative_count = sum(1 for word in negative_keywords if word in text_lower)
        
        # Calculate sentiment score
        total_keywords = positive_count + negative_count
        if total_keywords > 0:
            sentiment_score = round(5 + (positive_count - negative_count) * 5 / total_keywords, 1)
            sentiment_score = max(1, min(10, sentiment_score))  # Clamp between 1-10
        else:
            sentiment_score = 5
        
        # Determine mood based on score
        if sentiment_score >= 7:
            mood = "positive"
            energy = "high"
        elif sentiment_score >= 4:
            mood = "neutral"
            energy = "medium"
        else:
            mood = "concerned"
            energy = "low"
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.5,
            summary=f"Meeting sentiment: {mood} (fallback analysis)",
            insights=[
                f"Sentiment score: {sentiment_score}/10",
                f"Mood: {mood}",
                f"Energy level: {energy}",
                f"Positive indicators: {positive_count}",
                f"Negative indicators: {negative_count}"
            ],
            metadata={
                "sentiment_score": sentiment_score,
                "mood": mood,
                "energy_level": energy,
                "method": "fallback"
            },
            processing_time=processing_time,
            error_handled=True
        )
    
    def _fallback_decision_analysis(self, transcript: str, start_time: datetime) -> AnalysisResult:
        """Fallback decision analysis using pattern matching."""
        logger.info("Using fallback decision analysis")
        
        # Pattern matching for decisions
        decision_patterns = [
            r"we (?:will|should|must|need to) (\w+.*?)(?:\.|,)",
            r"(?:decided|agreed) (?:to|that) (\w+.*?)(?:\.|,)",
            r"the decision is (?:to|that) (\w+.*?)(?:\.|,)",
            r"let's (\w+.*?)(?:\.|,)"
        ]
        
        decisions = []
        for pattern in decision_patterns:
            matches = re.findall(pattern, transcript.lower(), re.IGNORECASE)
            decisions.extend(matches[:3])  # Limit matches per pattern
        
        # Remove duplicates and clean up
        unique_decisions = []
        seen = set()
        for decision in decisions:
            clean_decision = decision.strip()[:100]  # Limit length
            if clean_decision and clean_decision not in seen:
                unique_decisions.append(clean_decision)
                seen.add(clean_decision)
        
        insights = [f"• {d}" for d in unique_decisions[:5]]
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.4,
            summary=f"Identified {len(unique_decisions)} potential decisions (fallback)",
            insights=insights,
            metadata={
                "decisions": unique_decisions,
                "method": "fallback"
            },
            processing_time=processing_time,
            error_handled=True
        )
    
    def _fallback_summary_analysis(
        self,
        transcript: str,
        target_audience: str,
        start_time: datetime
    ) -> AnalysisResult:
        """Fallback summary generation using text extraction."""
        logger.info("Using fallback summary analysis")
        
        # Extract first and last parts of transcript
        words = transcript.split()
        intro = ' '.join(words[:50]) if len(words) > 50 else ' '.join(words)
        conclusion = ' '.join(words[-50:]) if len(words) > 100 else ''
        
        # Look for action items
        action_patterns = [
            r"(?:will|should|must|need to) (\w+.*?)(?:\.|,)",
            r"action item[s]?:? (\w+.*?)(?:\.|,)",
            r"follow up (?:on|with) (\w+.*?)(?:\.|,)"
        ]
        
        actions = []
        for pattern in action_patterns:
            matches = re.findall(pattern, transcript.lower(), re.IGNORECASE)
            actions.extend(matches[:2])
        
        insights = [
            f"Meeting start: {intro[:100]}...",
            f"Participants discussed: {len(words)} words exchanged"
        ]
        
        if actions:
            insights.extend([f"Action: {a[:50]}" for a in actions[:3]])
        
        if conclusion:
            insights.append(f"Conclusion: {conclusion[:100]}...")
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AnalysisResult(
            confidence=0.3,
            summary=f"Meeting summary for {target_audience} (fallback analysis)",
            insights=insights,
            metadata={
                "word_count": len(words),
                "action_items": actions[:5],
                "method": "fallback"
            },
            processing_time=processing_time,
            error_handled=True
        )
    
    def get_api_stats(self) -> Dict[str, Any]:
        """Get API usage statistics."""
        error_rate = (self.api_errors / self.api_calls * 100) if self.api_calls > 0 else 0
        
        return {
            "total_api_calls": self.api_calls,
            "total_errors": self.api_errors,
            "error_rate_percent": round(error_rate, 2),
            "total_retries": self.total_retry_count,
            "retry_config": {
                "max_retries": self.retry_config.max_retries,
                "initial_delay": self.retry_config.initial_delay,
                "max_delay": self.retry_config.max_delay
            }
        }

def test_enhanced_ai_with_retry():
    """Test the enhanced AI with retry logic."""
    print("Testing Enhanced AI with Retry Logic...")
    
    # Initialize with custom retry config
    retry_config = RetryConfig(
        max_retries=3,
        initial_delay=0.5,
        max_delay=10.0,
        jitter=True
    )
    
    ai = EnhancedAI(retry_config=retry_config)
    
    # Test transcript
    test_transcript = """
    John: Good morning everyone. Let's discuss the Q4 roadmap.
    Sarah: I think we should prioritize the mobile app development.
    Mike: Agreed. We also need to address the performance issues.
    John: Let's make a decision. We will allocate 60% of resources to mobile.
    Sarah: That sounds reasonable. I can lead that initiative.
    Mike: I'll handle the performance optimization then.
    John: Perfect. Let's meet again next week to review progress.
    """
    
    # Test sentiment analysis
    print("\n1. Testing sentiment analysis...")
    try:
        result = ai.analyze_meeting_sentiment(test_transcript)
        print(f"   Confidence: {result.confidence}")
        print(f"   Summary: {result.summary}")
        print(f"   Retry count: {result.retry_count}")
        print(f"   Error handled: {result.error_handled}")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Test decision analysis
    print("\n2. Testing decision analysis...")
    try:
        result = ai.analyze_decision_points(test_transcript)
        print(f"   Confidence: {result.confidence}")
        print(f"   Summary: {result.summary}")
        print(f"   Insights: {len(result.insights)} found")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Test executive summary
    print("\n3. Testing executive summary...")
    try:
        result = ai.generate_executive_summary(test_transcript, "management")
        print(f"   Confidence: {result.confidence}")
        print(f"   Processing time: {result.processing_time:.2f}s")
    except Exception as e:
        print(f"   Error: {str(e)}")
    
    # Print API stats
    print("\n4. API Statistics:")
    stats = ai.get_api_stats()
    for key, value in stats.items():
        if isinstance(value, dict):
            print(f"   {key}:")
            for k, v in value.items():
                print(f"      {k}: {v}")
        else:
            print(f"   {key}: {value}")

if __name__ == "__main__":
    test_enhanced_ai_with_retry()