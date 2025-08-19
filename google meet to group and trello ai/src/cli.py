#!/usr/bin/env python3
"""
Meeting Automation Tool CLI

A command-line interface for the meeting automation system that processes
transcripts, generates summaries, and distributes them via WhatsApp and Trello.
"""

import asyncio
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm, Prompt
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Import our modules
try:
    from agent import MeetingAutomationAgent
    from integrations.google_drive import GoogleDriveClient
    from integrations.green_api import WhatsAppClient
    from integrations.trello import TrelloClient
except ImportError as e:
    rprint(f"[red]Error importing modules: {e}[/red]")
    rprint("[yellow]Make sure you're in the project root directory and dependencies are installed[/yellow]")
    sys.exit(1)

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Meeting Automation Tool - AI-powered transcript processing and distribution."""
    pass


@cli.command()
@click.option('--file', '-f', 'file_path', required=True, type=click.Path(exists=True), 
              help='Path to the transcript file to process')
@click.option('--format', '-fmt', 'output_format', default='standard', 
              type=click.Choice(['standard', 'detailed', 'brief']),
              help='Output format for the summary')
@click.option('--output', '-o', 'output_path', type=click.Path(), 
              help='Output file path for the summary')
@click.option('--send-whatsapp/--no-whatsapp', default=True,
              help='Send summary via WhatsApp')
@click.option('--update-trello/--no-trello', default=True,
              help='Find and update existing Trello cards mentioned in meeting')
def process(file_path: str, output_format: str, output_path: Optional[str], 
           send_whatsapp: bool, update_trello: bool):
    """Process a single transcript file and generate summary."""
    
    with console.status("[bold green]Processing transcript..."):
        try:
            # Initialize the automation agent
            agent = MeetingAutomationAgent()
            
            # Process the transcript
            result = asyncio.run(agent.process_transcript(
                file_path=file_path,
                output_format=output_format,
                send_whatsapp=send_whatsapp,
                create_trello=update_trello
            ))
            
            # Save output if specified
            if output_path:
                Path(output_path).write_text(result.summary)
                console.print(f"[green]Summary saved to: {output_path}[/green]")
            
            # Display results
            _display_processing_results(result)
            
        except Exception as e:
            console.print(f"[red]Error processing transcript: {e}[/red]")
            sys.exit(1)


@cli.command()
@click.option('--folder', '-f', required=True, type=click.Path(exists=True),
              help='Folder to monitor for new transcript files')
@click.option('--interval', '-i', default=30, type=int,
              help='Polling interval in seconds (default: 30)')
@click.option('--recursive/--no-recursive', default=True,
              help='Monitor subfolders recursively')
def watch(folder: str, interval: int, recursive: bool):
    """Monitor a folder for new transcript files and process them automatically."""
    
    console.print(f"[green]Starting to monitor: {folder}[/green]")
    console.print(f"[blue]Polling interval: {interval} seconds[/blue]")
    console.print(f"[blue]Recursive monitoring: {recursive}[/blue]")
    console.print("[yellow]Press Ctrl+C to stop monitoring[/yellow]")
    
    try:
        agent = MeetingAutomationAgent()
        asyncio.run(agent.watch_folder(
            folder_path=folder,
            interval=interval,
            recursive=recursive
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped by user[/yellow]")
    except Exception as e:
        console.print(f"[red]Error during monitoring: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option('--service', '-s', 
              type=click.Choice(['all', 'google-drive', 'whatsapp', 'trello', 'openai']),
              default='all', help='Service to test (default: all)')
@click.option('--verbose', '-v', is_flag=True, help='Show detailed test results')
def test(service: str, verbose: bool):
    """Test connections to all integrated services."""
    
    console.print("[bold blue]Testing service connections...[/bold blue]\n")
    
    services_to_test = []
    if service == 'all':
        services_to_test = ['google-drive', 'whatsapp', 'trello', 'openai']
    else:
        services_to_test = [service]
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        for svc in services_to_test:
            task = progress.add_task(f"Testing {svc}...", total=None)
            
            try:
                result = asyncio.run(_test_service(svc, verbose))
                results[svc] = result
                progress.update(task, description=f"✅ {svc}")
            except Exception as e:
                results[svc] = {'status': 'error', 'message': str(e)}
                progress.update(task, description=f"❌ {svc}")
    
    # Display results table
    _display_test_results(results, verbose)


@cli.command()
@click.option('--force', is_flag=True, help='Overwrite existing configuration')
def setup(force: bool):
    """Interactive setup wizard for configuring the automation tool."""
    
    console.print(Panel.fit(
        "[bold blue]Meeting Automation Tool Setup[/bold blue]\n"
        "This wizard will help you configure all necessary API connections.",
        border_style="blue"
    ))
    
    env_file = Path('.env')
    
    if env_file.exists() and not force:
        if not Confirm.ask("Configuration file already exists. Overwrite?"):
            console.print("[yellow]Setup cancelled[/yellow]")
            return
    
    config = {}
    
    # Google Drive configuration
    console.print("\n[bold]📁 Google Drive Configuration[/bold]")
    config['GOOGLE_CLIENT_ID'] = Prompt.ask("Google Client ID")
    config['GOOGLE_CLIENT_SECRET'] = Prompt.ask("Google Client Secret", password=True)
    
    # Green API configuration
    console.print("\n[bold]💬 WhatsApp (Green API) Configuration[/bold]")
    config['GREEN_API_INSTANCE_ID'] = Prompt.ask("Green API Instance ID")
    config['GREEN_API_TOKEN'] = Prompt.ask("Green API Token", password=True)
    
    # Trello configuration
    console.print("\n[bold]📋 Trello Configuration[/bold]")
    config['TRELLO_API_KEY'] = Prompt.ask("Trello API Key")
    config['TRELLO_TOKEN'] = Prompt.ask("Trello Token", password=True)
    
    # AI Provider configuration
    console.print("\n[bold]🤖 AI Provider Configuration[/bold]")
    if Confirm.ask("Configure OpenAI?", default=True):
        config['OPENAI_API_KEY'] = Prompt.ask("OpenAI API Key", password=True)
    
    # Database configuration
    console.print("\n[bold]🗄️ Database Configuration[/bold]")
    config['DATABASE_URL'] = Prompt.ask(
        "Database URL", 
        default="postgresql://user:pass@localhost:5432/meetingdb"
    )
    config['REDIS_URL'] = Prompt.ask(
        "Redis URL", 
        default="redis://localhost:6379"
    )
    
    # Write configuration to .env file
    with open('.env', 'w') as f:
        for key, value in config.items():
            f.write(f"{key}={value}\n")
    
    console.print("\n[green]✅ Configuration saved to .env file[/green]")
    console.print("[yellow]Run 'python src/cli.py test' to verify your configuration[/yellow]")


@cli.command()
@click.option('--input-dir', '-i', required=True, type=click.Path(exists=True),
              help='Directory containing transcript files')
@click.option('--output-dir', '-o', required=True, type=click.Path(),
              help='Directory to save processed summaries')
@click.option('--pattern', '-p', default='*.txt',
              help='File pattern to match (default: *.txt)')
def batch_process(input_dir: str, output_dir: str, pattern: str):
    """Process multiple transcript files in batch."""
    
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    # Find matching files
    files = list(input_path.glob(pattern))
    
    if not files:
        console.print(f"[yellow]No files found matching pattern: {pattern}[/yellow]")
        return
    
    console.print(f"[blue]Found {len(files)} files to process[/blue]")
    
    agent = MeetingAutomationAgent()
    processed = 0
    errors = 0
    
    with Progress(console=console) as progress:
        task = progress.add_task("Processing files...", total=len(files))
        
        for file_path in files:
            try:
                result = asyncio.run(agent.process_transcript(str(file_path)))
                
                # Save summary
                output_file = output_path / f"{file_path.stem}_summary.md"
                output_file.write_text(result.summary)
                
                processed += 1
                progress.update(task, advance=1, 
                              description=f"Processed: {file_path.name}")
                
            except Exception as e:
                errors += 1
                console.print(f"[red]Error processing {file_path.name}: {e}[/red]")
                progress.update(task, advance=1)
    
    console.print(f"\n[green]Batch processing complete![/green]")
    console.print(f"Processed: {processed} files")
    console.print(f"Errors: {errors} files")


async def _test_service(service: str, verbose: bool) -> dict:
    """Test a specific service connection."""
    
    if service == 'google-drive':
        client = GoogleDriveClient()
        await client.test_connection()
        return {'status': 'success', 'message': 'Connected successfully'}
    
    elif service == 'whatsapp':
        client = WhatsAppClient()
        result = await client.test_connection()
        return {'status': 'success', 'message': f'Instance status: {result.get("stateInstance", "unknown")}'}
    
    elif service == 'trello':
        client = TrelloClient()
        user = await client.test_connection()
        return {'status': 'success', 'message': f'Connected as: {user.get("fullName", "unknown")}'}
    
    elif service == 'openai':
        from processors.summarizer import MeetingSummarizer
        summarizer = MeetingSummarizer()
        await summarizer.test_connection()
        return {'status': 'success', 'message': 'API key valid'}
    
    else:
        raise ValueError(f"Unknown service: {service}")


def _display_test_results(results: dict, verbose: bool):
    """Display service test results in a formatted table."""
    
    table = Table(title="Service Connection Test Results")
    table.add_column("Service", style="cyan", no_wrap=True)
    table.add_column("Status", style="magenta")
    table.add_column("Details", style="green")
    
    for service, result in results.items():
        status = result['status']
        message = result.get('message', '')
        
        if status == 'success':
            status_icon = "✅ Success"
            status_style = "green"
        else:
            status_icon = "❌ Failed"
            status_style = "red"
        
        table.add_row(
            service.title(),
            f"[{status_style}]{status_icon}[/{status_style}]",
            message if verbose else message[:50] + "..." if len(message) > 50 else message
        )
    
    console.print(table)


def _display_processing_results(result):
    """Display the results of transcript processing."""
    
    console.print("\n[bold green]Processing Complete![/bold green]\n")
    
    # Summary section
    console.print(Panel(
        result.summary[:500] + "..." if len(result.summary) > 500 else result.summary,
        title="📝 Meeting Summary",
        border_style="blue"
    ))
    
    # Action items
    if result.action_items:
        console.print("\n[bold]📋 Action Items:[/bold]")
        for i, item in enumerate(result.action_items, 1):
            console.print(f"  {i}. {item.description}")
            if item.assignee:
                console.print(f"     👤 Assigned to: {item.assignee}")
            if item.due_date:
                console.print(f"     📅 Due: {item.due_date}")
    
    # Distribution status
    console.print("\n[bold]📤 Distribution Status:[/bold]")
    if result.whatsapp_sent:
        console.print("  ✅ WhatsApp message sent")
    if result.trello_cards_created:
        console.print(f"  ✅ {len(result.trello_cards_created)} Trello cards updated with meeting notes")


if __name__ == '__main__':
    cli()