#!/usr/bin/env python3
"""
Quick Test Script for Meeting Automation Tool

Run this to test your setup with sample data.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

console = Console()

def setup_environment():
    """Copy .env.example to .env if it doesn't exist."""
    if not Path('.env').exists():
        if Path('.env.example').exists():
            import shutil
            shutil.copy('.env.example', '.env')
            console.print("[green]SUCCESS: Created .env file from template[/green]")
        else:
            console.print("[red]ERROR: .env.example not found![/red]")
            return False
    
    load_dotenv()
    return True

async def test_integrations():
    """Test all integrations quickly."""
    console.print("[bold blue]Testing Integrations...[/bold blue]")
    
    try:
        # Test WhatsApp
        from integrations.green_api import WhatsAppClient
        async with WhatsAppClient() as whatsapp:
            result = await whatsapp.test_connection()
            console.print(f"[green]SUCCESS WhatsApp: {result.get('stateInstance', 'Connected')}[/green]")
    except Exception as e:
        console.print(f"[yellow]WARNING WhatsApp: {str(e)[:50]}...[/yellow]")
    
    try:
        # Test Trello
        from integrations.trello import TrelloClient
        async with TrelloClient() as trello:
            user = await trello.test_connection()
            console.print(f"[green]SUCCESS Trello: Connected as {user.get('fullName', 'User')}[/green]")
    except Exception as e:
        console.print(f"[yellow]WARNING Trello: {str(e)[:50]}...[/yellow]")
    
    try:
        # Test OpenAI
        from agent import OpenAIProvider
        openai = OpenAIProvider()
        result = await openai.test_connection()
        console.print(f"[green]SUCCESS OpenAI: {'Connected' if result else 'Failed'}[/green]")
    except Exception as e:
        console.print(f"[yellow]WARNING OpenAI: {str(e)[:50]}...[/yellow]")

async def process_sample():
    """Process the sample transcript."""
    console.print("\\n[bold blue]Processing Sample Transcript...[/bold blue]")
    
    try:
        from agent import MeetingAutomationAgent
        
        agent = MeetingAutomationAgent()
        
        # Use the Trello sample transcript
        sample_file = "examples/sample_transcript_with_trello.txt"
        
        if not Path(sample_file).exists():
            console.print(f"[red]ERROR: Sample file not found: {sample_file}[/red]")
            return
        
        result = await agent.process_transcript(
            file_path=sample_file,
            output_format='standard',
            send_whatsapp=True,
            create_trello=True
        )
        
        # Display results
        console.print(Panel(
            result.summary[:400] + "..." if len(result.summary) > 400 else result.summary,
            title="Generated Summary",
            border_style="green"
        ))
        
        console.print(f"\\n[bold]Results:[/bold]")
        console.print(f"  WhatsApp sent: {'SUCCESS' if result.whatsapp_sent else 'FAILED'}")
        console.print(f"  Trello cards updated: {len(result.trello_cards_created)}")
        
        if result.errors:
            console.print(f"  Errors: {len(result.errors)}")
            for error in result.errors:
                console.print(f"    - {error}")
        
        console.print("\\n[green]Test completed successfully![/green]")
        
    except Exception as e:
        console.print(f"[red]ERROR: Processing failed: {e}[/red]")

def main():
    """Main test function."""
    console.print(Panel.fit(
        "[bold blue]Meeting Automation Tool - Quick Test[/bold blue]\\n"
        "Testing all integrations and processing sample transcript...",
        border_style="blue"
    ))
    
    # Setup environment
    if not setup_environment():
        return
    
    # Run tests
    try:
        asyncio.run(test_integrations())
        asyncio.run(process_sample())
        
        console.print("\\n[bold green]All tests completed![/bold green]")
        console.print("\\n[blue]Next steps:[/blue]")
        console.print("1. Check your WhatsApp group for the summary")
        console.print("2. Check your Trello board for updated card comments")
        console.print("3. Try with your own transcript: [cyan]python src/cli.py process --file your_file.txt[/cyan]")
        
    except KeyboardInterrupt:
        console.print("\\n[yellow]Test interrupted by user[/yellow]")
    except Exception as e:
        console.print(f"\\n[red]Test failed: {e}[/red]")

if __name__ == "__main__":
    main()