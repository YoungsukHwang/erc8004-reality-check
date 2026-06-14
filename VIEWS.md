# Per-view guide

A reader's manual for the dashboard. Every section answers the same three
questions:

1. **What the view shows** — the actual widgets on the page.
2. **How it's computed** — which SQL function in `app/queries.py` produced
   the numbers and what the partition cut / filters are.
3. **How to read it** — what each row or metric is evidence for, and what
   it isn't.

All counts are over Identity Registered events on Ethereum mainnet with
`block_timestamp >= 2026-01-28`. The registry contracts are
`0x8004a169fb…` (Identity) and `0x8004baa17c…` (Reputation). Validation
Registry has no mainnet address yet.

---

## Tab 1 — The Real Numbers

### What it shows
Two rows of metrics that walk the same set of agents from "claimed to be
something" to "did something verifiable on chain":

- **Identity side**: Registered → Has on-chain card → Functional (has a
  service endpoint) → Claims x402 payment support.
- **Reality side**: Has any feedback → Rated *and* claims x402 → Passes
  the gist Sybil bar (`unique_clients ≥ 3`) → Owner actually received
  USDC.

Below the funnel: a daily bar chart of Registered events, a cumulative
area chart, and a raw-counts expander.

### How it's computed
- Funnel left columns: `q_funnel()` — single roll-up over
  `decoded` (Identity Registered + inline JSON decode) and
  `reputation_base` (NewFeedback signature filter).
- "Rated AND claims x402": `q_rated_x402_count()` — inner join of
  Identity decoded cards and Reputation event agents, restricted to
  `x402Support = true`.
- "Received USDC": `q_x402_claim_vs_reality()` — joins the x402-true
  owner list against `token_transfers` filtered on USDC
  (`0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48`).
- Daily counts: `q1_adoption_daily()`.

### How to read it
Each metric's delta line is the share of the total Registered events
(34,566). The funnel is **monotone** — each stage is a strict subset of
the previous one's universe in spirit, even though the two rows describe
different attributes of the same agent population. The "Received USDC"
column is the only stage that goes beyond self-report — every other
field could be set to anything by the registrant.

---

## Tab 2 — Who's Behind It

### What it shows
- Six headline metrics: Total Registered, Distinct owners, Average agents
  per owner, Top 1 / 10 / 20 owner share.
- A collapsible drill-down on the #1 wallet listing every raw count from
  `q_owner_deep_dive()` (registrations, uri scheme breakdown, card
  decoding, x402 flag, services, nftOrigin, feedback presence, first
  and last registration timestamp).
- A 20-row owner table with first/last seen, plus a bar chart of their
  registration counts.
- External URI host breakdown: the host portion of every `http(s)://`
  agent_uri grouped, with `n_owners` per host. `n_owners = 1` is the
  signal that one wallet runs many cards under one domain.
- `registeredVia` self-declared platform breakdown (only inline-JSON
  cards expose this field).

### How it's computed
- `q_owner_concentration()` — single row with `n_owners`, `n_total`,
  `top1`, `top10`, `top20`, `top100` derived by ranking all owners.
- `q_owner_top(limit)` — top N owners with registration counts and the
  timestamp range of their activity.
- `q_owner_deep_dive(owner_address)` — every raw count above for one
  specific owner.
- `q_external_uri_hosts(limit)` — regex-extracts the host portion of
  `http(s)://` URIs and groups by host + counts distinct owners per
  host.
- `q_registered_via(limit)` — `JSON_VALUE($.registeredVia)` on inline
  cards.

### How to read it
The deep-dive expander on the #1 wallet shows raw counts and nothing
else. Read them as evidence; the dashboard does not draw a conclusion
for you. A host with `n_owners = 1` is the bot-farm signature — one
wallet operating many cards under one domain — but a host with high
`n_owners` (`ag0.xyz`) is a multi-tenant platform, a different shape
of phenomenon.

---

## Tab 3 — What Agents Actually Do

### What it shows
- Five KPIs: Registered, Has inline JSON card, Functional, Claims x402,
  Has nftOrigin.
- `agent_class` 6-bucket priority classification (no_uri → external_uri →
  test_spam → functional → nft_wrapper → other_card) with both agent
  and owner counts.
- agent_uri scheme breakdown (`none`, `inline_base64`, `https`,
  `plain_json`, `ipfs`, `http`, `raw_xml_svg`, `inline_json_other`,
  `other_text`).
- x402 claim vs reality: distinct x402=true owners, owners that
  received any ERC-20, owners that received USDC, with a caption
  pointing out the bot-farm `registeredVia=null` concentration.
- Top `services[].name` (OASF / web / custom / MCP / A2A / ENS / …).
- Top OASF skills, flattened from `services[].skills[]`.
- `registeredVia` self-declared platforms.

### How it's computed
- `q_headline_kpis()` — single roll-up.
- `q_agent_class_counts()` — `CASE WHEN` priority chain over
  decoded cards.
- `q_uri_scheme_breakdown()` — explicit `STARTS_WITH` rules covering
  every observed prefix; the totals must sum to 34,566.
- `q_x402_support()` — `LOWER(COALESCE($.x402Support, $.x402support))`
  grouped. The two spellings are disjoint per card, verified.
- `q_x402_claim_vs_reality()` — same query as Tab 1's "Received USDC"
  stage.
- `q_top_service_names(limit)` and `q_top_skills(limit)` — `UNNEST` on
  `services[]` and `services[].skills[]`.

### How to read it
`plain_json` (2,164) cards look like a second on-chain card pool but
are mostly Twitter-style user profiles (`{name, bio, type:"user"}`)
piggybacking on the registry — not ERC-8004 agents. We do not absorb
them into the rest of the counts. The x402 reality KPIs are the
strongest piece on this tab: the claim/reality gap is two orders of
magnitude.

---

## Tab 4 — Reputation, Real or Fake

### What it shows
- Reputation overall (Sybil-bar-agnostic): total NewFeedback events,
  distinct agents rated, distinct reviewers, distinct feedbackURI
  hashes, perfect-100 score count.
- Reviewer-count distribution bucketed as `1_reviewer`, `2_reviewers`,
  `3_to_4_reviewers`, `5_to_9_reviewers`, `10_plus_reviewers` — shows
  the long tail the Sybil bar discards.
- Q3 leaderboard: agents passing `unique_clients ≥ 3`, ranked by
  `avg_score` then `unique_clients`.
- Q4 client dominance: clients sorted by feedbacks given, with a
  `uri_diversity_ratio = distinct_feedback_uris / feedbacks_given`
  progress bar.
- Q4b feedbackURI hash collisions: hashes that recur, with their
  distinct-client and distinct-agent counts.
- Drill-down expanders:
  - Score > 100 outliers — two rows where the `fixedDecimals` field in
    `data` produced a 10× / 100× rendered score.
  - Clients whose entire feedback history is `score = 100`.

### How it's computed
- `q_reputation_summary()`, `q_reviewer_count_distribution()`,
  `q_score_distribution()` — straight aggregates on
  `reputation_base`.
- `q3_leaderboard(min_unique_clients, limit)` — `GROUP BY agent_id
  HAVING COUNT(DISTINCT client) >= 3`.
- `q4_client_dominance(limit)` — direct read from the Reputation logs
  (no CTE) so the SQL stays close to the handoff doc's reference
  version.
- `q4_feedback_uri_collisions(limit)` — `GROUP BY feedback_uri_hash
  HAVING COUNT(*) > 1`.

### How to read it
Q3 is the gist's standard filter — the "leaderboard the rest of the
world uses." Q4 and Q4b are the second-pass exposure: low
`uri_diversity_ratio` means the same client sent the same feedback URI
across many agents; high distinct-client counts on a single URI hash
means the *source* of the feedback was reused, even though the
on-chain signers were different. The two together are the picture the
Sybil bar can't render.

---

## Tab 5 — Trustworthy + Payable

### What it shows
The intersection that the GCP prize statement asks for: agents that
pass the Sybil bar **and** clear a minimum reputation score **and**
self-report x402 support. Each row is then enriched with the owner's
on-chain ERC-20 / USDC activity from `token_transfers`. Wallets that
received USDC float to the top.

Sliders let the user adjust the two filter parameters
(`min_unique_clients`, `min_avg_score`).

### How it's computed
`q_trustworthy_payable(min_unique_clients, min_avg_score)`:

1. Aggregate `reputation_base` by `agent_id` with the two `HAVING`
   filters.
2. Inner-join against decoded Identity cards where
   `x402Support = true`.
3. Left-join the result against `token_transfers` (partition cut
   matched, `event_type = 'ERC-20'`, `to_address IN candidate.owner`),
   counting transfers and summing USDC quantities.
4. Order by `(has_usdc DESC, avg_score DESC, unique_clients DESC)`.

### How to read it
This is the most narrowly-defined view in the dashboard. Each row is a
specific agent that survives every public filter you might reasonably
apply. With the default sliders (`3 / 80`) the answer is small enough
to read by eye. The dollar column on the right is the only field that
can't be set by the agent itself — it's the strongest single signal.

---

## Tab 6 — Find Agents

### What it shows
A natural-language search box at the top, with the same parsed filters
exposed as editable widgets below. The user can either let Gemini map
their request to filter parameters, or fill the structured filters in
manually.

Available filters: `agent_id`, `owner`, `name contains`,
`description contains`, `min unique reviewers`, `min avg score`,
`x402 only`, `has services`. Each ends up as a clause in the same
`q_agent_search()` SQL.

### How it's computed
- `app/nl_search.py` calls Vertex AI Gemini
  (`gemini-2.5-flash`) with one function-calling tool spec
  (`filter_agents`). The model is forced (`mode="ANY"`,
  `allowed_function_names=["filter_agents"]`) to emit exactly one
  function call. We parse its `args` into a dict.
- `q_agent_search(**filter_dict)` builds a `WHERE` clause from the
  non-null entries and a `HAVING` clause for the reputation
  aggregates, then groups by agent and orders by score and reviewer
  count.

Authentication is implicit: locally via Application Default
Credentials (`gcloud auth application-default login`); on Cloud Run via
the attached service account. No API key, no secret file. The SA needs
`roles/aiplatform.user` (granted in the deploy steps).

### How to read it
Treat the parsed-filters success banner as a transcript of what Gemini
heard. If it picked filters you didn't intend, edit the structured
widgets below and click "Search" again — that bypasses Gemini entirely
and runs the SQL directly.

---

## Tab 7 — Cheat Sheet

### What it shows
Every headline number from every other tab in three rows: the
eight-stage funnel, owner concentration, top external hosts, then the
reputation-side counts (events, distinct URI hashes, 1-reviewer
agents, perfect-100 feedbacks, USDC actually paid). Ends with a
one-line pitch summary built from the same numbers.

### How it's computed
No new SQL — it reuses cached results from `q_funnel()`,
`q_rated_x402_count()`, `q_x402_claim_vs_reality()`,
`q_owner_concentration()`, `q_external_uri_hosts(5)`,
`q_reputation_summary()`, `q_score_distribution()`,
`q_reviewer_count_distribution()`. Because of `@st.cache_data`, the
tab loads instantly after the others have been visited.

### How to read it
This is the booth-pitch tab. Open it last (or first, if you want the
audience to see the picture before the explanation). Every cell is a
shortcut to one of the deeper views.

---

## What we do NOT do (deliberately)

- **No risk model**: the pitch is observation and exposure, not
  scoring. Every cell is a raw count or a documented ratio.
- **No off-chain fetches**: `https://` / `ipfs://` URIs are reported
  as a category and broken down by host, but never dereferenced.
- **No multi-chain**: the GCP track is about on-chain agent economy
  on mainnet, and that's where ERC-8004 actually lives.
- **No ValidationRegistry view**: there is no mainnet address yet
  (spec WIP). Acknowledged explicitly in the sidebar.

## Trust but verify

Run `python app/verify.py` from the repo root to cross-check every
headline number against an independent SQL path. Each section prints
the value, a second-path recomputation, and (for x402) a third
native-JSON `SAFE.BOOL(PARSE_JSON.x402Support)` check. Mismatches are
flagged inline.
