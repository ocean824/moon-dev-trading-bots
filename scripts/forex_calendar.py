"""
🌙 Moon Dev's Forex Factory Calendar Scraper 📅
================================================
Fetches today's economic news events from Forex Factory
and displays them nicely in the terminal.

The next upcoming event is highlighted in YELLOW!

Moon Dev 🌙
"""

import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
import os
import time
from colorama import Fore, Back, Style, init

init(autoreset=True)

# Forex Factory requires browser-like headers
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0',
}

MOON_DEV_BANNER = f"""
{Fore.CYAN}{'='*70}
{Fore.MAGENTA}  🌙 MOON DEV'S FOREX FACTORY CALENDAR 📅
{Fore.CYAN}{'='*70}
{Fore.WHITE}  Economic news events for today - Next event highlighted in YELLOW!
{Fore.CYAN}{'='*70}
"""


def get_forex_calendar(date=None):
    """
    Fetch Forex Factory calendar for a specific date.
    Date format: jan7.2026
    """
    if date is None:
        # Use today's date
        today = datetime.now()
        date = today.strftime("%b%d.%Y").lower().replace(" ", "")
        # Remove leading zero from day (jan07 -> jan7)
        date = re.sub(r'(\w{3})0(\d)', r'\1\2', date)

    url = f"https://www.forexfactory.com/calendar?day={date}"

    session = requests.Session()
    response = session.get(url, headers=HEADERS, timeout=15)
    response.raise_for_status()

    return response.text, date


def parse_calendar(html):
    """
    Parse the Forex Factory calendar HTML and extract events.
    Moon Dev's parser! 🔍
    """
    soup = BeautifulSoup(html, 'html.parser')
    events = []

    # Find the calendar table
    table = soup.find('table', class_='calendar__table')
    if not table:
        print(f"{Fore.RED}❌ Moon Dev couldn't find calendar table!")
        return events

    rows = table.find_all('tr', class_='calendar__row')

    current_time = None

    for row in rows:
        # Skip non-event rows
        if 'calendar__row--day-breaker' in row.get('class', []):
            continue

        event = {}

        # Get time
        time_cell = row.find('td', class_='calendar__time')
        if time_cell:
            time_text = time_cell.get_text(strip=True)
            if time_text:
                current_time = time_text
        event['time'] = current_time or ''

        # Get currency
        currency_cell = row.find('td', class_='calendar__currency')
        if currency_cell:
            event['currency'] = currency_cell.get_text(strip=True)
        else:
            event['currency'] = ''

        # Get impact
        impact_cell = row.find('td', class_='calendar__impact')
        if impact_cell:
            impact_span = impact_cell.find('span')
            if impact_span:
                impact_class = impact_span.get('class', [])
                if any('high' in c for c in impact_class):
                    event['impact'] = 'HIGH'
                elif any('medium' in c for c in impact_class):
                    event['impact'] = 'MED'
                elif any('low' in c for c in impact_class):
                    event['impact'] = 'LOW'
                else:
                    event['impact'] = ''
            else:
                event['impact'] = ''
        else:
            event['impact'] = ''

        # Get event name
        event_cell = row.find('td', class_='calendar__event')
        if event_cell:
            event_link = event_cell.find('a') or event_cell.find('span', class_='calendar__event-title')
            if event_link:
                event['name'] = event_link.get_text(strip=True)
            else:
                event['name'] = event_cell.get_text(strip=True)
        else:
            event['name'] = ''

        # Get actual value
        actual_cell = row.find('td', class_='calendar__actual')
        event['actual'] = actual_cell.get_text(strip=True) if actual_cell else ''

        # Get forecast value
        forecast_cell = row.find('td', class_='calendar__forecast')
        event['forecast'] = forecast_cell.get_text(strip=True) if forecast_cell else ''

        # Get previous value
        previous_cell = row.find('td', class_='calendar__previous')
        event['previous'] = previous_cell.get_text(strip=True) if previous_cell else ''

        # Only add if we have an event name
        if event['name']:
            events.append(event)

    return events


def parse_event_time(time_str, date_str):
    """
    Parse event time and return datetime object.
    Handles formats like "8:30am", "10:00pm", "All Day", "Tentative"
    """
    if not time_str or time_str in ['All Day', 'Tentative', 'Day 1', 'Day 2', 'Day 3']:
        return None

    try:
        # Parse the date from date_str (e.g., "jan7.2026")
        date_match = re.match(r'(\w{3})(\d{1,2})\.(\d{4})', date_str)
        if not date_match:
            return None

        month_str, day, year = date_match.groups()
        month_map = {'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
                     'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}
        month = month_map.get(month_str.lower(), 1)

        # Parse time (e.g., "8:30am")
        time_match = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_str.lower())
        if time_match:
            hour, minute, ampm = time_match.groups()
            hour = int(hour)
            minute = int(minute)
            if ampm == 'pm' and hour != 12:
                hour += 12
            elif ampm == 'am' and hour == 12:
                hour = 0

            return datetime(int(year), month, int(day), hour, minute)
    except Exception:
        pass

    return None


def find_next_event(events, date_str):
    """
    Find the index of the next upcoming event.
    Moon Dev highlights this one! 🎯
    """
    now = datetime.now()
    next_idx = None
    min_diff = None

    for i, event in enumerate(events):
        event_time = parse_event_time(event['time'], date_str)
        if event_time:
            diff = (event_time - now).total_seconds()
            # Only consider future events or events within the last 5 minutes
            if diff > -300:  # -5 minutes
                if min_diff is None or diff < min_diff:
                    min_diff = diff
                    next_idx = i

    return next_idx


def print_calendar(events, date_str):
    """
    Print the calendar in a nice terminal format.
    Moon Dev's beautiful output! ✨
    Only shows HIGH impact events (red folder)
    """
    # Filter to only HIGH impact events
    high_impact_events = [e for e in events if e['impact'] == 'HIGH']

    print(MOON_DEV_BANNER)

    # Parse date for display
    date_match = re.match(r'(\w{3})(\d{1,2})\.(\d{4})', date_str)
    if date_match:
        month_str, day, year = date_match.groups()
        print(f"{Fore.WHITE}  📅 Date: {month_str.upper()} {day}, {year}")
        print(f"{Fore.WHITE}  🕐 Current Time: {datetime.now().strftime('%I:%M %p')}")
    print(f"{Fore.CYAN}{'='*60}\n")

    if not high_impact_events:
        print(f"{Fore.YELLOW}  No HIGH impact events today! 🎉")
        print(f"\n{Fore.CYAN}{'='*60}\n")
        return

    # Find next event (from high impact only)
    next_idx = find_next_event(high_impact_events, date_str)

    # Print header - simplified
    print(f"{Fore.WHITE}  {'TIME':<10} {'EVENT':<40} {'FORE':<10} {'PREV':<10}")
    print(f"{Fore.CYAN}  {'-'*10} {'-'*40} {'-'*10} {'-'*10}")

    for i, event in enumerate(high_impact_events):
        time_str = event['time'][:10] if event['time'] else ''
        name = event['name'][:40] if event['name'] else ''
        forecast = event['forecast'][:10] if event['forecast'] else ''
        previous = event['previous'][:10] if event['previous'] else ''

        # Highlight next event with yellow background
        if i == next_idx:
            print(f"{Back.YELLOW}{Fore.BLACK}  {time_str:<10} {name:<40} {forecast:<10} {previous:<10}{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}  ⬆️  NEXT UP! ⬆️{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}  {time_str:<10} {name:<40} {forecast:<10} {previous:<10}")

    print(f"\n{Fore.CYAN}{'='*60}")
    print(f"{Fore.GREEN}  🌙 Moon Dev - {len(high_impact_events)} HIGH impact events")
    print(f"{Fore.CYAN}{'='*60}\n")


REFRESH_MINUTES = 15  # Moon Dev's refresh interval
DAYS_AHEAD = 3  # How many days to look ahead


def main():
    """
    Moon Dev's main function 🚀
    Runs on a loop, refreshing every 15 minutes
    Shows next 7 days of HIGH impact events
    """
    while True:
        # Clear screen
        os.system('cls' if os.name == 'nt' else 'clear')

        print(MOON_DEV_BANNER)
        print(f"{Fore.WHITE}  🕐 Current Time: {datetime.now().strftime('%I:%M %p')}")
        print(f"{Fore.WHITE}  📅 Showing next {DAYS_AHEAD} days (HIGH + MEDIUM impact)")
        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.YELLOW}  Loading...", end='', flush=True)

        all_events = []

        # Fetch next 3 days
        for day_offset in range(DAYS_AHEAD):
            target_date = datetime.now() + timedelta(days=day_offset)
            date = target_date.strftime("%b%d.%Y").lower()
            date = re.sub(r'(\w{3})0(\d)', r'\1\2', date)

            html, date_str = get_forex_calendar(date)
            events = parse_calendar(html)

            # Filter HIGH and MEDIUM impact events
            for event in events:
                if event['impact'] in ['HIGH', 'MED']:
                    event['date'] = target_date.strftime('%a %b %d')
                    event['date_str'] = date_str
                    all_events.append(event)

        print(f"\r{' '*20}\n")  # Clear loading message

        if not all_events:
            print(f"{Fore.YELLOW}  No HIGH/MEDIUM impact events in the next {DAYS_AHEAD} days! 🎉\n")
        else:
            # Print header
            print(f"{Fore.WHITE}  {'DATE':<12} {'TIME':<10} {'EVENT':<38} {'FORE':<8} {'PREV':<8}")
            print(f"{Fore.CYAN}  {'-'*12} {'-'*10} {'-'*38} {'-'*8} {'-'*8}")

            # Find next upcoming event
            now = datetime.now()
            next_idx = None
            for i, event in enumerate(all_events):
                event_time = parse_event_time(event['time'], event['date_str'])
                if event_time and event_time > now:
                    next_idx = i
                    break

            high_count = 0
            med_count = 0
            for i, event in enumerate(all_events):
                date_str = event['date']
                time_str = event['time'][:10] if event['time'] else ''
                name = event['name'][:38] if event['name'] else ''
                forecast = event['forecast'][:8] if event['forecast'] else ''
                previous = event['previous'][:8] if event['previous'] else ''

                if event['impact'] == 'HIGH':
                    high_count += 1
                    # RED background for HIGH impact
                    print(f"{Back.RED}{Fore.WHITE}  {date_str:<12} {time_str:<10} {name:<38} {forecast:<8} {previous:<8}{Style.RESET_ALL}")
                else:
                    med_count += 1
                    # Orange/yellow text for MEDIUM impact
                    print(f"{Fore.YELLOW}  {date_str:<12} {time_str:<10} {name:<38} {forecast:<8} {previous:<8}")

                if i == next_idx:
                    print(f"{Fore.CYAN}  ⬆️  NEXT UP! ⬆️{Style.RESET_ALL}")

            print(f"\n{Fore.GREEN}  🌙 Moon Dev - {high_count} HIGH (red) + {med_count} MEDIUM (yellow)")

        print(f"{Fore.CYAN}{'='*60}")
        print(f"{Fore.CYAN}  🔄 Auto-refresh in {REFRESH_MINUTES} min | Ctrl+C to exit{Style.RESET_ALL}\n")

        time.sleep(REFRESH_MINUTES * 60)


if __name__ == "__main__":
    main()
