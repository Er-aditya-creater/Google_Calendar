# AI Meeting Scheduler — LangChain + Google Calendar

An AI agent that understands natural language scheduling requests, checks your
real Google Calendar for conflicts, creates events, and suggests smart
alternatives when a slot is blocked.

---

## Project Structure

```
meeting_scheduler/
├── credentials.json   ← downloaded from Google Cloud Console
├── token.json         ← auto-generated on first run (do NOT commit)
├── .env               ← API keys
├── tools.py           ← all LangChain tool definitions
├── agent.py           ← multi-step agentic loop
├── main.py            ← entry point / chat loop
└── README.md
```

---

## Step-by-Step Setup

### 1 — Clone / copy the project files

Place all four Python files (`tools.py`, `agent.py`, `main.py`) and this
`README.md` in a folder named `meeting_scheduler/`.

### 2 — Create a Python virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3 — Install dependencies

```bash
pip install \
  langchain \
  langchain-google-genai \
  google-auth \
  google-auth-oauthlib \
  google-api-python-client \
  python-dotenv
```

### 4 — Get a Gemini API key

1. Visit <https://aistudio.google.com/app/apikey>
2. Click **Create API Key**
3. Create a `.env` file in the project root:

```
GOOGLE_API_KEY=your_key_here
```

### 5 — Enable Google Calendar API & create OAuth credentials

1. Go to <https://console.cloud.google.com>
2. Create a new project (or select an existing one)
3. **APIs & Services → Library** → search **Google Calendar API** → Enable
4. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Desktop App**
   - Click **Create**, then **Download JSON**
5. Rename the downloaded file to `credentials.json` and place it in the project root

### 6 — Add yourself as a test user (IMPORTANT)

Because the app is in development mode, only whitelisted accounts can log in.

1. **APIs & Services → OAuth consent screen**
2. Scroll to **Test users → Add Users**
3. Enter your Gmail address → Save

### 7 — First-run authentication (copy-paste flow)

The first time you run the app it will:

1. Print an authorisation URL in the terminal
2. You open that URL in any browser
3. Log in with the Gmail address you whitelisted
4. Google shows you an authorisation code — copy it
5. Paste it back into the terminal prompt
6. `token.json` is created automatically; future runs skip this step

---

## Running the Agent

```bash
python main.py
```

You will see a confirmation that the agent connected to your calendar, then an
interactive prompt:

```
✓ Connected to calendar: your.email@gmail.com

You: Schedule a 1-hour meeting called Team Sync tomorrow at 10am
```

Type `help` to see example prompts. Type `exit` to quit.

---

## Example Interactions

| Input | Expected behaviour |
|---|---|
| `Schedule a 1-hour meeting called Team Sync tomorrow at 10am` | Event created, link returned |
| `Book a 30-minute standup at 9am this Friday` | Event created at the correct time |
| `Set up a 45-min call with raj@example.com on Monday at 3pm` | Event created with attendee invited |
| `Schedule a meeting at 2pm yesterday` | Rejected: past date |
| `Book a call on Friday at 2pm` (slot already taken) | Conflict detected + 2-3 alternatives suggested |
| `Which days am I free this week?` | Lists days with no meetings |
| `How many hours of meetings do I have this week?` | Returns total meeting hours |
| `What was my busiest day this month?` | Returns the day with most events |

---

## Feature Overview by Task

| Task | What is implemented |
|---|---|
| **Task 1 – Setup** | OAuth flow, `token.json` caching, Calendar ID verification |
| **Task 2 – Trivial Creation** | `create_event` tool, single LLM → tool call → confirmation |
| **Task 3 – Conflict Detection** | Past-date guard, overlap check `(A_start < B_end AND A_end > B_start)`, multi-step agent loop with `ToolMessage` history |
| **Task 4 – Smart Suggestions** | `analyse_booking_patterns`, `find_free_slots`, ranked alternatives with reasons in the system prompt workflow |
| **Bonus – Calendar Insights** | `query_calendar_insights` handles free days, busiest day, total meeting hours, and general event listing |

---

## Notes

- All times are handled in **Asia/Kolkata (IST, UTC+5:30)**. Change `TIMEZONE`
  in `tools.py` if you are in a different zone.
- The agent loop runs up to **8 iterations** per request (configurable via
  `MAX_ITERATIONS` in `agent.py`).
- `token.json` is sensitive — add it to `.gitignore`.
