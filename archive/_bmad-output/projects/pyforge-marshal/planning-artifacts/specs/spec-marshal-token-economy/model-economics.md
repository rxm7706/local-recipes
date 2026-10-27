# Model economics — the declared price catalog and the provider ladder

Companion to `SPEC.md` (spec: marshal-token-economy). Operator-supplied catalog snapshot,
**2026-08-30**. This is the seed data for CAP-11's declared price table and CAP-12's
cross-provider tier routing. It is a **dated, hand-refreshed snapshot** — prices are
declared policy data, never fetched live (air-gap constraint). When a provider reprices,
the operator updates this file and the rendered policy; nothing in marshal talks to a
billing API.

Scope: coding-agent text models only. The operator's full catalog also lists Gemini
audio/TTS/video/music/robotics/embedding models — all out of this spec's scope (non-goal).

## Subscription pools (flat-rate channels before metered API)

| Pool | Terms | Marginal-token implication |
|---|---|---|
| Cursor Ultra | $200/mo; generous included usage on first-party + third-party pools, then on-demand at model API rate | Included allowance is the cheapest marginal token in the estate — prefer until exhausted |
| Anthropic Claude Max (20×) | Max plan at the 20×-Pro usage tier, covering Claude-CLI sessions | The largest flat pool in the estate for claude-harness runs — first preference for that harness; its size is why the claude harness stays the drain default even with cheaper metered rivals |
| GitHub Copilot Pro | $100/yr — **downgrade pending** (operator clarification 2026-08-30). At Pro: premium-request quota can drive agent sessions via the copilot harness; post-downgrade: inline/chat only (~2,000 completions/mo, Haiku 4.5 / GPT-5 mini) | **Transitional** — may serve as a secondary agent pool while Pro lasts, but routing must not depend on it persisting; degrade to "not a drain workhorse" when the downgrade lands |
| GitHub Pro | $48/yr | Repo/platform features, not a model pool — irrelevant to routing |
| Google Gemini API | Metered only (no flat pool) | Economy-class rates make it the cheap metered fallback |

## Price table (per 1M tokens, USD)

**Cursor first-party pool** (no routing fees):

| Model | In | Out | Cache read | cr/in ratio |
|---|---:|---:|---:|---:|
| Composer 2.5 | 0.50 | 2.50 | 0.20 | 0.40 |
| Composer 2.5 Fast | 3.00 | 15.00 | 0.50 | 0.17 |
| Grok 4.6 | 2.00 | 6.00 | 0.50 | 0.25 |
| Grok 4.6 Fast | 4.00 | 12.00 | 1.00 | 0.25 |
| Grok 4.5 | 2.00 | 6.00 | 0.50 | 0.25 |
| Grok 4.5 Fast | 4.00 | 18.00 | 1.00 | 0.25 |

**Anthropic** (direct API; 1M context, 128k out except Haiku 200k/64k):

| Model | In | Out | Cache read | Cache write | cr/in ratio |
|---|---:|---:|---:|---:|---:|
| Fable 5 | 10.00 | 50.00 | 1.00 | 12.50 | 0.10 |
| Opus 5 | 5.00 | 25.00 | 0.50 | 6.25 | 0.10 |
| Sonnet 5 | 2.00 | 10.00 | 0.20 | 2.50 | 0.10 |
| Haiku 4.5 | 1.00 | 5.00 | — | — | — |

**OpenAI via Cursor third-party pool:**

| Model | In | Out | Cache read | Cache write | cr/in ratio |
|---|---:|---:|---:|---:|---:|
| GPT-5.6 Sol | 4.00 | 20.00 | 0.40 | 5.00 | 0.10 |
| GPT-5.6 Terra | 2.00 | 12.00 | 0.20 | 2.50 | 0.10 |
| GPT-5.6 Luna | 0.20 | 1.20 | 0.02 | 0.25 | 0.10 |

**Google Gemini** (API; Cursor-pool rate noted where it differs):

| Model | Context | In | Out | Cache read | Note |
|---|---|---:|---:|---:|---|
| Gemini 3.1 Pro | 2M | 2.00 | 12.00 | 0.20 | Same rate in Cursor pool |
| Gemini 3.7 Flash | 1M | 0.75 | 3.75 | 0.075 | Cursor pool lists out at 3.50 |
| Gemini 3.1 Flash-Lite | 1M | 0.25 | 1.50 | — | |
| Gemini 2.5 Flash-Lite | 1M | 0.10 | 0.40 | — | Cheapest major-provider multimodal |

## The difficulty ladder maps onto a real price ladder

The tier vocabulary already in `marshal-policy.toml` (`heavy`/`medium`/`easy`, Story 6.1
fixture vocabulary) now has concrete cross-provider candidates. Input-rate spread across the
ladder is ~50× (0.10 → 10.00), output ~125× (0.40 → 50.00) — this is why feeding the tiering
mechanism matters more than any single compression layer.

| Difficulty | Class | Candidates | In $/1M |
|---|---|---|---:|
| easy | economy | Gemini 2.5/3.1 Flash-Lite, GPT-5.6 Luna, Composer 2.5, Haiku 4.5 | 0.10–1.00 |
| medium | standard | Sonnet 5, Gemini 3.1 Pro, GPT-5.6 Terra, Grok 4.6 | ~2.00 |
| heavy | frontier | Opus 5, GPT-5.6 Sol | 4.00–5.00 |
| (review ceiling) | flagship | Fable 5 — "strongest model where it pays" (review misses ship false-greens) | 10.00 |

## Cache-ratio observation (feeds CAP-11's per-provider weights)

Marshal's weighted tally uses a global `cache_read_weight = 0.1` (NFR-14). The catalog shows
that constant is **exactly right for Anthropic, OpenAI, and Gemini** (published cache-read =
10% of input across all three families) but **understates Cursor first-party models**
(Grok 0.25, Composer 0.40). CAP-11 therefore derives per-provider weights from the declared
catalog, with the global constant as fallback for undeclared providers. Anthropic cache
*write* is uniformly 1.25× input — relevant to the ladder's cache-churn accounting.

## Refresh discipline

- Snapshot date in the heading; update it when prices move.
- The rendered policy table is derived from this file by the operator (or a story's tooling),
  never by a network call.
- Dollar figures downstream (journals, `marshal status`, benchmark artifacts) are estimates
  from declared prices × observed token counts — advisory, never a gate, never reconciled
  live against provider billing dashboards.
