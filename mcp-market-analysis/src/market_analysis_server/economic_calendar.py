"""Forex Factory economic calendar integration.

This is the only scraping-based module in the system.
Isolated for easy replacement if a paid API becomes available.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass
class CalendarEvent:
    name: str
    time: str  # ISO format
    currency: str
    impact: str  # "HIGH", "MEDIUM", "LOW"
    previous: str = ""
    forecast: str = ""


@dataclass
class EconomicCalendarResult:
    events: list = field(default_factory=list)
    blackout_active: bool = False
    next_high_impact: Optional[CalendarEvent] = None
    remaining_minutes: Optional[int] = None
    error: str = ""


# Known high-impact events schedule (manually updated)
# This is a fallback when scraping is unavailable
FALLBACK_HIGH_IMPACT_SLOTS = {
    # NFP: First Friday of each month at 12:30 UTC
    # FOMC: Scheduled by Federal Reserve (8 meetings/year)
    # CPI: Monthly, ~2nd week
}


def check_economic_calendar(
    currency: str = "USD",
    impact_filter: str = "HIGH",
    window_minutes: int = 60,
) -> EconomicCalendarResult:
    """Fetch economic calendar events from Forex Factory.

    Attempts to scrape the calendar page. Falls back to an empty
    result if scraping fails (fail-open: no blackout rather than
    blocking trades on a scraping error).
    """
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        return EconomicCalendarResult(
            error="Missing dependencies: requests, beautifulsoup4"
        )

    try:
        url = "https://www.forexfactory.com/calendar"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")
        events = []
        now = datetime.now(timezone.utc)

        # Parse calendar rows
        table = soup.find("table", class_="calendar__table")
        if not table:
            return EconomicCalendarResult(
                error="Could not find calendar table on Forex Factory"
            )

        rows = table.find_all("tr", class_="calendar__row")
        for row in rows:
            try:
                # Extract time
                time_cell = row.find("td", class_="calendar__time")
                if not time_cell:
                    continue

                time_str = time_cell.get_text(strip=True)

                # Extract currency
                currency_cell = row.find("td", class_="calendar__currency")
                if not currency_cell:
                    continue
                curr = currency_cell.get_text(strip=True)

                if curr.upper() != currency.upper():
                    continue

                # Extract impact
                impact_cell = row.find("td", class_="calendar__impact")
                if not impact_cell:
                    continue
                impact_spans = impact_cell.find_all("span", class_="impact")
                impact = "MEDIUM"
                if len(impact_spans) >= 3:
                    impact = "HIGH"
                elif len(impact_spans) >= 2:
                    impact = "MEDIUM"
                else:
                    impact = "LOW"

                if impact_filter != "ALL" and impact != impact_filter:
                    continue

                # Extract event name
                event_cell = row.find("td", class_="calendar__event")
                if not event_cell:
                    continue
                name = event_cell.get_text(strip=True)

                events.append({
                    "name": name,
                    "time": time_str,
                    "currency": curr,
                    "impact": impact,
                })
            except Exception:
                continue

        # Check blackout: are any events within the window?
        blackout = False
        next_event = None
        min_remaining = None

        for ev in events:
            diff_minutes = _parse_time_diff(ev["time"], now)
            if diff_minutes is None:
                continue

            if abs(diff_minutes) <= window_minutes:
                blackout = True

            if diff_minutes > 0 and (min_remaining is None or diff_minutes < min_remaining):
                min_remaining = diff_minutes
                next_event = CalendarEvent(
                    name=ev["name"],
                    time=ev["time"],
                    currency=ev["currency"],
                    impact=ev["impact"],
                )

        return EconomicCalendarResult(
            events=[
                CalendarEvent(
                    name=e["name"],
                    time=e["time"],
                    currency=e["currency"],
                    impact=e["impact"],
                )
                for e in events
            ],
            blackout_active=blackout,
            next_high_impact=next_event,
            remaining_minutes=int(min_remaining) if min_remaining else None,
        )

    except Exception as e:
        return EconomicCalendarResult(
            error=f"Failed to fetch calendar: {e}"
        )


def _parse_time_diff(time_str: str, now: datetime) -> Optional[float]:
    """Parse Forex Factory time string and compute difference in minutes.

    Returns None if parsing fails.
    """
    # Forex Factory times are typically like "12:30pm" or "9:00am"
    # They are in ET (Eastern Time)
    try:
        from datetime import timedelta

        time_str = time_str.lower().replace(".", "").strip()
        is_pm = "pm" in time_str
        time_str = time_str.replace("am", "").replace("pm", "").strip()

        parts = time_str.split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0

        if is_pm and hour != 12:
            hour += 12
        if not is_pm and hour == 12:
            hour = 0

        # ET is UTC-4 (EDT) or UTC-5 (EST) — approximate as UTC-4
        et_offset = -4
        event_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        event_time = event_time - timedelta(hours=et_offset)

        # If the event time is more than 12 hours behind, it might be for the next day
        diff = (event_time - now).total_seconds() / 60
        return diff
    except Exception:
        return None
