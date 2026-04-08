import os
import datetime
from zoneinfo import ZoneInfo

from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from langchain_core.tools import tool

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = "Asia/Kolkata"
TZ = ZoneInfo(TIMEZONE)
WORK_START = 9   # 09:00
WORK_END   = 18  # 18:00


# ---------------------------------------------------------------------------
# Google Calendar service helper
# ---------------------------------------------------------------------------
def get_calendar_service():
    """Authenticate and return a Google Calendar API service object."""
    creds = None

    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            "credentials.json",
            SCOPES,
            redirect_uri="urn:ietf:wg:oauth:2.0:oob",
        )
        auth_url, _ = flow.authorization_url(prompt="consent")
        print("\n-> Open this URL in your browser:\n", auth_url)
        code = input("\n-> Paste the authorization code here: ").strip()
        flow.fetch_token(code=code)
        creds = flow.credentials
        with open("token.json", "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ---------------------------------------------------------------------------
# Helper: fetch events on a given date
# ---------------------------------------------------------------------------
def _fetch_events_on_date(service, date_str: str) -> list[dict]:
    """
    Return a list of raw event dicts for the given date (YYYY-MM-DD).
    Each dict has keys: summary, start_dt, end_dt.
    """
    day = datetime.date.fromisoformat(date_str)
    time_min = datetime.datetime(day.year, day.month, day.day, 0, 0, tzinfo=TZ).isoformat()
    time_max = datetime.datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=TZ).isoformat()

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    events = []
    for item in result.get("items", []):
        start_raw = item["start"].get("dateTime", item["start"].get("date"))
        end_raw   = item["end"].get("dateTime",   item["end"].get("date"))
        try:
            start_dt = datetime.datetime.fromisoformat(start_raw)
            end_dt   = datetime.datetime.fromisoformat(end_raw)
        except Exception:
            continue
        events.append(
            {
                "summary":  item.get("summary", "(no title)"),
                "start_dt": start_dt,
                "end_dt":   end_dt,
            }
        )
    return events


# ---------------------------------------------------------------------------
# Tool 1 – get_calendar_events  (Task 3)
# ---------------------------------------------------------------------------
@tool
def get_calendar_events(date: str) -> str:
    """
    Fetch all Google Calendar events on a specific date.

    Args:
        date: Date in YYYY-MM-DD format (e.g. "2025-07-14")

    Returns:
        A human-readable summary of events for that day, or a message if none exist.
    """
    service = get_calendar_service()
    events  = _fetch_events_on_date(service, date)

    if not events:
        return f"No events found on {date}."

    lines = [f"Events on {date}:"]
    for ev in events:
        start = ev["start_dt"].strftime("%H:%M")
        end   = ev["end_dt"].strftime("%H:%M")
        lines.append(f"  • {ev['summary']}  [{start} – {end}]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 2 – create_event  (Task 2 + Task 3 guards)
# ---------------------------------------------------------------------------
@tool
def create_event(
    title: str,
    date: str,
    start_time: str,
    duration_minutes: int,
    attendee_email: str = None,
) -> str:
    """
    Create a meeting in Google Calendar after validating the requested slot.

    Args:
        title:            Meeting title / subject.
        date:             Date in YYYY-MM-DD format.
        start_time:       Start time in HH:MM (24-hour) format.
        duration_minutes: Duration of the meeting in minutes.
        attendee_email:   Optional – email address of an attendee to invite.

    Returns:
        A confirmation message with the event link, or an error description.
    """
    # ---- Parse requested time ----
    try:
        start_dt = datetime.datetime.strptime(f"{date} {start_time}", "%Y-%m-%d %H:%M")
        start_dt = start_dt.replace(tzinfo=TZ)
    except ValueError as exc:
        return f"[Error] Could not parse date/time: {exc}"

    end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)

    # ---- Guard 1: Past-date check ----
    now = datetime.datetime.now(tz=TZ)
    if start_dt < now:
        return (
            f"[Error] The requested time ({date} {start_time}) is in the past. "
            "Please provide a future date and time."
        )

    # ---- Guard 2: Conflict / overlap check ----
    service = get_calendar_service()
    existing = _fetch_events_on_date(service, date)

    for ev in existing:
        ev_start = ev["start_dt"]
        ev_end   = ev["end_dt"]
        # Make timezone-aware for comparison if needed
        if ev_start.tzinfo is None:
            ev_start = ev_start.replace(tzinfo=TZ)
        if ev_end.tzinfo is None:
            ev_end = ev_end.replace(tzinfo=TZ)

        if start_dt < ev_end and end_dt > ev_start:
            return (
                f"[Conflict] The slot {start_time}–{end_dt.strftime('%H:%M')} overlaps "
                f"with an existing event: \"{ev['summary']}\" "
                f"({ev_start.strftime('%H:%M')}–{ev_end.strftime('%H:%M')}). "
                "Please choose a different time."
            )

    # ---- Create the event ----
    event_body = {
        "summary": title,
        "start": {
            "dateTime": start_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
        "end": {
            "dateTime": end_dt.isoformat(),
            "timeZone": TIMEZONE,
        },
    }
    if attendee_email:
        event_body["attendees"] = [{"email": attendee_email}]

    created = (
        service.events()
        .insert(calendarId="primary", body=event_body)
        .execute()
    )
    link = created.get("htmlLink", "(no link)")
    return f"[Success] Event \"{title}\" created on {date} at {start_time}. Link: {link}"


# ---------------------------------------------------------------------------
# Tool 3 – find_free_slots  (Task 4)
# ---------------------------------------------------------------------------
@tool
def find_free_slots(date: str, duration_minutes: int) -> str:
    """
    Find all free time slots on a given date that can fit a meeting of the
    requested duration, within working hours (09:00 – 18:00).

    Args:
        date:             Date in YYYY-MM-DD format.
        duration_minutes: Required meeting duration in minutes.

    Returns:
        A list of available time windows, or a message if none exist.
    """
    service = get_calendar_service()
    events  = _fetch_events_on_date(service, date)

    day       = datetime.date.fromisoformat(date)
    work_start = datetime.datetime(day.year, day.month, day.day, WORK_START, 0, tzinfo=TZ)
    work_end   = datetime.datetime(day.year, day.month, day.day, WORK_END,   0, tzinfo=TZ)
    delta      = datetime.timedelta(minutes=duration_minutes)

    # Build list of busy intervals, clamped to working hours
    busy = []
    for ev in events:
        s = ev["start_dt"] if ev["start_dt"].tzinfo else ev["start_dt"].replace(tzinfo=TZ)
        e = ev["end_dt"]   if ev["end_dt"].tzinfo   else ev["end_dt"].replace(tzinfo=TZ)
        s = max(s, work_start)
        e = min(e, work_end)
        if s < e:
            busy.append((s, e))
    busy.sort(key=lambda x: x[0])

    # Find gaps
    free_slots = []
    cursor = work_start
    for s, e in busy:
        if cursor + delta <= s:
            free_slots.append((cursor, s))
        cursor = max(cursor, e)
    if cursor + delta <= work_end:
        free_slots.append((cursor, work_end))

    if not free_slots:
        return f"No free slots on {date} for a {duration_minutes}-minute meeting."

    lines = [f"Free slots on {date} (≥{duration_minutes} min):"]
    for slot_start, slot_end in free_slots:
        lines.append(f"  • {slot_start.strftime('%H:%M')} – {slot_end.strftime('%H:%M')}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 4 – analyse_booking_patterns  (Task 4)
# ---------------------------------------------------------------------------
@tool
def analyse_booking_patterns() -> str:
    """
    Analyse the user's Google Calendar events from the past 30 days to
    surface scheduling habits: busiest days, lightest days, preferred hours,
    and average meeting duration.

    Returns:
        A structured text summary of the user's booking patterns.
    """
    service = get_calendar_service()
    now      = datetime.datetime.now(tz=TZ)
    time_min = (now - datetime.timedelta(days=30)).isoformat()
    time_max = now.isoformat()

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=200,
        )
        .execute()
    )

    items = result.get("items", [])
    if not items:
        return "No events found in the past 30 days."

    day_counts     = {}   # weekday name → count
    hour_counts    = {}   # hour int → count
    total_duration = 0    # minutes
    valid_count    = 0

    for item in items:
        start_raw = item["start"].get("dateTime", item["start"].get("date"))
        end_raw   = item["end"].get("dateTime",   item["end"].get("date"))
        try:
            start_dt = datetime.datetime.fromisoformat(start_raw)
            end_dt   = datetime.datetime.fromisoformat(end_raw)
        except Exception:
            continue

        weekday = start_dt.strftime("%A")
        hour    = start_dt.hour
        minutes = int((end_dt - start_dt).total_seconds() / 60)

        day_counts[weekday]  = day_counts.get(weekday, 0) + 1
        hour_counts[hour]    = hour_counts.get(hour, 0) + 1
        total_duration      += minutes
        valid_count         += 1

    sorted_days  = sorted(day_counts.items(),  key=lambda x: -x[1])
    sorted_hours = sorted(hour_counts.items(), key=lambda x: -x[1])
    avg_duration = total_duration // valid_count if valid_count else 0

    busiest_day  = sorted_days[0][0]  if sorted_days  else "N/A"
    lightest_day = sorted_days[-1][0] if len(sorted_days) > 1 else "N/A"
    peak_hours   = ", ".join(f"{h:02d}:00" for h, _ in sorted_hours[:3]) or "N/A"

    summary = (
        f"📊 Booking Patterns (last 30 days, {valid_count} events)\n"
        f"  • Busiest day   : {busiest_day} ({sorted_days[0][1]} meetings)\n"
        f"  • Lightest day  : {lightest_day} ({sorted_days[-1][1]} meetings)\n"
        f"  • Peak hours    : {peak_hours}\n"
        f"  • Avg duration  : {avg_duration} minutes\n"
        f"  • Meetings/day  :\n"
        + "\n".join(f"      {d}: {c}" for d, c in sorted_days)
    )
    return summary


# ---------------------------------------------------------------------------
# Bonus Tool – query_calendar_insights
# ---------------------------------------------------------------------------
@tool
def query_calendar_insights(question: str) -> str:
    """
    Answer open-ended questions about the user's calendar, such as:
    - "Which days am I free this week?"
    - "What was my busiest day this month?"
    - "How many hours of meetings do I have this week?"

    Args:
        question: A natural-language question about the user's schedule.

    Returns:
        A plain-text answer computed from the user's Google Calendar data.
    """
    service = get_calendar_service()
    now     = datetime.datetime.now(tz=TZ)
    q       = question.lower()

    # ---- Determine time window ----
    if "this week" in q:
        start_of_window = now - datetime.timedelta(days=now.weekday())   # Monday
        end_of_window   = start_of_window + datetime.timedelta(days=6)   # Sunday
    elif "this month" in q:
        start_of_window = now.replace(day=1, hour=0, minute=0, second=0)
        # First day of next month
        if now.month == 12:
            end_of_window = now.replace(year=now.year + 1, month=1, day=1)
        else:
            end_of_window = now.replace(month=now.month + 1, day=1)
    else:
        # Default: next 7 days
        start_of_window = now
        end_of_window   = now + datetime.timedelta(days=7)

    time_min = start_of_window.replace(hour=0, minute=0, second=0).isoformat()
    time_max = end_of_window.replace(hour=23, minute=59, second=59).isoformat()

    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=time_min,
            timeMax=time_max,
            singleEvents=True,
            orderBy="startTime",
            maxResults=200,
        )
        .execute()
    )
    items = result.get("items", [])

    # ---- "how many hours" ----
    if "how many hours" in q:
        total_min = 0
        for item in items:
            s = item["start"].get("dateTime")
            e = item["end"].get("dateTime")
            if s and e:
                total_min += int(
                    (
                        datetime.datetime.fromisoformat(e)
                        - datetime.datetime.fromisoformat(s)
                    ).total_seconds()
                    / 60
                )
        hours   = total_min // 60
        minutes = total_min % 60
        return f"You have {hours}h {minutes}m of meetings in the requested period."

    # ---- "busiest day" ----
    if "busiest" in q:
        day_counts = {}
        for item in items:
            s = item["start"].get("dateTime", item["start"].get("date"))
            if s:
                d = datetime.datetime.fromisoformat(s).strftime("%A, %Y-%m-%d")
                day_counts[d] = day_counts.get(d, 0) + 1
        if not day_counts:
            return "No events found in the requested period."
        busiest = max(day_counts, key=day_counts.get)
        return f"Your busiest day was {busiest} with {day_counts[busiest]} meeting(s)."

    # ---- "free days" / "which days am I free" ----
    if "free" in q:
        busy_dates = set()
        for item in items:
            s = item["start"].get("dateTime", item["start"].get("date"))
            if s:
                busy_dates.add(datetime.datetime.fromisoformat(s).date())
        free_days = []
        cursor = start_of_window.date()
        while cursor <= end_of_window.date():
            if cursor not in busy_dates:
                free_days.append(cursor.strftime("%A, %Y-%m-%d"))
            cursor += datetime.timedelta(days=1)
        if not free_days:
            return "You have meetings every day in that period."
        return "Days with no meetings:\n" + "\n".join(f"  • {d}" for d in free_days)

    # ---- Fallback: list all events ----
    if not items:
        return "No events found for that period."
    lines = [f"Events ({start_of_window.date()} → {end_of_window.date()}):"]
    for item in items:
        s = item["start"].get("dateTime", item["start"].get("date"))
        dt_str = datetime.datetime.fromisoformat(s).strftime("%a %d %b %H:%M") if s else "?"
        lines.append(f"  • {item.get('summary', '(no title)')} — {dt_str}")
    return "\n".join(lines)
