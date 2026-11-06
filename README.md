# ReplyKaro

An AI sales assistant for local businesses. It answers customers instantly from the business's own information, captures leads, books visits, and hands off to the team when needed.

One engine serves every business. A business is **data**, and an industry is a **template file**. The core code never names a business.

## Quick start

```bash
uv sync                                    # install all workspace packages
cp .env.example .env                       # then put your ANTHROPIC_API_KEY in .env
uv run replykaro-load examples/*.toml      # load the example businesses
uv run uvicorn web.application.routes:app --reload
```

- Test chat: http://localhost:8000/chat/raam-mg (or `/chat/demo-clinic`)
- API docs: http://localhost:8000/docs
- Tests: `uv run pytest` (they use a fake AI client, so no API key or cost)

## Project structure

```
replykaro/
├── pyproject.toml                  # uv workspace root
├── examples/                       # business data files (one per business)
│   ├── raam-mg.toml                #   first pilot: car dealership
│   └── demo-clinic.toml            #   fictional clinic, shows a second industry
├── src/
│   ├── core.utils/core/utils/      # no dependencies on other packages
│   │   ├── config.py               #   settings from env / .env
│   │   ├── constants.py            #   channels, roles, statuses, lead stages
│   │   ├── money.py                #   "₹7.98 Lakh" ⇄ numbers
│   │   └── text.py                 #   keyword tokens for search
│   ├── core.db/core/db/            # database only, no business logic
│   │   ├── models/                 #   tenant.py, conversation.py, lead.py, usage.py
│   │   ├── session.py              #   engine, sessions, init_db
│   │   └── statements.py           #   stmt_* SQL statement builders
│   ├── core.business/core/business/  # business-agnostic domain logic
│   │   ├── spec.py                 #   BusinessSpec: one format for any business + import
│   │   ├── verticals/              #   industry templates: generic / automotive / clinic .toml
│   │   ├── knowledge.py            #   knowledge-base search and formatting
│   │   ├── conversations.py        #   start/find chats, messages, hand-off
│   │   ├── leads.py                #   create/update leads
│   │   └── cli.py                  #   `replykaro-load` command
│   ├── core.ai/core/ai/            # the AI layer
│   │   ├── client.py               #   Claude client + cost per call
│   │   ├── prompt.py               #   builds the system prompt from the 3 layers below
│   │   ├── prompt_templates/       #   sales_assistant.txt (the core rules, editable text)
│   │   ├── tools.py                #   tool schemas → calls into core.business
│   │   ├── guardrails.py           #   flags replies with prices not in the knowledge base
│   │   └── agent.py                #   handle_message(): the entry point for every channel
│   └── web.application/web/application/  # HTTP layer only
│       ├── routes.py               #   FastAPI app, wires the routers
│       ├── common.py               #   shared dependencies: session, tenant, AI client
│       ├── api/inputs.py           #   request bodies
│       ├── api/types.py            #   response shapes
│       ├── api/app/                #   chat, business, conversations, leads, usage
│       └── static/chat.html        #   test chat page
└── tests/
```

**Dependency direction** (each layer only imports the ones to its left):
`core.utils → core.db → core.business → core.ai → web.application`

## How the assistant knows each business

The system prompt is built from three layers:

1. **Core rules** (`core/ai/prompt_templates/sales_assistant.txt`) are the same for everyone: be accurate, keep replies short, match the customer's language, save leads, hand off when needed.
2. **Industry rules** (`core/business/verticals/<vertical>.toml`) set what to ask, what to book, and industry cautions. A dealership books a *test drive* and quotes *ex-showroom* prices; a clinic books an *appointment* and never diagnoses.
3. **Business details** come from that business's profile and knowledge base: products, prices, FAQs, offers, timings, locations and the owner's own rules.

## Adding things

| To add… | Do this | Code change? |
|---|---|---|
| A business | Write `examples/<name>.toml` and run `replykaro-load`, or `POST /api/businesses` with the same fields as JSON | No |
| An industry | Drop `src/core.business/core/business/verticals/<name>.toml` | No |
| Change prices/FAQs | `PUT /api/<slug>/kb/<id>` or edit the file and reload | No |
| A channel (Telegram, WhatsApp) | A new adapter that calls `core.ai.agent.handle_message` | Adapter only |

`tests/test_structure.py` fails if a business or industry name appears in core code.

## API (current)

| Method | Path | What it does |
|---|---|---|
| POST | `/api/businesses` | Create/update a business from a full spec |
| GET | `/api/businesses/verticals` | Available industry templates |
| POST | `/api/{slug}/chat` | Customer message → assistant reply |
| GET/PUT | `/api/{slug}/profile` | Business profile |
| GET/POST/PUT/DELETE | `/api/{slug}/kb[/{id}]` | Knowledge base |
| GET | `/api/{slug}/leads` | Captured leads |
| GET | `/api/{slug}/conversations[/{id}]` | Inbox and chat history |
| POST | `/api/{slug}/conversations/{id}/reply` | Team member replies (takes over from the bot) |
| POST | `/api/{slug}/conversations/{id}/release` | Hand the chat back to the bot |
| GET | `/api/{slug}/usage` | AI calls, tokens and cost |

⚠️ The API has **no authentication yet**, so run it locally only. Owner login is the next task (Phase 0.5 in `PLAN.md`).
