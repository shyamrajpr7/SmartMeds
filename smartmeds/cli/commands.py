"""
SmartMeds CLI commands.

Provides a rich command-line interface for managing medications,
checking interactions, and viewing schedules.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box
from rich.text import Text

from smartmeds import __version__
from smartmeds.core.interactions import InteractionChecker
from smartmeds.core.medication import (
    Dosage,
    DosageUnit,
    FrequencyUnit,
    Medication,
    MedicationSchedule,
)
from smartmeds.core.scheduler import MedicationScheduler
from smartmeds.utils.helpers import format_datetime

console = Console()
scheduler = MedicationScheduler()
interaction_checker = InteractionChecker()


def _print_banner() -> None:
    """Print the SmartMeds welcome banner."""
    banner = Text()
    banner.append("💊 SmartMeds", style="bold cyan")
    banner.append(f" v{__version__}", style="dim")
    console.print(Panel(banner, border_style="cyan", padding=(0, 2)))


@click.group()
@click.version_option(__version__, "--version", "-V", message="SmartMeds %(version)s")
def main() -> None:
    """
    💊 SmartMeds — Intelligent Medication Management System

    Manage your medications, check interactions, and track your schedules
    all from the command line.
    """
    _print_banner()


@main.command("add")
@click.option("--name", "-n", required=True, help="Medication name")
@click.option("--dose", "-d", required=True, type=float, help="Dosage amount")
@click.option(
    "--unit",
    "-u",
    default="tablet",
    type=click.Choice([u.value for u in DosageUnit]),
    help="Dosage unit",
)
@click.option(
    "--frequency",
    "-f",
    default="daily",
    type=click.Choice([f.value for f in FrequencyUnit]),
    help="Frequency",
)
@click.option("--times", "-t", default="08:00", help="Dose times (HH:MM, comma-separated)")
@click.option("--prescriber", "-p", default=None, help="Prescribing doctor")
@click.option("--notes", default="", help="Additional notes")
@click.option("--pills", default=None, type=int, help="Initial pill count")
def add_medication(
    name: str,
    dose: float,
    unit: str,
    frequency: str,
    times: str,
    prescriber: Optional[str],
    notes: str,
    pills: Optional[int],
) -> None:
    """Add a new medication to your schedule."""
    try:
        specific_times = []
        for t_str in times.split(","):
            t_str = t_str.strip()
            h, m = map(int, t_str.split(":"))
            specific_times.append(time(h, m))

        med = Medication(
            name=name,
            dosage=Dosage(amount=dose, unit=DosageUnit(unit)),
            schedule=MedicationSchedule(
                frequency=FrequencyUnit(frequency),
                times_per_day=len(specific_times),
                specific_times=specific_times,
            ),
            prescriber=prescriber,
            notes=notes,
            pills_remaining=pills,
        )
        scheduler.add_medication(med)

        console.print(
            f"\n[bold green]✅ Added:[/bold green] [cyan]{name}[/cyan] "
            f"({dose} {unit}) — [yellow]{frequency}[/yellow] at {times}"
        )
        if prescriber:
            console.print(f"   Prescribed by: [dim]{prescriber}[/dim]")
        if pills is not None:
            console.print(f"   Pills remaining: [magenta]{pills}[/magenta]")
    except Exception as e:
        console.print(f"[bold red]❌ Error:[/bold red] {e}")
        raise SystemExit(1)


@main.command("list")
def list_medications() -> None:
    """List all medications currently in your schedule."""
    meds = scheduler.list_medications()
    if not meds:
        console.print("[dim]No medications found. Use 'smartmeds add' to get started.[/dim]")
        return

    table = Table(
        title="📋 Your Medications",
        box=box.ROUNDED,
        border_style="cyan",
        show_lines=True,
    )
    table.add_column("#", style="dim", width=4)
    table.add_column("Name", style="bold cyan", min_width=15)
    table.add_column("Dosage", style="yellow")
    table.add_column("Frequency", style="green")
    table.add_column("Times", style="white")
    table.add_column("Status", style="bold")
    table.add_column("Refill ⚠️", style="magenta")

    for i, med in enumerate(meds, 1):
        status = "[green]Active[/green]" if med.is_active() else "[red]Inactive[/red]"
        refill = "[red]⚠️  Soon[/red]" if med.needs_refill() else "[dim]OK[/dim]"
        times_str = ", ".join(t.strftime("%H:%M") for t in med.schedule.specific_times)

        table.add_row(
            str(i),
            med.name,
            str(med.dosage),
            med.schedule.frequency.value,
            times_str,
            status,
            refill,
        )

    console.print(table)


@main.command("schedule")
def show_schedule() -> None:
    """Show upcoming doses for the next 24 hours."""
    events = scheduler.get_upcoming_doses(hours=24)
    if not events:
        console.print("[dim]No upcoming doses in the next 24 hours.[/dim]")
        return

    table = Table(
        title="⏰ Upcoming Doses (Next 24h)",
        box=box.ROUNDED,
        border_style="yellow",
        show_lines=True,
    )
    table.add_column("Time", style="bold yellow", width=8)
    table.add_column("Medication", style="bold cyan")
    table.add_column("Dosage", style="white")
    table.add_column("Status", style="bold")

    for event in events:
        status = "✅ Taken" if event.taken else ("⚠️  Overdue" if event.is_overdue() else "⏳ Pending")
        table.add_row(
            event.scheduled_time.strftime("%H:%M"),
            event.medication.name,
            str(event.medication.dosage),
            status,
        )

    console.print(table)


@main.command("check")
@click.argument("medications", nargs=-1, required=True)
def check_interactions(medications: tuple) -> None:
    """
    Check for drug interactions between medications.

    \b
    Example:
        smartmeds check warfarin aspirin metformin
    """
    med_list = list(medications)
    console.print(f"\n🔍 Checking interactions for: [cyan]{', '.join(med_list)}[/cyan]\n")

    interactions = interaction_checker.check(med_list)

    if not interactions:
        console.print("[bold green]✅ No known interactions found![/bold green]")
        return

    for interaction in interactions:
        severity_colors = {
            "low": "yellow",
            "moderate": "orange1",
            "high": "red",
            "contraindicated": "bold red",
        }
        color = severity_colors.get(interaction.severity.value, "white")

        panel = Panel(
            f"[bold]{interaction.drug_a}[/bold] + [bold]{interaction.drug_b}[/bold]\n\n"
            f"{interaction.description}\n\n"
            f"[dim]💡 Recommendation:[/dim] {interaction.recommendation}",
            title=f"[{color}]⚠️  {interaction.severity.value.upper()} INTERACTION[/{color}]",
            border_style=color,
        )
        console.print(panel)


@main.command("remove")
@click.argument("name")
def remove_medication(name: str) -> None:
    """Remove a medication from your schedule."""
    if scheduler.remove_medication(name):
        console.print(f"[bold green]✅ Removed:[/bold green] [cyan]{name}[/cyan]")
    else:
        console.print(f"[bold red]❌ Medication not found:[/bold red] [cyan]{name}[/cyan]")


if __name__ == "__main__":
    main()
