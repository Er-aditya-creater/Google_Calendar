"""
agent.py  –  LangChain agent for the AI Meeting Scheduler.

Covers:
  Task 2 – simple tool invocation (create_event)
  Task 3 – multi-step loop + conflict / past-date handling
  Task 4 – smart alternative suggestions when a conflict is detected
  Bonus  – calendar intelligence queries
"""

import os
import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()

TIMEZONE = "Asia/Kolkata"
TZ = ZoneInfo(TIMEZONE)

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from tools import (
    create_event,
    get_calendar_events,
    find_free_slots,
    analyse_booking_patterns,
    query_calendar_insights,
)

# ---------------------------------------------------------------------------
# All tools registered with the agent
# ---------------------------------------------------------------------------
ALL_TOOLS = [
    create_event,
    get_calendar_events,
    find_free_slots,
    analyse_booking_patterns,
    query_calendar_insights,
]

TOOL_MAP = {t.name: t for t in ALL_TOOLS}

# ---------------------------------------------------------------------------
# System prompt — built dynamically so today's date is always accurate
# ---------------------------------------------------------------------------
def build_system_prompt() -> str:
    now       = datetime.datetime.now(tz=TZ)
    today_str = now.strftime("%A, %Y-%m-%d")   # e.g. "Wednesday, 2025-04-09"
    tomorrow  = (now + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    day_after  = (now + datetime.timedelta(days=2)).strftime("%Y-%m-%d")

    return f"""You are an intelligent AI meeting scheduler connected to the user's
Google Calendar. You have access to the following tools:

1. get_calendar_events(date)          – Retrieve all events on a given date.
2. create_event(title, date,           – Create a new event. Has built-in guards for
   start_time, duration_minutes,         past dates and scheduling conflicts.
   attendee_email?)
3. find_free_slots(date,               – Find available slots on a date.
   duration_minutes)
4. analyse_booking_patterns()          – Analyse the user's last 30 days of calendar
                                         history to surface scheduling habits.
5. query_calendar_insights(question)   – Answer open-ended calendar questions
                                         (free days, busiest day, total meeting hours…).

### IMPORTANT — Current date/time context
- Today is       : {today_str}
- Current time   : {now.strftime("%H:%M")} IST
- Tomorrow is    : {tomorrow}
- Day after      : {day_after}
- Timezone       : Asia/Kolkata (IST, UTC+5:30)

When the user says "tomorrow", use date {tomorrow}.
When the user says "today",    use date {now.strftime("%Y-%m-%d")}.
When the user says "this Friday / Monday / Wednesday" etc., calculate the
correct YYYY-MM-DD date relative to today ({today_str}) and use that exact date.
Always pass dates to tools in YYYY-MM-DD format.

### Workflow when scheduling a meeting
Step 1  Call get_calendar_events on the requested date to check for conflicts.
Step 2  Attempt create_event.
Step 3  If create_event returns a [Conflict] error:
          a. Call analyse_booking_patterns to learn the user's lightest days.
          b. Call find_free_slots on the requested date.
          c. Call find_free_slots on 1-2 of the user's lightest days.
          d. Present 2-3 ranked alternatives with a clear reason for each.
Step 4  If create_event returns a [Error] (past date), inform the user politely.

### Workflow for calendar questions
Detect the intent, then call query_calendar_insights or analyse_booking_patterns.

Always be concise, helpful, and professional. Never expose raw JSON to the user.
"""


# ---------------------------------------------------------------------------
# Agent factory
# ---------------------------------------------------------------------------
def create_scheduler_agent():
    """Return a callable run_agent(user_input) -> str."""

    llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite-preview", temperature=0)
    llm_with_tools = llm.bind_tools(ALL_TOOLS)

    def run_agent(user_input: str) -> str:
        # Seed the conversation with system instructions + user message
        messages = [
            HumanMessage(content=build_system_prompt() + "\n\nUser: " + user_input),
        ]

        # Multi-step agentic loop (Task 3 requirement)
        MAX_ITERATIONS = 8
        for iteration in range(MAX_ITERATIONS):
            response: AIMessage = llm_with_tools.invoke(messages)
            messages.append(response)

            # If no tool calls → LLM gave a final text answer
            if not response.tool_calls:
                return response.content or "[No response]"

            # Execute every tool the LLM requested
            for tc in response.tool_calls:
                tool_name = tc["name"]
                tool_args = tc["args"]
                tool_id   = tc["id"]

                print(f"\n[Agent] Calling tool '{tool_name}' with args: {tool_args}")

                tool_fn = TOOL_MAP.get(tool_name)
                if tool_fn is None:
                    tool_result = f"[Error] Unknown tool: {tool_name}"
                else:
                    try:
                        tool_result = tool_fn.invoke(tool_args)
                    except Exception as exc:
                        tool_result = f"[Tool Error] {exc}"

                print(f"[Agent] Tool result: {tool_result}")

                # Append the tool result so the LLM sees it in the next turn
                messages.append(
                    ToolMessage(content=str(tool_result), tool_call_id=tool_id)
                )

        return "[Error] Agent did not reach a conclusion within the iteration limit."

    return run_agent
