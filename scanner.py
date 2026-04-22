import os
import subprocess
import json
import tkinter as tk
from tkinter import filedialog
import google.generativeai as genai

# Try importing rich for dashboard UI
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich.progress import Progress, SpinnerColumn, TextColumn
except ImportError:
    print("Please install 'rich' for the Dashboard UI: pip install rich")
    exit(1)

console = Console()

# --- CONFIGURATION ---
# Replace with your actual Gemini API Key
GEMINI_API_KEY = "AIzaSyAV1xwliNPAWBxvDsPXYrxhdGIRktqehXs"

def count_files(directory):
    count = 0
    for root, _, files in os.walk(directory):
        count += len(files)
    return count

def main():
    # 0. Setup beautiful Dashboard Header
    console.print(Panel.fit(
        "[bold cyan]AI-Powered Security Code Scanner[/bold cyan]\n"
        "[italic]Semgrep & Gemini 2.5 Integration[/italic]",
        border_style="cyan"
    ))

    # 1. Setup the AI Model
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-2.5-flash')

    # 2. Open a UI window to select a target folder to scan
    root = tk.Tk()
    root.withdraw() # Hides the blank background window
    
    # Needs to be on top to ensure user sees the prompt
    root.attributes('-topmost', True)
    
    console.print("\n[bold yellow][*] Waiting for user to select a folder to scan...[/bold yellow]")
    folder_path = filedialog.askdirectory(title="Select Target Folder to Scan with Semgrep")

    if not folder_path:
        console.print("[bold red][X] No folder selected. Exiting.[/bold red]")
        return

    # Count files in the selected folder
    total_files = count_files(folder_path)

    # Show selection details
    console.print(Panel(
        f"[bold green]Target Directory Selected:[/bold green] {folder_path}\n"
        f"[bold green]Total Files Found:[/bold green] {total_files}",
        title="[bold blue]Scan Target Overview[/bold blue]",
        border_style="green"
    ))

    # Create a custom environment to force Windows Python to use UTF-8
    custom_env = os.environ.copy()
    custom_env["PYTHONUTF8"] = "1"

    # 3. Run Semgrep and capture the JSON output directly in memory
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="[bold cyan]1/2 Running Semgrep Analysis... (This might take a moment)[/bold cyan]", total=None)
        
        process = subprocess.run(
            ["semgrep", "scan", "--config=auto", "--json", folder_path],
            capture_output=True,
            text=True,
            shell=True,
            env=custom_env,
            encoding="utf-8"
        )

    try:
        # Try to parse the output as JSON
        semgrep_data = json.loads(process.stdout)
        findings = semgrep_data.get('results', [])
    except json.JSONDecodeError:
        # If it fails, print exactly what Semgrep actually said!
        console.print("[bold red][!] Semgrep ran, but didn't output valid JSON. Here is the raw error:[/bold red]")
        console.print("-" * 40)
        console.print("STDOUT (Standard Output):", process.stdout)
        console.print("-" * 40)
        console.print("STDERR (Standard Error):", process.stderr)
        console.print("-" * 40)
        return

    if not findings:
        console.print("[bold green][*] Scan complete: No vulnerabilities found! Code looks clean.[/bold green]")
        return

    console.print(f"[bold yellow][*] Found {len(findings)} vulnerabilities in {total_files} files scanned.[/bold yellow]")

    # 4. Filter the JSON data so we don't overload the AI with unnecessary data
    simplified_findings = []
    for issue in findings:
        simplified_findings.append({
            "file": issue.get("path"),
            "line": issue.get("start", {}).get("line"),
            "vulnerability": issue.get("check_id"),
            "message": issue.get("extra", {}).get("message"),
            "severity": issue.get("extra", {}).get("severity")
        })

    # 5. Ask the AI to format the report
    prompt = f"""
    You are a strict security auditor. I scanned apps with Semgrep.
    Review this raw JSON data and output ONLY a single Markdown table. 
    
    Rules to save tokens:
    1. DO NOT write an introduction or conclusion.
    2. DO NOT write long explanations.
    3. Group identical vulnerabilities together if they occur in multiple files.
    4. Format the table with these columns: [File Path] | [Line] | [Severity] | [Vulnerability] | [1-Sentence Fix]
    
    Raw Data:
    {json.dumps(simplified_findings, indent=2)}
    """

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="[bold magenta]2/2 Generating AI Security Report...[/bold magenta]", total=None)
        
        try:
            response = model.generate_content(prompt)
            report_markdown = response.text
        except Exception as e:
            console.print(f"[bold red][!] AI generation failed: {e}[/bold red]")
            return

    # Output AI Report to Terminal
    console.print("\n[bold cyan]=== AI Security Review Dashboard ===[/bold cyan]")
    console.print(Markdown(report_markdown))
    console.print("[bold cyan]======================================[/bold cyan]\n")

    # 6. Prompt user to save the report and let them select a directory
    try:
        console.print("[bold yellow]Do you want to save this report to a file? (y/n):[/bold yellow] ", end="")
        choice = input().strip().lower()
    except EOFError:
        choice = 'n'

    if choice == 'y':
        console.print("\n[bold yellow][*] Waiting for user to select a save directory...[/bold yellow]")
        
        # Bring root to top so the save dialog is visible
        root.attributes('-topmost', True)
        save_dir = filedialog.askdirectory(title="Select Directory to Save Security Report")
        
        if save_dir:
            report_path = os.path.join(save_dir, "AI_Security_Report.md")
            try:
                with open(report_path, "w", encoding="utf-8") as f:
                    f.write(report_markdown)
                console.print(f"[bold green][✓] Professional report saved to:[/bold green] {report_path}")
            except Exception as e:
                console.print(f"[bold red][X] Failed to save report: {e}[/bold red]")
        else:
            console.print("[bold red][X] Save directory selection cancelled. Report was not saved.[/bold red]")
    else:
        console.print("[bold cyan][*] Skipping save. Exiting dashboard.[/bold cyan]")


if __name__ == "__main__":
    main()