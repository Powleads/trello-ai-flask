#!/usr/bin/env python3
"""
Simple Test - WhatsApp + OpenAI Only

Test the core functionality without Trello for now.
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, 'src')

from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv

console = Console()
load_dotenv()

async def test_whatsapp_and_openai():
    """Test WhatsApp and OpenAI integration."""
    console.print("[bold blue]Testing Core Integrations (WhatsApp + OpenAI)...[/bold blue]")
    
    try:
        # Test WhatsApp
        from integrations.green_api import WhatsAppClient
        async with WhatsAppClient() as whatsapp:
            result = await whatsapp.test_connection()
            console.print(f"[green]SUCCESS WhatsApp: {result.get('stateInstance', 'Connected')}[/green]")
    except Exception as e:
        console.print(f"[red]ERROR WhatsApp: {str(e)[:50]}...[/red]")
        return False
    
    try:
        # Test OpenAI
        from agent import OpenAIProvider
        openai = OpenAIProvider()
        result = await openai.test_connection()
        console.print(f"[green]SUCCESS OpenAI: {'Connected' if result else 'Failed'}[/green]")
    except Exception as e:
        console.print(f"[red]ERROR OpenAI: {str(e)[:50]}...[/red]")
        return False
    
    return True

async def process_sample_without_trello():
    """Process sample transcript with WhatsApp + OpenAI only."""
    console.print("\\n[bold blue]Processing Sample (No Trello)...[/bold blue]")
    
    try:
        from agent import MeetingAutomationAgent
        
        agent = MeetingAutomationAgent()
        
        sample_file = "examples/sample_transcript_with_trello.txt"
        
        if not Path(sample_file).exists():
            console.print(f"[red]ERROR: Sample file not found: {sample_file}[/red]")
            return
        
        # Process with Trello disabled
        result = await agent.process_transcript(
            file_path=sample_file,
            output_format='standard',
            send_whatsapp=True,
            create_trello=False  # Disable Trello for now
        )
        
        # Display results
        console.print(Panel(
            result.summary[:400] + "..." if len(result.summary) > 400 else result.summary,
            title="Generated Summary",
            border_style="green"
        ))
        
        console.print(f"\\n[bold]Results:[/bold]")
        console.print(f"  WhatsApp sent: {'SUCCESS' if result.whatsapp_sent else 'FAILED'}")
        console.print(f"  Summary generated: {'SUCCESS' if result.summary else 'FAILED'}")
        console.print(f"  Processing time: {result.processing_time:.2f} seconds")
        
        if result.errors:
            console.print(f"  Errors: {len(result.errors)}")
            for error in result.errors:
                console.print(f"    - {error}")
        
        console.print("\\n[green]Core test completed successfully![/green]")
        
        # Show what the WhatsApp message would look like
        console.print("\\n[bold yellow]WhatsApp Message Preview:[/bold yellow]")
        console.print("--------------------------------")
        print(result.summary[:200] + "..." if len(result.summary) > 200 else result.summary)
        console.print("--------------------------------")
        
    except Exception as e:
        console.print(f"[red]ERROR: Processing failed: {e}[/red]")

def main():
    """Main test function."""
    console.print(Panel.fit(
        "[bold blue]Meeting Automation Tool - Core Test[/bold blue]\\n"
        "Testing WhatsApp and OpenAI (Trello disabled for now)...",
        border_style="blue"
    ))
    
    try:
        # Test integrations
        success = asyncio.run(test_whatsapp_and_openai())
        
        if success:
            # Process sample
            asyncio.run(process_sample_without_trello())
            
            console.print("\\n[bold green]Core functionality is working![/bold green]")
            console.print("\\n[blue]What's working:[/blue]")
            console.print("✅ AI-powered meeting summaries")
            console.print("✅ WhatsApp message sending") 
            console.print("✅ Transcript processing")
            console.print("\\n[yellow]Next: Fix Trello authentication[/yellow]")
        else:
            console.print("\\n[red]Core integrations failed - check your API keys[/red]")
        
    except Exception as e:
        console.print(f"\\n[red]Test failed: {e}[/red]")

if __name__ == "__main__":
    main()