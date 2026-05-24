"""News blackout integration — blocks entries before high-impact economic events."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CalendarEvent:
    name: str
    time: str
    currency: str
    impact: str


@dataclass
class NewsBlackoutResult:
    blackout_active: bool
    blocked: bool
    events_in_blackout: list = field(default_factory=list)
    next_high_impact_event: Optional[CalendarEvent] = None
    remaining_minutes: Optional[int] = None


def check_news_blackout(
    events: Optional[list] = None,
    blackout_minutes: int = 30,
    current_time: Optional[str] = None,
) -> NewsBlackoutResult:
    """Check if we are in a news blackout period.

    This is a pure function — it receives event data from the caller
    (typically mcp-market-analysis) and determines blackout status.
    No HTTP calls or scraping inside this module.

    Args:
        events: List of dicts with keys: name, time (ISO), currency, impact
        blackout_minutes: Minutes before/after event to block trading
        current_time: ISO timestamp for "now" (defaults to utcnow)
    """
    if events is None:
        events = []

    now = datetime.fromisoformat(current_time) if current_time else datetime.now(timezone.utc)

    events_in_window = []
    next_event = None
    min_remaining = None

    for ev in events:
        try:
            ev_time = datetime.fromisoformat(ev["time"])
        except (KeyError, ValueError):
            continue

        diff_minutes = (ev_time - now).total_seconds() / 60

        if abs(diff_minutes) <= blackout_minutes:
            events_in_window.append(CalendarEvent(
                name=ev.get("name", "Unknown"),
                time=ev.get("time", ""),
                currency=ev.get("currency", "USD"),
                impact=ev.get("impact", "HIGH"),
            ))

        if diff_minutes > 0 and (min_remaining is None or diff_minutes < min_remaining):
            min_remaining = diff_minutes
            next_event = CalendarEvent(
                name=ev.get("name", "Unknown"),
                time=ev.get("time", ""),
                currency=ev.get("currency", "USD"),
                impact=ev.get("impact", "HIGH"),
            )

    blackout_active = len(events_in_window) > 0

    return NewsBlackoutResult(
        blackout_active=blackout_active,
        blocked=blackout_active,
        events_in_blackout=events_in_window,
        next_high_impact_event=next_event,
        remaining_minutes=int(min_remaining) if min_remaining else None,
    )
