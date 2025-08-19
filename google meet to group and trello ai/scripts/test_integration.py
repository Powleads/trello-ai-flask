#!/usr/bin/env python3
"""
Integration Testing Script

Tests all service integrations for the meeting automation tool
including Google Drive, WhatsApp (Green API), Trello, and AI providers.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Dict, Any

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

# Load environment variables
load_dotenv()

console = Console()

async def test_google_drive():
    """Test Google Drive integration."""
    try:
        from integrations.google_drive import GoogleDriveClient
        
        client = GoogleDriveClient()
        result = await client.test_connection()
        
        return {
            'status': 'success',
            'details': f"Connected as {result.get('email', 'unknown')}",
            'data': result
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_whatsapp():
    """Test WhatsApp (Green API) integration."""
    try:
        from integrations.green_api import WhatsAppClient
        
        async with WhatsAppClient() as client:
            result = await client.test_connection()
            
            return {
                'status': 'success',
                'details': f"Instance state: {result.get('stateInstance', 'unknown')}",
                'data': result
            }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_trello():
    """Test Trello integration."""
    try:
        from integrations.trello import TrelloClient
        
        async with TrelloClient() as client:
            result = await client.test_connection()
            
            return {
                'status': 'success',
                'details': f"Connected as {result.get('fullName', 'unknown')}",
                'data': result
            }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_openai():
    """Test OpenAI integration."""
    try:
        from agent import OpenAIProvider
        
        provider = OpenAIProvider()
        result = await provider.test_connection()
        
        if result:
            return {
                'status': 'success',
                'details': 'API connection successful',
                'data': {'api_working': True}
            }
        else:
            return {
                'status': 'error',
                'details': 'API connection failed',
                'data': None
            }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_transcript_parser():
    """Test transcript parsing functionality."""
    try:
        from processors.transcript_parser import TranscriptParser
        
        parser = TranscriptParser()
        
        # Create a test transcript
        test_transcript = """
John: Good morning everyone, let's start our project review.
Sarah: Thanks John. I wanted to update on the budget status.
Mike: We need to prioritize the core features for this release.
John: Agreed. Sarah, can you prepare a revised budget by Friday?
Sarah: Sure, I'll have it ready by end of week.
        """
        
        # Write test file
        test_file = Path('test_transcript.txt')
        test_file.write_text(test_transcript)
        
        try:
            parsed_data = parser.parse_file(str(test_file))
            
            return {
                'status': 'success',
                'details': f"Parsed {parsed_data['total_segments']} segments, detected {len(parsed_data['participants'])} participants",
                'data': {
                    'format': parsed_data['format'],
                    'segments': parsed_data['total_segments'],
                    'participants': len(parsed_data['participants'])
                }
            }
        finally:
            # Clean up test file
            if test_file.exists():
                test_file.unlink()
                
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_task_extractor():
    """Test task extraction functionality."""
    try:
        from processors.task_extractor import TaskExtractor
        
        extractor = TaskExtractor()
        
        test_transcript = """
        John: We need to finish the project proposal by Friday.
        Sarah: I'll review the budget section and send feedback by tomorrow.
        Mike: Can someone schedule a follow-up meeting with the client?
        Action item: Update the project timeline.
        """
        
        participants = ["John", "Sarah", "Mike"]
        items = extractor.extract_action_items(test_transcript, participants)
        
        return {
            'status': 'success',
            'details': f"Extracted {len(items)} action items",
            'data': {
                'action_items': len(items),
                'with_assignee': len([item for item in items if item.assignee]),
                'with_deadline': len([item for item in items if item.due_date])
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_summarizer():
    """Test meeting summarization functionality."""
    try:
        from processors.summarizer import MeetingSummarizer
        
        # This test only checks if the summarizer can be initialized
        # Full testing would require API keys
        summarizer = MeetingSummarizer()
        
        return {
            'status': 'success',
            'details': f"Summarizer initialized with {len(summarizer.get_available_formats())} formats",
            'data': {
                'available_formats': summarizer.get_available_formats(),
                'default_format': summarizer.default_format
            }
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_cli_imports():
    """Test CLI module imports."""
    try:
        from cli import cli
        
        return {
            'status': 'success',
            'details': 'CLI module imported successfully',
            'data': {'cli_available': True}
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def test_agent_imports():
    """Test main agent imports."""
    try:
        from agent import MeetingAutomationAgent, ActionItem, MeetingSummary
        
        # Test basic instantiation
        agent = MeetingAutomationAgent()
        
        return {
            'status': 'success',
            'details': 'Agent module imported and instantiated successfully',
            'data': {'agent_available': True}
        }
    except Exception as e:
        return {
            'status': 'error',
            'details': str(e),
            'data': None
        }

async def run_all_tests():
    """Run all integration tests."""
    
    tests = {
        'Core Modules': {
            'CLI Imports': test_cli_imports,
            'Agent Imports': test_agent_imports,
        },
        'Processors': {
            'Transcript Parser': test_transcript_parser,
            'Task Extractor': test_task_extractor,
            'Summarizer': test_summarizer,
        },
        'External Services': {
            'Google Drive': test_google_drive,
            'WhatsApp (Green API)': test_whatsapp,
            'Trello': test_trello,
            'OpenAI': test_openai,
        }
    }
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for category, category_tests in tests.items():
            results[category] = {}
            
            for test_name, test_func in category_tests.items():
                task = progress.add_task(f"Testing {test_name}...", total=None)
                
                try:
                    result = await test_func()
                    results[category][test_name] = result
                    
                    if result['status'] == 'success':
                        progress.update(task, description=f"✅ {test_name}")
                    else:
                        progress.update(task, description=f"❌ {test_name}")
                        
                except Exception as e:
                    results[category][test_name] = {
                        'status': 'error',
                        'details': f"Test execution failed: {e}",
                        'data': None
                    }
                    progress.update(task, description=f"❌ {test_name}")
    
    return results

def display_results(results: Dict[str, Dict[str, Dict[str, Any]]]):
    """Display test results in a formatted table."""
    
    for category, category_results in results.items():
        console.print(f"\\n[bold blue]{category}[/bold blue]")
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Test", style="cyan", no_wrap=True)
        table.add_column("Status", style="magenta")
        table.add_column("Details", style="green")
        
        for test_name, result in category_results.items():
            status = result['status']
            details = result['details']
            
            if status == 'success':
                status_icon = "✅ Pass"
                status_style = "green"
            else:
                status_icon = "❌ Fail"
                status_style = "red"
            
            # Truncate long details
            if len(details) > 60:
                details = details[:57] + "..."
            
            table.add_row(
                test_name,
                f"[{status_style}]{status_icon}[/{status_style}]",
                details
            )
        
        console.print(table)

def generate_summary(results: Dict[str, Dict[str, Dict[str, Any]]]):
    """Generate a summary of test results."""
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for category_results in results.values():
        for result in category_results.values():
            total_tests += 1
            if result['status'] == 'success':
                passed_tests += 1
            else:
                failed_tests += 1
    
    pass_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
    
    summary = f"""
[bold]Test Summary[/bold]
Total Tests: {total_tests}
Passed: [green]{passed_tests}[/green]
Failed: [red]{failed_tests}[/red]
Pass Rate: [blue]{pass_rate:.1f}%[/blue]
"""
    
    if pass_rate == 100:
        summary += "\\n[green]🎉 All tests passed! Your setup is ready.[/green]"
    elif pass_rate >= 80:
        summary += "\\n[yellow]⚠️  Most tests passed. Check failed tests for issues.[/yellow]"
    else:
        summary += "\\n[red]❌ Many tests failed. Please check your configuration.[/red]"
    
    console.print(Panel(summary, border_style="blue"))

def show_next_steps(results: Dict[str, Dict[str, Dict[str, Any]]]):
    """Show next steps based on test results."""
    
    failed_services = []
    
    for category, category_results in results.items():
        if category == 'External Services':
            for test_name, result in category_results.items():
                if result['status'] != 'success':
                    failed_services.append(test_name)
    
    if not failed_services:
        console.print("\\n[green]🚀 All integrations are working! You can start using the tool.[/green]")
        console.print("\\nNext steps:")
        console.print("1. Run: [cyan]python src/cli.py process --file your_transcript.txt[/cyan]")
        console.print("2. Or start monitoring: [cyan]python src/cli.py watch --folder ./transcripts[/cyan]")
    else:
        console.print("\\n[yellow]⚠️  Some integrations need attention:[/yellow]")
        for service in failed_services:
            console.print(f"- {service}: Check API credentials in .env file")
        
        console.print("\\nTo fix issues:")
        console.print("1. Check your .env file has all required API keys")
        console.print("2. Run: [cyan]python src/cli.py setup[/cyan] to reconfigure")
        console.print("3. For Google Drive: [cyan]python scripts/setup_google_auth.py[/cyan]")

async def main():
    """Main function."""
    console.print(Panel.fit(
        "[bold blue]Meeting Automation Tool - Integration Tests[/bold blue]\\n"
        "Testing all components and integrations...",
        border_style="blue"
    ))
    
    # Check if .env file exists
    if not Path('.env').exists():
        console.print("[yellow]⚠️  .env file not found. Some tests may fail.[/yellow]")
        console.print("Run [cyan]cp .env.example .env[/cyan] and configure your API keys.\\n")
    
    # Run tests
    results = await run_all_tests()
    
    # Display results
    display_results(results)
    
    # Generate summary
    generate_summary(results)
    
    # Show next steps
    show_next_steps(results)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\\n[yellow]Tests interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\\n[red]Test runner failed: {e}[/red]")