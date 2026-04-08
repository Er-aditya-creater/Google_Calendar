"""
main.py  –  Entry point for the AI Meeting Scheduler.

Run:
    python main.py
"""

from agent import create_scheduler_agent

BANNER = """
╔══════════════════════════════════════════════════════╗
║        AI Meeting Scheduler  (Gemini + LangChain)   ║
║  Type 'help' for example prompts  |  'exit' to quit ║
╚══════════════════════════════════════════════════════╝
"""

HELP_TEXT = """
Example prompts
───────────────
Scheduling
  • Schedule a 1-hour meeting called Team Sync tomorrow at 10am
  • Book a 30-minute standup at 9am this Friday
  • Set up a 45-min call with raj@example.com on Monday at 3pm

Calendar queries (Bonus)
  • Which days am I free this week?
  • What was my busiest day this month?
  • How many hours of meetings do I have this week?
  • Show me my schedule for tomorrow

Type 'exit' to quit.
"""


def main():
    print(BANNER)
    agent = create_scheduler_agent()
    print("Authenticating with Google Calendar…")
    # Trigger OAuth on startup so the user authenticates before the first query
    from tools import get_calendar_service
    svc = get_calendar_service()
    cal = svc.calendarList().get(calendarId="primary").execute()
    print(f"✓ Connected to calendar: {cal.get('summary', 'primary')}\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            print("Goodbye!")
            break
        if user_input.lower() == "help":
            print(HELP_TEXT)
            continue

        print()
        result = agent(user_input)
        print(f"\nAssistant: {result}\n")
        print("─" * 60)


if __name__ == "__main__":
    main()
