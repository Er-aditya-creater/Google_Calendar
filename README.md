# AI Meeting Scheduler — LangChain + Google Calendar

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![LangChain](https://img.shields.io/badge/LangChain-latest-green)
![Gemini](https://img.shields.io/badge/Gemini-1.5--flash-orange)
![License](https://img.shields.io/badge/License-MIT-yellow)

An AI-powered meeting scheduler that understands **natural language requests**, checks your real **Google Calendar** for conflicts, creates events, suggests **smart alternatives** when a slot is blocked, and answers open-ended calendar questions — all from a simple terminal chat interface.

Built as a LangChain lab assignment demonstrating multi-step agentic reasoning with real external API integration.

---

## Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Architecture](#architecture)
- [Setup Guide](#setup-guide)
- [Running the Agent](#running-the-agent)
- [Example Interactions](#example-interactions)
- [Tool Reference](#tool-reference)
- [Task Coverage](#task-coverage)
- [Known Issues and Fixes](#known-issues-and-fixes)
- [License](#license)

---

## Features

- **Natural language scheduling** — say "Book a call tomorrow at 3pm" instead of filling forms
- **Real Google Calendar integration** — events actually appear in your calendar
- **Past-date guard** — rejects requests for times that have already passed
- **Conflict detection** — checks for overlapping events before creating anything
- **Smart alternative suggestions** — when a slot is taken, analyses your booking patterns and suggests 2-3 ranked alternatives with reasons
- **Calendar intelligence** — answers questions like "Which days am I free this week?" or "How many hours of meetings do I have?"
- **Attendee invites** — optionally invite someone by email when creating an event
- **Date-aware LLM** — today's date is injected into every prompt so "tomorrow", "this Friday" etc. always resolve correctly

---

## Project Structure

```
25CS60R45/
├── tools.py           <- All LangChain @tool definitions (5 tools)
├── agent.py           <- Multi-step agentic loop + dynamic system prompt
├── main.py            <- Entry point / interactive chat loop
├── requirements.txt   <- Python dependencies
├── .gitignore         <- Excludes secrets from Git
├── LICENSE            <- MIT License
├── README.md          <- This file
│
├── .env               <- YOUR GEMINI API KEY  (never commit — in .gitignore)
├── credentials.json   <- FROM GOOGLE CLOUD    (never commit — in .gitignore)
└── token.json         <- AUTO-GENERATED       (never commit — in .gitignore)
```

---

## Architecture

```
User Input (natural language)
        |
        v
  build_system_prompt()
  [injects today's date, tomorrow's date, current IST time]
        |
        v
  Gemini 1.5 Flash LLM
  [bound with 5 tools via bind_tools()]
        |
        v
  response.tool_calls populated?
    |
    |-- YES --> execute tool(s)
    |           append ToolMessage to history
    |           loop back to LLM  (up to 8 iterations)
    |
    |-- NO  --> return final text answer to user
```

The agent runs in a **multi-step agentic loop**. Each tool result is appended
to the conversation as a `ToolMessage` so the LLM has full context before
deciding its next action. This enables complex multi-step reasoning such as:
check calendar → detect conflict → analyse patterns → find free slots → suggest alternatives.

---

## Setup Guide

### Step 1 — Clone the repository

```bash
git clone https://github.com/Er-aditya-creater/Google_Calendar
cd Google_Calendar
```

### Step 2 — Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

Or install manually:

```bash
pip install langchain langchain-google-genai google-auth \
            google-auth-oauthlib google-api-python-client python-dotenv
```

### Step 4 — Get a Gemini API Key

1. Visit https://aistudio.google.com/app/apikey
2. Click **Create API Key** and copy it
3. Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_gemini_api_key_here
```

> **Free tier limits:**
> - `gemini-2.5-flash` — 20 requests/day (too low for testing)
> - `gemini-1.5-flash` — 1500 requests/day (recommended)
>
> To switch models, change one line in `agent.py`:
> ```python
> llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
> ```

### Step 5 — Enable Google Calendar API

1. Go to https://console.cloud.google.com
2. Create a new project (or select an existing one)
3. Navigate to **APIs & Services → Library**
4. Search for **Google Calendar API** and click **Enable**

> Skipping this step causes a `403 accessNotConfigured` error on first run.
> You can also enable it directly at:
> https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview

### Step 6 — Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client ID**
3. Set **Application type** to **Desktop App**, give it any name, click **Create**
4. Click the **Download JSON** (⬇) icon next to your new credential
5. Rename the downloaded file to exactly `credentials.json`
6. Place it in the project root (same folder as `main.py`)

### Step 7 — Add Yourself as a Test User

Because the app is in development/testing mode, Google only allows whitelisted Gmail accounts to authenticate. Without this step you will get an "Access blocked" error.

1. Go to **APIs & Services → OAuth consent screen**
2. Scroll to the **Test users** section
3. Click **Add Users**, enter your Gmail address, click **Save**

> If you still see the "App not verified" warning after adding yourself,
> click **Advanced → Go to [app name] (unsafe)** to proceed.
> This is completely safe for your own personal development app.

### Step 8 — First-Run Authentication (one-time only)

Because the app runs in a terminal with no browser redirect, authentication uses a manual copy-paste code flow:

1. Run `python3 main.py`
2. A long Google OAuth URL is printed in the terminal
3. Open that URL in any browser
4. Log in with the Gmail address you whitelisted in Step 7
5. Click **Allow** to grant Calendar permissions
6. Google displays an authorization code — copy the entire code
7. Paste it back into the terminal where it says `-> Paste the authorization code here:`
8. Press Enter — `token.json` is created automatically
9. All future runs skip this step entirely

---

## Running the Agent

```bash
python3 main.py
```

Successful startup looks like:

```
╔══════════════════════════════════════════════════════╗
║        AI Meeting Scheduler  (Gemini + LangChain)   ║
║  Type 'help' for example prompts  |  'exit' to quit ║
╚══════════════════════════════════════════════════════╝

Authenticating with Google Calendar...
✓ Connected to calendar: your.email@gmail.com

You:
```

Type `help` to see example prompts. Type `exit` to quit.

---

## Example Interactions

### Task 2 — Basic Scheduling

```
You: Schedule a 1-hour meeting called Team Sync tomorrow at 10am
Assistant: Event "Team Sync" created on 2026-04-09 at 10:00.
           Link: https://calendar.google.com/event?eid=...

You: Book a 30-minute standup at 9am this Friday
Assistant: Event "standup" created on 2026-04-11 at 09:00.
           Link: https://calendar.google.com/event?eid=...

You: Set up a 45-min call with raj@example.com on Monday at 3pm
Assistant: Event created and raj@example.com has been invited.
           Link: https://calendar.google.com/event?eid=...
```

### Task 3 — Conflict Detection

```
You: Schedule a meeting called Old Meeting on 2024-01-15 at 10am
Assistant: The requested time (2024-01-15 10:00) is in the past.
           Please provide a future date and time.

You: Book a 30-minute Design Review tomorrow at 2:30pm
     [when "Team Sync" already occupies 2:00-3:00pm]
Assistant: Conflict detected. The slot 14:30-15:00 overlaps with
           "Team Sync" (14:00-15:00). Please choose a different time.
```

### Task 4 — Smart Suggestions

```
You: Schedule a 1-hour Strategy Call tomorrow at 10am
     [when that slot is already blocked]

[Agent] Calling tool 'create_event'       <- detects conflict
[Agent] Calling tool 'analyse_booking_patterns'
[Agent] Calling tool 'find_free_slots'    <- on requested day
[Agent] Calling tool 'find_free_slots'    <- on lightest day
Assistant: That slot is taken. Here are 3 alternatives for you:

  1. Tomorrow at 14:00 — free 2-hour gap in the afternoon
  2. Wednesday at 09:00 — Wednesday is your lightest day historically
  3. Thursday at 11:00 — consistent free window in your past patterns

### Bonus — Calendar Insights

```
You: Which days am I free this week?
Assistant: Days with no meetings:
  - Monday, 2026-04-13
  - Thursday, 2026-04-16

You: How many hours of meetings do I have this week?
Assistant: You have 3h 45m of meetings this week.

You: What was my busiest day this month?
Assistant: Your busiest day was Wednesday, 2026-04-08 with 4 meetings.
```

---

## Tool Reference

| Tool | Task | Description |
|------|------|-------------|
| `create_event` | 2, 3 | Creates a Google Calendar event. Includes past-date guard and overlap check before calling the API. |
| `get_calendar_events` | 3 | Fetches all events on a given date. Used by the agent to check for conflicts before scheduling. |
| `find_free_slots` | 4 | Scans working hours (09:00-18:00) and returns every gap large enough for the requested meeting. |
| `analyse_booking_patterns` | 4 | Looks at the last 30 days to find busiest days, lightest days, preferred hours, and average meeting duration. |
| `query_calendar_insights` | Bonus | Answers open-ended questions — free days, total hours, busiest day, event listings. |

---

## Task Coverage

| Task | Marks | What is Implemented |
|------|-------|---------------------|
| **Task 1 - Setup** | 10 | OAuth 2.0 copy-paste flow, token.json caching, Calendar ID verified on startup |
| **Task 2 - Trivial Creation** | 30 | create_event tool, LLM extracts structured args, event appears in Google Calendar, confirmation link returned |
| **Task 3 - Conflict Detection** | 25 | Past-date guard, overlap check using A_start < B_end AND A_end > B_start, multi-step agent loop with full ToolMessage history |
| **Task 4 - Smart Suggestions** | 35 | analyse_booking_patterns + find_free_slots called automatically on conflict, 2-3 ranked alternatives with reasons |
| **Bonus - Calendar Insights** | 20 | query_calendar_insights handles free days, total hours, busiest day, general event listing |

---

## Known Issues and Fixes

**Access blocked: App has not completed Google verification**
Your Gmail was not added as a test user. Go to APIs & Services -> OAuth consent screen -> Test users -> Add Users.

**Google Calendar API has not been used in this project (403)**
Enable the API at: https://console.developers.google.com/apis/api/calendar-json.googleapis.com/overview

**Your API key was reported as leaked**
Your Gemini key was exposed publicly. Generate a new key at https://aistudio.google.com/app/apikey and update .env.

**Quota exceeded / 429 error**
You hit the free tier limit (20 req/day for gemini-2.5-flash). Switch to `gemini-1.5-flash` in agent.py (1500 req/day free).

**Tomorrow resolves to a past date**
Ensure agent.py uses build_system_prompt() (not a static SYSTEM_PROMPT string) so today's real date is injected at runtime.

**Author identity unknown (git error)**
```bash
git config --global user.email "you@example.com"
git config --global user.name "Your Name"
```

---

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
