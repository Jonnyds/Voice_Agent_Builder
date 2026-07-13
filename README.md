# Voice Agent Builder

Chat with an AI **builder** to create a voice AI assistant in plain English, then
**talk to that assistant live in your browser**. The assistant qualifies the lead and books a meeting.


---

## What it does

```
Describe an agent      ->   Builder generates a       ->   Talk to it live:
                            validated config               it qualifies you and books
```

1. You describe the agent you want ("call gym trial sign-ups and book a tour").
2. The builder turns that into a structured, validated config (name, opening line,
   qualifying questions, goal, and the instructions the voice agent follows).
3. You start a real voice call in the browser, talk to the agent, and it qualifies
   you and books — showing a `BOOKING` line with the structured booking data.

Everything runs in one interface. No phone number required.

---

## Project structure

```
app.py            Gradio single-page UI + the in-browser voice call (Vapi web SDK)
builder.py        The builder: LLM + tool-schema structured output + build/clarify/refuse
requirements.txt  Pinned dependencies
.env              Your keys (create locally from .env.example; not committed)
```

Deliberately small: the voice complexity (speech-to-text, the conversation, text-to-speech,
turn-taking) is handled by Vapi, and generation by the LLM. This code is the glue and the
judgment — the builder prompt, the output schema, safety routing, and the config->call
handoff.

---

## Setup (full instructions)

Follow these from a clean machine. Takes about 10 minutes, most of it creating accounts.

### 1. Prerequisites
- **Python 3.10 or newer.** Check with `python --version` (Windows) or `python3 --version` (Mac/Linux).
  If you don't have it, install from https://www.python.org/downloads/ and, on Windows, tick
  "Add Python to PATH" during install.
- A modern browser with a microphone (Chrome recommended).

### 2. Get the code
Clone the repository, then open a terminal **in the project folder** — the folder
that contains `app.py`:
```bash
git clone <your-repo-url>
cd <repo-folder>
```

### 3. Create a virtual environment (recommended)
This keeps the project's packages isolated from your system Python.

Windows (PowerShell):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Mac / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

You'll see `(.venv)` at the start of your prompt when it's active.

### 4. Install dependencies
```bash
pip install -r requirements.txt
```
This installs Gradio (the UI), the Anthropic SDK (the builder brain), and python-dotenv
(reads your `.env`).

### 5. Get your two API keys

**a) Anthropic API key (required — powers the builder)**
1. Go to https://console.anthropic.com and sign in.
2. Open **API Keys**, click **Create Key**, and copy it (starts with `sk-ant-`).

**b) Vapi PUBLIC key (required — powers the in-browser voice call)**
1. Go to https://dashboard.vapi.ai and sign in.
2. Open **API Keys**. You will see two keys — copy the one labelled **Public**
   (safe to use in a browser). Do NOT use the private key here.
3. In the Vapi dashboard, open **Provider Keys** and add an **Anthropic** provider key
   (your Anthropic key from step 5a is fine). The voice agent uses Claude via Vapi, so
   this must be set or the call will fail with a 400 error.

### 6. Create your .env file
Copy the example and fill in your keys:

Windows (PowerShell):
```powershell
Copy-Item .env.example .env
```
Mac / Linux:
```bash
cp .env.example .env
```

Then open `.env` in a text editor and set:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key
VAPI_PUBLIC_KEY=pk-your-vapi-public-key
```
(`VAPI_PUBLIC_KEY` is optional in the file — if you leave it blank you can paste the key
into the app's field instead. Setting it here just pre-fills that field.)

### 7. Run it
```bash
python app.py
```
Open the URL it prints — **http://127.0.0.1:7860** — in your browser.

### 8. Use it
1. **Build** an agent by typing a description in the left chat (see the examples below).
2. The generated agent appears on the right (name, opening line, questions, goal).
3. If it isn't pre-filled, paste your **Vapi public key** into the field.
4. Click **Start call**, and **allow microphone access** when the browser asks.
5. Talk to the agent. It asks its qualifying questions; when a lead qualifies and gives
   a time, it books and a green **BOOKING** line shows the structured data.
6. Click **End call** to hang up (the agent also ends the call itself after saying goodbye).

**Example build prompt to try:**
```
Build an outbound voice agent for a boutique gym called Ironline Fitness. It calls people
who signed up for a free trial. The agent's name is Alex. Qualify the lead one question at
a time: (1) are they 18 or older? if under 18, politely end without booking; (2) what is
their main fitness goal? (3) can they come in for a tour this week? If they qualify, book a
tour by asking their preferred day and time and their name, then confirm. Keep it warm and
concise.
```

---

## Configuration

All configuration is via `.env` — nothing sensitive is hardcoded.

| Variable            | Required | Used by            | Purpose                                                        |
|---------------------|----------|--------------------|----------------------------------------------------------------|
| `ANTHROPIC_API_KEY` | Yes      | `builder.py`       | The builder LLM that turns a description into a config.         |
| `VAPI_PUBLIC_KEY`   | Yes*     | browser voice call | Starts the in-browser Vapi call. *Can be typed into the UI instead of `.env`. |

The Vapi **public** key is browser-safe by design. The Anthropic key is used only
server-side (in Python) and never reaches the browser.

---

## Troubleshooting

- **`ANTHROPIC_API_KEY is not set`** — your `.env` is missing the key or the app was run
  from a different folder. Confirm `.env` sits next to `app.py` and holds a real key.
- **Voice call fails with a 400 / "start failed"** — your Vapi account is missing the
  Anthropic **provider key**. Add it in Vapi dashboard -> Provider Keys (step 5b).
- **Call connects but the agent can't hear you** — the browser blocked the microphone.
  Click the mic icon in the address bar and set it to Allow, then reload. (Serving over
  `http://127.0.0.1:7860` — as this app does — is a secure context, so mic access is allowed.)
- **"Enter your Vapi PUBLIC key first"** — paste the public key into the field (or set
  `VAPI_PUBLIC_KEY` in `.env`).
- **Gradio startup error / long traceback** — keep Gradio pinned to the version in
  `requirements.txt`; some other versions have a startup bug.

---

## Design decisions

**Builder = prompt + output schema, not a heavy agent framework.** The builder is a single LLM call. There's no branching, multi-node control flow, so LangGraph or an agent framework would be over-engineering.

**Structured output, not text parsing.** The builder uses Anthropic tool-calling with a forced tool whose schema *is* the config contract, so the API returns a validated object directly — no fragile JSON scraping and no separate validation step. The schema enforces the shape (required fields, question count, a minimum systemPrompt length).

**Safety routing (build / clarify / refuse).** Before building, the builder decides an action: refuse harmful or manipulative requests (including prompt-injection attempts hidden in the description), ask a clarifying question when the description is too vague, or build.

**Web call, not phone.** The demo uses a Vapi **web call** — a real voice conversation over the browser — so it needs no phone number, no telephony provider, and no per-call setup, and it works anywhere. The Vapi **public** key is a *publishable* key, designed to be used in client-side code (like a Stripe publishable key), so shipping it in the browser is expected and safe — the Anthropic key and any private Vapi key stay server-side. Note "publishable" does not mean "powerless": a public key can start web calls, so in production it should be rate-limited and domain-restricted in the Vapi dashboard to prevent abuse.

**Why Claude Sonnet.** Sonnet runs both the builder and the voice agent: it follows the multi-rule qualifying script reliably — in testing, other models drifted (skipped or reordered questions, booked unqualified leads), while Sonnet asked all questions in order, enforced disqualifiers, and respected booking constraints — and it's fast enough for real-time voice, where a heavier reasoning model would add latency for no conversational gain. The model is set via .env (BUILDER_MODEL / VOICE_MODEL), so it's swappable without code changes.

---

## How it works (the Python <-> JavaScript bridge)

```
[builder chat]  ->  builder.build_agent()  ->  validated config (gr.State)
                                                     |
                                       render_agent()  and  config_json()
                                                     |
                                     hidden config box (Textbox in the page)
                                                     |
   click "Start call"  ->  Gradio runs JS: startVapiCall(publicKey, config)
                                                     |
                              Vapi web SDK runs the mic call in the real page
                                                     |
                    transcript + BOOKING events  ->  appended to the call log
```

Python builds the agent (the schema enforces its shape); the browser (via Vapi's web SDK) runs the actual voice call. They meet at a hidden text box that carries the config from Python into the JavaScript when you press Start.

---

## Production path (not in this demo)

The **builder** half carries over and the same generated config drives production. The **calling** half is genuinely different, though. This demo runs the call client-side (browser mic, an inline assistant, the publishable key). Real outbound **phone** calls are server-side: you create a saved assistant and place calls via Vapi's `/call` endpoint using the **private** key and an imported phone number (free Vapi numbers are US-only; international requires importing a Twilio/provider number). Booking also moves from the in-browser display to a **webhook** that writes to a real calendar (Cal.com / Google Calendar). So config generation is identical; the telephony and booking layers change.

---

## Known limitation

The voice agent follows its instructions conversationally rather than reading the qualifying questions as a rigid script — it may occasionally reword or reorder a question. Using a strong instruction-following model (Claude Sonnet) for the voice agent keeps this tight, and
in testing it reliably asks all questions in order, enforces disqualifiers (e.g. under-18), and respects booking constraints (e.g. opening hours). Guaranteeing an exact script every
time would mean driving the turn-by-turn flow in code rather than trusting the model — a deliberate scoping choice left out of this demo.

Booking is captured and displayed (the `BOOKING` payload) rather than written to a live calendar, as noted in the production path above.