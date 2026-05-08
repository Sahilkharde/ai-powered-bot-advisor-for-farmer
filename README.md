# 🌱 KrishiMitra — Pomegranate Mandi Advisor Agent

> An AI agent that helps Indian pomegranate farmers decide **when** and **where** to sell their harvest, based on live mandi prices, trends, and arrivals data. Built for the [Damco "Build at Damco"](https://damcogroup.com/build-at-damco) challenge.

## The problem

I come from a farming family in Maharashtra. We have a pomegranate (`Bhagwa`) farm with around 1,000 trees. Every season my father agonizes over **when** to sell and **which mandi** to go to.

Pomegranate prices vary 10–30% across Maharashtra mandis on the same day. They also swing 20–40% week to week pre-harvest. Right now the decision is gut-feel + WhatsApp rumors + last week's neighbor's price. We have lost lakhs of rupees over the years selling at the wrong time or in the wrong mandi.

This is a real problem. I built this to solve it for my own family first.

## What it does

You chat with KrishiMitra in **English, Hindi, or Marathi** — over Telegram or via a CLI — and it tells you:

- ✅ Today's prices across the 6 main pomegranate mandis in Maharashtra
- ✅ The 14-day trend per mandi (rising / falling / flat, with %)
- ✅ Best mandi to sell at today, with the actual numbers
- ✅ A structured recommendation: `SELL_NOW` / `HOLD` / `SELL_PARTIAL` / `INSUFFICIENT_DATA`
- ✅ Honest confidence level (low / medium / high) — never overconfident

## Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                         DATA SOURCES                           │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  ┌──────────┐  │
│  │  agmarknet  │  │ Weather API │  │ Agri news│  │User profile│ │
│  │  (mandi $)  │  │  (supply)   │  │ (demand) │  │(mandis,stk)│ │
│  └──────┬──────┘  └──────┬──────┘  └────┬─────┘  └────┬─────┘  │
└─────────┼────────────────┼───────────────┼─────────────┼───────┘
          │                │               │             │
          ▼                ▼               ▼             ▼
┌────────────────────────────────────────────────────────────────┐
│              INGESTION + STORAGE                               │
│       (CSV today → SQLite/Snowflake in production)             │
└────────────────────────────┬───────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                    AGENT CORE (Langchain)                      │
│                                                                │
│  ┌──────────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────┐ │
│  │get_current_  │ │get_price_│ │compare_mandis│ │rag_context │ │
│  │   prices     │ │  trend   │ │              │ │ (planned)  │ │
│  └──────────────┘ └──────────┘ └──────────────┘ └────────────┘ │
│                              │                                 │
│                              ▼                                 │
│             ┌──────────────────────────────┐                   │
│             │      Decision LLM            │                   │
│             │  (Gemini 2.5 Flash, JSON     │                   │
│             │   structured output)         │                   │
│             └──────────────┬───────────────┘                   │
└────────────────────────────┼───────────────────────────────────┘
                             ▼
                  ┌─────────────────────┐
                  │   Telegram bot      │
                  │ (English/Hi/Marathi)│
                  └──────────┬──────────┘
                             ▼
                  ┌─────────────────────┐   
                  │   Father / family   │
                  └─────────────────────┘
```

The agent isn't a price lookup. It has **tools** (Langchain pattern), and a separate **decision LLM** that synthesizes tool outputs into a structured recommendation. That separation matters: the tool-calling agent does retrieval, the decision LLM does judgment.

## Tech stack

| Layer | Tool | Why |
|---|---|---|
| LLM | Gemini 2.0 Flash | Free tier, fast, supports tool calling + structured output |
| Agent framework | Langchain (`create_tool_calling_agent`) | Standard for tool-using agents |
| Structured output | Pydantic + Gemini's JSON mode | Forces the model to commit to a schema |
| Storage (MVP) | CSV + pandas | Demo-grade. Trivially swappable. |
| Storage (prod) | Snowflake / Postgres | Time-series price data |
| Bot | `python-telegram-bot` | Free, runs on father's phone, no install |
| Runtime | Python 3.10+ | Matches my day-to-day stack |

## How to run

### 1. Setup
```bash
git clone <your-repo-url>
cd mandi-agent
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

### 2. Get API keys (both free)
- **Gemini**: https://aistudio.google.com/app/apikey → Create API key → paste into `.env` as `GOOGLE_API_KEY`
- **Telegram bot**: Open Telegram → search `@BotFather` → `/newbot` → follow prompts → paste token into `.env` as `TELEGRAM_BOT_TOKEN`

### 3. Test the agent (CLI, no Telegram needed)
```bash
python main.py "Should I sell my pomegranates today?"
python main.py "Compare all mandis"
python main.py "Solapur cha trend kaay?"
```

### 4. Run the Telegram bot
```bash
python -m src.bot
```
Then message your bot from Telegram and ask it anything.

## Scope honesty: what's real, what's stubbed

I deliberately scoped this to ship a working agent end-to-end rather than half-build everything. Here's the honest breakdown:

| Component | Status | Notes |
|---|---|---|
| Langchain agent + tool calling | ✅ Real | Uses Gemini's function calling, fully working |
| Structured decision output | ✅ Real | Pydantic-validated `Recommendation` schema |
| Mandi price data | 🟡 Sample CSV | 30 days × 6 mandis × realistic noise + trend. Production = agmarknet scraper (see "tradeoffs"). |
| Trend analysis | ✅ Real | Computes % change over arbitrary windows |
| Telegram bot | ✅ Real | Multi-language, structured replies |
| Marathi/Hindi output | ✅ Real | Prompted in the system message + the structured schema includes a `reasoning_marathi` field |
| Voice (STT/TTS) | ❌ Not in MVP | Whisper + ElevenLabs would slot in cleanly; not built |
| Weather + news ingestion | ❌ Stubbed in design | Not in MVP code; described in architecture |
| Multi-user / auth | ❌ Single-user | Single Telegram bot for now |
| Memory of past decisions | ❌ Not in MVP | ChromaDB integration designed but not built |

## Tradeoffs I made (and would defend in the live round)

**1. Sample CSV instead of live agmarknet scraping.**
Agmarknet has a public price portal but no stable API. Scraping it works but is fragile (HTML changes break parsers). I shipped with a high-quality sample dataset so the agent demonstrably *works end-to-end* — and documented the scraping path in code. Real production would have a daily cron job + retry + fallback to last-known-good. With more time I'd build that scraper as a separate module — the rest of the agent doesn't change.

**2. Two separate LLM calls (tool agent + decision LLM) instead of one.**
A single LLM with both tools and structured output works in theory but mixes concerns. Splitting them means: tool agent is responsible for *retrieval* (gather facts), decision LLM is responsible for *judgment* (commit to a recommendation). It's also easier to swap in a smaller cheaper model for the retrieval step later. Cost: 2× LLM calls. Worth it.

**3. Gemini over OpenAI.**
Gemini 2.0 Flash has a generous free tier, native function calling, and works with Langchain. For a farmer-facing tool that needs to be cheap to run, this matters more than a marginal quality bump from GPT-4o.

**4. Telegram instead of WhatsApp or a custom mobile app.**
WhatsApp Business API has restrictions and isn't free. A custom mobile app is weeks of work. Telegram works on my father's phone instantly, supports Marathi keyboard, and `python-telegram-bot` is rock solid. Reach > polish for v1.

**5. Confidence levels instead of pretending to be certain.**
The decision LLM is *required* to emit `low / medium / high` confidence. With sparse data (one day of prices, no trend) it's prompted to say "INSUFFICIENT_DATA" rather than guess. A wrong recommendation at high confidence costs my family real money — I'd rather the agent admit it doesn't know.

## Failure modes (what breaks, and what I designed for)

This is the section I care most about. An agent that gives confident-but-wrong sell advice is worse than no agent at all.

**1. Stale or missing price data.**
- *What goes wrong:* If the agmarknet scraper hasn't run, the agent recommends based on yesterday's prices. Real markets move 5–10%/day pre-harvest.
- *Mitigation:* Tool returns the date of the data; system prompt instructs the agent to flag staleness. Decision schema's `confidence` field drops to `low` for stale data.
- *What's missing:* No automatic alert when scraper fails.

**2. Wrong recommendation costs real money.**
- *What goes wrong:* Agent says SELL today at Solapur, prices spike 8% tomorrow. Farmer loses ₹X per quintal.
- *Mitigation:* Recommendation always includes the *reasoning* and *numbers it saw*. Farmer sees "I'm recommending sell because Solapur is +5% above 30-day average and trend is flat" and can override. Agent is an advisor, not an autopilot.
- *Honest limitation:* No model can predict tomorrow's price reliably. The right framing is "given this data, here's the probabilistic best move" — not "sell now."

**3. Marathi nuance and agricultural slang.**
- *What goes wrong:* Farmer asks `डाळिंबाला आज काय भाव?` and Gemini's Marathi is competent but not native. Agricultural Marathi has terms like `बाजारभाव`, `आडत`, `दलाल` with specific meanings.
- *Mitigation:* Prompt includes explicit term mapping. Output schema has separate `reasoning_english` and `reasoning_marathi` fields so the farmer always has both.
- *What's missing:* No glossary of regional dialect terms; Western Maharashtra Marathi differs from Marathwada.

**4. Mandi access reality.**
- *What goes wrong:* Agent recommends Pune (+₹500/quintal) but my farm is in Solapur district. Transport cost eats the gain.
- *Mitigation:* Designed user-profile component (in architecture, not yet in code) that holds reachable mandis + transport cost per kilometer.
- *Status:* Not implemented in MVP.

**5. Over-confidence on thin signal.**
- *What goes wrong:* Three days of data + an LLM hallucinating a "trend" = bad sell signal.
- *Mitigation:* Trend tool refuses to compute on <2 data points. Decision schema requires honest confidence.
- *What's missing:* No statistical significance test. With more time I'd add a moving-average + std-dev gate.

**6. Off-season silence.**
- *What goes wrong:* Pomegranate is mostly traded Oct–Feb. May–Aug, prices barely move. Agent has nothing useful to say.
- *Mitigation:* Should pivot to other helpful tasks (storage planning, scheme awareness, next-season prep). Not built.

## What I'd build next (if this were a real product)

In rough priority order:
1. **Real agmarknet scraper** with cron + retries + last-known-good cache
2. **User profile** (reachable mandis, transport cost/km, current stock) — recommendations weighted by net realizable price, not gross mandi price
3. **Memory** — ChromaDB store of past decisions and outcomes; agent learns "when I sold at Solapur in May 2025 it was +6% in two weeks"
4. **Voice** — Whisper STT + Marathi TTS so my father can talk to it instead of typing
5. **Weather + news signals** — pre-monsoon weather affects supply; export demand affects price
6. **WhatsApp Business API** — Telegram works but WhatsApp is where farmers already are
7. **Multi-crop** — same architecture works for grapes, oranges, onions

## Repo layout

```
mandi-agent/
├── README.md                      ← you are here
├── requirements.txt
├── .env.example
├── .gitignore
├── main.py                        ← CLI test entry
├── data/
│   └── sample_mandi_prices.csv    ← 30 days × 6 mandis
└── src/
    ├── __init__.py
    ├── prompts.py                 ← system prompts (Marathi-aware)
    ├── tools.py                   ← Langchain tools over the price data
    ├── agent.py                   ← agent + decision LLM
    └── bot.py                     ← Telegram interface
```

## Author

**Sahil Kharde** — AIML Engineer, Bangalore
Built for the Damco "Build at Damco" challenge, May 2026.

The farm is real. The problem is real. The code is honest about what it is.
