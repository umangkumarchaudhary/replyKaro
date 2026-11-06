# ReplyKaro — AI Sales Assistant for Local Businesses
*(working name — easy to change)*

> Every message answered in seconds, every lead captured, every follow-up sent —
> on WhatsApp, Instagram, website and Telegram — in Hindi, English or Hinglish.

---

## LEVEL 0 — The Big Picture

### Problem
- Local businesses (dealerships, clinics, gyms, coaching, salons, real estate) get 20–200 messages/day.
- Replies take hours → customers go to the competitor who replied first.
- Follow-ups depend on a salesperson's memory → most leads die silently.
- Owners have zero visibility: "How many enquiries came this week? Who followed up?"
- Enterprise tools (Salesforce, Freshworks bots) are too complex and expensive for them.

### Solution
A plug-and-play AI assistant that:
1. **Answers instantly** from the business's own info (no model training — see §2.2).
2. **Qualifies** the lead (budget, need, timeline) naturally in conversation.
3. **Books** the action (test drive / appointment / trial / site visit).
4. **Follows up** automatically until the lead converts or says no.
5. **Hands over** to a human when needed, with the full context.
6. **Shows the owner** everything on a simple dashboard + daily WhatsApp summary.

### Who pays
| Segment | Why they buy | First target? |
|---|---|---|
| Car / bike dealerships | High-value leads, heavy WhatsApp usage, you know this domain | ✅ **Yes — beachhead** |
| Clinics / dentists | Appointment booking, repetitive FAQs | Phase 4 |
| Coaching / gyms | Fee/batch questions, trial bookings | Phase 4 |
| Real estate | Site visits, high lead value | Phase 4 |

**Strategy:** win dealerships first (Raam MG = first pilot), then make the "business profile" generic so other verticals are just templates.

### North-star metric
**Leads converted to bookings per business per month.** Owners pay for bookings, not for chat.

---

## LEVEL 1 — Product Pillars

| # | Pillar | What it means |
|---|---|---|
| P1 | **Brain** | The AI agent: understands the message, answers from business knowledge, uses tools (book, save lead, hand off). |
| P2 | **Knowledge** | Each business's profile: products, prices, offers, timings, FAQs, rules. Built from PDF / website / form. |
| P3 | **Channels** | Adapters: Web widget, Telegram, WhatsApp Cloud API, Instagram DM. Same brain behind all. |
| P4 | **Leads & Follow-ups** | Lead record, stages, scoring, automated follow-up sequences, reminders. |
| P5 | **Owner Dashboard** | Inbox (live chats + human takeover), leads pipeline, bookings calendar, analytics, settings. |
| P6 | **Platform** | Multi-tenant accounts, auth, billing, usage limits, logs, admin panel. |
| P7 | **Trust & Compliance** | Meta policy, opt-in, DPDP Act (India), guardrails so the bot never lies about price/stock. |

---

## LEVEL 2 — Architecture

```
                    ┌──────────────── Channels (P3) ────────────────┐
 Customer ──►  Web Widget │ Telegram │ WhatsApp Cloud API │ Instagram
                    └───────────────────────┬───────────────────────┘
                                            │ normalized message
                                            ▼
                               ┌──────────────────────────┐
                               │  Message Gateway (API)   │  FastAPI
                               │  - dedupe, tenant lookup │
                               │  - enqueue               │
                               └────────────┬─────────────┘
                                            ▼  Redis queue (RQ / arq)
                               ┌──────────────────────────┐
                               │   Agent Worker  (P1)     │
                               │  1. load conversation    │
                               │  2. load business profile│◄── Knowledge (P2)
                               │  3. retrieve relevant    │    Postgres + pgvector
                               │     products/FAQs (RAG)  │
                               │  4. call Claude w/ tools │──► Claude API
                               │  5. execute tools        │
                               │  6. send reply           │
                               └────────────┬─────────────┘
                                            ▼
                     ┌──────────────────────────────────────────┐
                     │ Postgres: tenants, contacts, conversations,│
                     │ messages, leads, bookings, followups, kb   │
                     └──────────────────────────────────────────┘
                                            ▲
             Scheduler (APScheduler) ───────┤ follow-ups, reminders, daily summary
                                            │
                     Owner Dashboard (Next.js) ◄── WebSocket / Supabase realtime
```

### Tech stack (matches what you already use)
| Layer | Choice | Why |
|---|---|---|
| Backend API | **FastAPI** (Python 3.11+) | Your EPICCRM/AeroRisk stack |
| Queue/workers | **Redis + RQ** (or arq) | Already used in EPICCRM |
| DB | **Postgres (Supabase)** + **pgvector** | One DB for data + embeddings |
| Frontend | **Next.js + Tailwind + shadcn/ui** | Your raam-mg / EPICCRM stack |
| Realtime | Supabase realtime or WebSocket | Live inbox |
| AI | **Claude Haiku 5.5** for most customer chats (~₹0.5/conversation), **Sonnet 5.5** only for hard cases / PDF ingestion (~₹5/conversation) | Keeps AI cost < 10% of subscription |
| Embeddings | Any embedding API / local model | For RAG on big catalogs |
| Hosting | Render / Railway (API+workers), Vercel or Cloudflare (dashboard) | Cheap to start |
| Payments | Razorpay | India subscriptions |

---

## LEVEL 2.0.1 — Code Structure
See `README.md` → *Project structure*. Rule: the core never names a business or industry;
businesses are data (`examples/*.toml`, DB), industries are `core/business/verticals/*.toml`.
Layering: `core.utils → core.db → core.business → core.ai → web.application`.

---

## LEVEL 2.1 — Data Model (core tables)

```
tenants        (id, name, vertical, plan, timezone, language, created_at)
users          (id, tenant_id, name, phone, email, role[owner|agent])
channels       (id, tenant_id, type[web|telegram|whatsapp|instagram], config_json, status)
business_profile (tenant_id, about, address, hours_json, rules_json, tone, booking_type)
kb_items       (id, tenant_id, type[product|faq|offer|doc_chunk], title, content, price, metadata_json, embedding)
contacts       (id, tenant_id, name, phone, channel_ids_json, language, opted_in, created_at)
conversations  (id, tenant_id, contact_id, channel_id, status[bot|human|closed], last_message_at)
messages       (id, conversation_id, role[customer|bot|human], content, media_url, tool_calls_json, created_at)
leads          (id, tenant_id, contact_id, interest, budget, timeline, score, stage, source, assigned_to)
bookings       (id, tenant_id, lead_id, type, slot_at, status[booked|confirmed|done|no_show|cancelled])
followups      (id, lead_id, due_at, step, template, status)
usage_events   (id, tenant_id, type, tokens_in, tokens_out, cost, created_at)
```

---

## LEVEL 2.2 — How the AI "knows" each business (no training)

1. **Onboarding ingests knowledge** → stored as `kb_items`
   - Form (products, prices, hours, FAQs)
   - PDF brochure / price list → extracted by Claude into structured items
   - Website URL → scraped → extracted
   - Excel/CSV catalog upload
2. **At reply time** the worker builds the prompt:
   - System prompt = role + business profile + rules + tone + today's date/offers
   - If catalog small (< ~100 items) → include all
   - If large → vector search top-k relevant items
   - Last N messages of conversation + lead summary
3. **Tools the agent can call**
   | Tool | Does |
   |---|---|
   | `save_lead(name, phone, interest, budget, timeline)` | Create/update lead |
   | `check_slots(date)` / `book(slot, type)` | Bookings |
   | `search_catalog(query)` | RAG lookup |
   | `handoff_to_human(reason)` | Flags conversation, notifies owner |
   | `send_media(item_id)` | Brochure PDF / car image |
4. **Guardrails**
   - Only quote prices that exist in `kb_items`; otherwise "let me confirm with the team" + handoff.
   - Never promise discounts not in `offers`.
   - Detect anger/complaint → instant handoff.
   - Language mirroring (reply in customer's language/script).
5. **Quality loop**
   - Owner can 👍/👎 any bot reply and write the correct answer → becomes a new FAQ item.
   - Eval set of 50+ real conversations per vertical; run before every prompt change.

---

## LEVEL 2.3 — Compliance & Meta (P7)

- **WhatsApp Cloud API**: free test number for development (5 recipients). Production needs Business verification + a dedicated number per business.
- **Meta 2026 policy**: general-purpose AI chatbots are not allowed; *business-specific* assistants (support, sales, booking) are allowed. Keep the bot scoped to the business.
- **24-hour window**: free-form replies only within 24h of the customer's last message; after that, only pre-approved **template messages** (follow-ups must use templates).
- **Opt-in**: record consent for follow-ups; honour "STOP".
- **DPDP Act (India)**: privacy notice, data deletion on request, data stored securely, per-tenant isolation.
- Become a **Tech Provider** with Meta later so businesses can connect their number via Embedded Signup (one-click).

---

## LEVEL 3 — Phased Roadmap

| Phase | Name | Goal | Est. time |
|---|---|---|---|
| **0** | Foundation | Repo, infra, DB, auth skeleton | 2–3 days |
| **1** | Brain MVP | Bot answers from a business profile in a web chat | 1 week |
| **2** | Leads + Telegram | Lead capture, bookings, dashboard v1, Telegram channel | 1–2 weeks |
| **3** | WhatsApp + Pilot | WhatsApp Cloud API, follow-ups, **Raam MG pilot** | 2 weeks |
| **4** | Self-serve SaaS | Onboarding wizard, PDF/URL ingestion, multi-tenant, billing | 3 weeks |
| **5** | Growth | Instagram, analytics, verticals, Meta Tech Provider, voice notes | ongoing |

---

## LEVEL 4 — Tasks per Phase

### Phase 0 — Foundation
- [x] 0.1 uv workspace: `src/core.utils`, `src/core.db`, `src/core.business`, `src/core.ai`, `src/web.application` (dashboard/widget folders come in Phase 2)
- [ ] 0.2 Docker compose: Postgres (+pgvector), Redis
- [ ] 0.3 Alembic migrations for core tables
- [x] 0.4 Config/env handling (`core.utils.config`), logging (loguru) — [ ] error tracking (Sentry) still to do
- [ ] 0.5 Auth (Supabase auth or JWT) — owner login
- [x] 0.6 Claude API client wrapper with token/cost logging → `usage_events`
- [ ] 0.7 CI: lint + tests on push

**Done when:** `docker compose up` runs API + DB + Redis, health check green.

### Phase 1 — Brain MVP
- [x] 1.1 `business_profile` + `kb_items` CRUD API
- [x] 1.2 Business spec format + `replykaro-load` + `POST /api/businesses`; examples: Raam MG (pilot), demo clinic
- [x] 1.3 Prompt builder: core rules template + vertical (industry) template + business profile/kb
- [x] 1.4 Agent loop with Claude tool use (`search_catalog`, `save_lead`, `handoff_to_human`) — tested with a fake client; needs a first real-API run
- [x] 1.5 Conversation + message storage
- [x] 1.6 Simple web chat page (test UI) at `/chat/{slug}`
- [x] 1.7 Guardrails: price-only-from-kb (flags unknown prices), language mirroring + handoff triggers (prompt rules)
- [ ] 1.8 Eval harness: 30 sample customer messages → check answers (hinglish, price, booking)

**Done when:** you chat in Hinglish about a car, get correct prices, and a lead row appears.

### Phase 2 — Leads, Bookings, Dashboard v1, Telegram
- [ ] 2.1 Channel adapter interface (`receive()`, `send()`, `normalize()`)
- [ ] 2.2 Web widget adapter (embeddable `<script>` snippet)
- [ ] 2.3 Telegram adapter (BotFather token, webhook)
- [ ] 2.4 Redis queue: gateway enqueues, worker processes (handles bursts, retries)
- [ ] 2.5 Booking tools: `check_slots`, `book` + slot config in profile
- [ ] 2.6 Lead scoring (Haiku extracts budget/timeline/intent → score Hot/Warm/Cold)
- [ ] 2.7 Dashboard: Login, **Inbox** (live chats, bot/human toggle, reply as human)
- [ ] 2.8 Dashboard: **Leads** table + kanban by stage
- [ ] 2.9 Dashboard: **Bookings** calendar
- [ ] 2.10 Dashboard: **Knowledge** editor (products/FAQs) + 👍/👎 → FAQ loop
- [ ] 2.11 Owner notifications (Telegram/email) on hot lead or handoff

**Done when:** someone chats on Telegram, books a test drive, owner sees it live and can take over.

### Phase 3 — WhatsApp + Follow-ups + Pilot
- [ ] 3.1 Meta developer app + Business portfolio + test number
- [ ] 3.2 WhatsApp Cloud API adapter (webhook verify, signature check, text/media/buttons)
- [ ] 3.3 Interactive messages: quick-reply buttons, list (choose model / choose slot)
- [ ] 3.4 Message templates: follow-up, booking reminder, booking confirmation (submit for approval)
- [ ] 3.5 Follow-up engine: sequences (e.g. +2h, +1 day, +3 days, +7 days), stop on reply/booking/STOP
- [ ] 3.6 24h-window logic: free-form vs template switch
- [ ] 3.7 Booking reminders (day before + 2h before) & no-show follow-up
- [ ] 3.8 Daily owner summary on WhatsApp ("Yesterday: 34 chats, 12 leads, 5 test drives")
- [ ] 3.9 Voice-note support: transcribe → treat as text
- [ ] 3.10 **Pilot at Raam MG**: 2 weeks, measure response time, leads, bookings vs before
- [ ] 3.11 Collect testimonial + numbers → case study

**Done when:** real customers of Raam MG talk to the bot and bookings are measured.

### Phase 4 — Self-serve SaaS
- [ ] 4.1 Multi-tenant hardening (row-level security, tenant_id everywhere, tests)
- [ ] 4.2 Signup + onboarding wizard: business type → template → upload PDF/URL → preview chat → go live
- [ ] 4.3 Ingestion pipeline: PDF/URL/Excel → Claude extraction → review screen → `kb_items`
- [ ] 4.4 pgvector RAG for big catalogs
- [ ] 4.5 Vertical templates: generic, automotive, clinic ✅ — gym, coaching, real estate still to add
- [ ] 4.6 Team members & lead assignment (round-robin)
- [ ] 4.7 Plans & billing (Razorpay subscriptions), usage limits per plan
- [ ] 4.8 Admin panel (all tenants, usage, costs, errors)
- [ ] 4.9 Landing page with live demo ("message this number")
- [ ] 4.10 Privacy policy, terms, data deletion flow (DPDP)

**Done when:** a stranger signs up, uploads a brochure, and is live in < 15 minutes.

### Phase 5 — Growth
- [ ] 5.1 Instagram DM adapter
- [ ] 5.2 Meta Tech Provider + Embedded Signup (businesses connect their own WhatsApp number in 1 click)
- [ ] 5.3 Analytics: response time, conversion funnel, top questions, lost-lead reasons
- [ ] 5.4 CRM integrations / export (Google Sheets, your EPICCRM, webhooks)
- [ ] 5.5 Broadcast campaigns (offers to opted-in contacts, template-based)
- [ ] 5.6 Meta lead-ads → instant WhatsApp first contact (reuse `meta_leads_sync` learnings)
- [ ] 5.7 Mobile-friendly owner app (PWA)
- [ ] 5.8 Voice calls AI (later)

---

## Business Model (draft)
| Plan | For | Includes | Price idea (₹/month) |
|---|---|---|---|
| Starter | Single shop | 1 channel, 500 conversations | ₹1,499 |
| Growth | Dealership / clinic | All channels, 2,000 convos, follow-ups, 3 users | ₹4,999 |
| Pro | Multi-branch | Unlimited users, analytics, integrations | ₹12,999+ |

WhatsApp conversation charges from Meta are passed through at cost.

**AI cost check (Nov 2026 prices):** a typical 8-message chat costs ~₹0.5 on Haiku 5.5 vs ~₹5 on Sonnet 5.5.
Starter (500 chats) = ~₹250 on Haiku ✅ vs ~₹2,500 on Sonnet ❌ (loss). → Default to Haiku, escalate to Sonnet only when needed, and enforce per-plan conversation limits.
Validate pricing with the first 5 pilot customers before fixing it.

---

## Success Metrics
- First reply time: **< 10 seconds** (vs hours today)
- % chats where lead details captured: **> 60%**
- Chat → booking conversion: track vs baseline
- Handoff rate: **< 20%** (bot handles most)
- Wrong-answer rate on eval set: **< 2%**
- AI cost per conversation: track; keep well under plan price

---

## Risks & Mitigations
| Risk | Mitigation |
|---|---|
| Bot gives wrong price/info | Prices only from kb; handoff when unsure; owner feedback loop; evals |
| Meta policy / account issues | Official Cloud API only; business-scoped bot; templates for follow-ups; web + Telegram as backup channels |
| AI cost too high | Haiku for side tasks, prompt caching, short history + lead summary |
| Owners don't update info | Weekly "is this still correct?" WhatsApp nudge; price-list re-upload in 1 click |
| Competition (Interakt, AiSensy, Wati) | They are broadcast/inbox tools; we win on **AI that sells + books + follows up**, Hinglish, dealership depth |
| Customer data privacy | Tenant isolation, encryption, DPDP-compliant deletion |

---

## Immediate Next Step
Start **Phase 0 → Phase 1**: scaffold the repo and get the Raam MG bot answering in a web chat.
