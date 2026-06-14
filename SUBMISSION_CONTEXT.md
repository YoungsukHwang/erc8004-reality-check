# Submission handoff — paste this into a fresh Claude chat

Everything Claude needs to help finish the ETHGlobal NY 2026 submission
form for **ERC 8004 Reality Check**.

---

## 1. What the project is

A BigQuery + Streamlit dashboard that decodes the Ethereum mainnet
ERC-8004 Identity and Reputation registries straight from raw events and
shows the gap between what agents claim and what the chain confirms.
Built for the **GCP "Best On-Chain Agent Economy Application"** track
($5,000). Also angling for the **ENS "Integrate ENS" pool** ($6,000
split) via owner reverse-resolution.

**Repo**: <https://github.com/YoungsukHwang/erc8004-reality-check>
**Cloud Run URL**: `https://erc8004-reality-check-<hash>-uc.a.run.app`
**Hackathon**: ETHGlobal New York 2026, June 13-14.

---

## 2. Validated numbers (cross-checked twice via `app/verify.py`)

| Metric | Value | Source |
|---|---:|---|
| Registered events | 34,569 | Identity Registered signature, partition cut from 2026-01-28 |
| Has inline JSON card | 9,520 | `data:application/json;base64,…` |
| Functional (has service endpoint) | 224 | `services[]` array non-empty |
| Claims x402 support | 4,645 | `x402Support` or `x402support` = true |
| Rated AND claims x402 | 216 | inner-join Identity decoded × Reputation |
| Trustworthy + Payable shortlist | 6 | Sybil ≥ 3 + avg_score ≥ 80 + x402 = true |
| **Of those, owner actually received USDC** | **2** | Surf ($1,594.91), Ethy AI ($13.45) — the chain's true final stage |
| Has any feedback | 1,652 | Distinct agent_id in NewFeedback events |
| Passes Sybil bar (≥ 3 reviewers) | 105 | `HAVING COUNT(DISTINCT client) >= 3` |
| Owner received USDC | 32 | `token_transfers` JOIN restricted to USDC + x402 owners |
| Total USDC received | $320,156 | 372 transfers aggregated |
| Distinct owners (registry) | 8,147 | |
| Top owner registrations | 9,967 | wallet `0xd5d6d96…`, every agent_uri empty |
| Top 20 owner share | 55% | 18,890 of 34,569 |
| External host `api.normies.art` | 1,171 / 1 owner | bot-farm fingerprint |
| Distinct feedbackURI hashes | 183 | for 3,173 feedback events (≈17× reuse) |
| Feedback with perfect score (100) | 1,022 | 32% of all scored feedbacks |
| 1-reviewer agents (Sybil bar left tail) | 1,472 | 89% of rated agents |
| Notable wash hash `0xc5d246…` | 386 hits / 301 clients / 39 agents | coordinated Sybil campaign |
| `plain_json` non-ERC-8004 cards | 2,164 (2,157 are Twitter-style `type:"user"`) | piggyback on registry |

### ENS layer

- Top 3 registrants `0xd5d6d96…`, `0xde152afb…`, `0x5f297b81…`: **no ENS** set.
- Trustworthy + Payable shortlist:
  - Surf (agent 13683) → owner `kevinlilili.eth`, $1,594.91 USDC
  - Ethy AI (agent 9380) → owner `ethyagent.eth`, $13.45 USDC
  - Jeff Zyfai (agent 9750) → owner `jeffceo.eth`
- Pattern: the registry's biggest registrants are anonymous; the actual
  payable agents disproportionately belong to ENS-named wallets.

---

## 3. The seven dashboard views

1. **The Real Numbers** — strict 5-stage funnel (Registered →
   Has card → Claims x402 → Rated AND x402 → Trustworthy+Payable),
   plus a parallel "Activity & settlement" row (feedback, Sybil pass,
   endpoint, USDC, USDC dollars). Below: daily/cumulative registration
   charts.
2. **Who's Behind It** — owner Pareto + top-20 table with ENS column +
   drill-down on the #1 wallet's raw counts (9,967 empty registrations)
   + external URI host breakdown (bot-farm fingerprint via `n_owners=1`).
3. **What Agents Actually Do** — agent_class classification, URI scheme
   breakdown (incl. the plain_json piggyback discovery), x402 claim vs
   `token_transfers` reality, service.name protocol distribution,
   top OASF skills, registeredVia platforms.
4. **Reputation, Real or Fake** — overall reputation counts and
   reviewer-count distribution; Q3 leaderboard; Q4 client dominance
   with `uri_diversity_ratio`; Q4b feedbackURI hash collisions;
   drill-down expanders for score>100 outliers and perfect-100-only
   clients.
5. **Trustworthy + Payable** — 6-row shortlist with ENS column,
   sliders for `min_unique_clients` and `min_avg_score`.
6. **Find Agents** — Vertex AI Gemini natural-language search
   (`gemini-2.5-flash` with one tool_use spec) plus the same filters
   exposed as structured widgets. No API key — same SA as BigQuery.
7. **Cheat Sheet** — every headline number on one page.

---

## 4. Tech stack

- **Data**: BigQuery, public dataset
  `bigquery-public-data.goog_blockchain_ethereum_mainnet_us`, partition
  cut `block_timestamp >= 2026-01-28`. Tables: `logs`, `token_transfers`.
- **Frontend**: Streamlit + `streamlit-option-menu` (top nav) + altair
  (chart fallback).
- **Hosting**: Google Cloud Run (`gcloud run deploy --source=.`),
  Artifact Registry, Cloud Build.
- **NL search**: Vertex AI Gemini (`google-genai` SDK with
  `vertexai=True`, model `gemini-2.5-flash`, tool_use mode `"ANY"`).
- **ENS**: `web3.py` 7.x ENS reverse lookup over public RPC
  (`ethereum-rpc.publicnode.com`).
- **Auth**: one service account
  (`erc8004-reality-check@…iam.gserviceaccount.com`) with
  `bigquery.dataViewer`, `bigquery.jobUser`, `aiplatform.user`.
  No API keys anywhere.
- **Language**: Python 3.12.

### Files

```
app/
  app.py         Streamlit entry, option-menu nav, per-view dispatcher
  bq.py          BigQuery client + cached query helper + shared CTEs
  queries.py     Every SQL function used by the dashboard
  ens_utils.py   Cached ENS reverse lookup
  nl_search.py   Vertex AI Gemini tool_use NL parser
  verify.py      Standalone cross-check of every headline number
  validate.py    Quick step-by-step JSON sanity checks
  peek_cards.py  Raw card inspector
Dockerfile
requirements.txt
README.md
VIEWS.md          per-tab reading guide
DEMO.md           90-second + 30-second video scripts
```

---

## 5. Contracts decoded

| Registry | Address | Status |
|---|---|---|
| Identity | `0x8004a169fb4a3325136eb29fa0ceb6d2e539a432` | active mainnet |
| Reputation | `0x8004baa17c55a88189ae136b182e5fda19de9b63` | active mainnet |
| Validation | (no mainnet address yet) | spec WIP — noted in sidebar |

Event signatures:

- Registered: `0xca52e62c367d81bb2e328eb795f7c7ba24afb478408a26c0e201d155c449bc4a`
- NewFeedback: `0x6a4a61743519c9d648a14e6493f47dbe3ff1aa29e7785c96c8326a205e58febc`

Topic layout differs between the two — Identity has `topics[2] = owner`
(20 bytes); Reputation has `topics[2] = client`, `topics[3] =
feedbackURI hash`. The hash is the field we use for wash detection.

---

## 6. Drafts of every submission-form field

### Project details

- **Name**: ERC 8004 Reality Check
- **Category**: Data/Analytics
- **Emoji**: 🔎 (or 🎯)
- **Demo link**: the Cloud Run URL above
- **Short description** (≤100 chars):
  > What's actually inside the ERC-8004 registry — decoded from raw on-chain bytes via BigQuery.
- **Description** (≥280 chars):
  > ERC 8004 Reality Check decodes the on-chain Identity, Reputation, and
  > (where it exists) Validation registries straight from BigQuery's public
  > Ethereum dataset, then exposes the gap between what agents claim and
  > what the chain confirms. The dashboard walks from 34,569 raw
  > registrations down to the six agents that survive every filter
  > (reputation ≥ 3 unique reviewers, score ≥ 80, x402 claim, real USDC
  > settlement). Stops along the way: owner concentration (the top wallet
  > registered 9,967 empty agents), agent-class classification, x402 claim
  > vs token_transfers reality, reputation wash detection via feedbackURI
  > hash collisions, and a natural-language search powered by Vertex AI
  > Gemini. ENS reverse resolution adds a human-identity layer on top of
  > every owner column — the wallets running the registry's biggest farms
  > are anonymous, while the few actually-payable agents are owned by
  > ENS-named identities like kevinlilili.eth and ethyagent.eth.
- **How it's made** (≥280 chars):
  > One Streamlit frontend over a handful of BigQuery queries against
  > bigquery-public-data.goog_blockchain_ethereum_mainnet_us.logs and
  > .token_transfers. Every query carries a partition cut
  > (block_timestamp >= 2026-01-28), keeping per-page scans inside the
  > 1 TB / month free tier. Identity and Reputation event topics are
  > decoded inline: CONCAT('0x', SUBSTR(topics[2], 27)) for addresses,
  > SAFE_CONVERT_BYTES_TO_STRING(FROM_HEX(...)) for the ABI-encoded
  > agent_uri string, SAFE.FROM_BASE64 for inline
  > data:application/json;base64,... cards. x402 claim vs reality is a
  > token_transfers JOIN restricted to ERC-20 and USDC. Natural-language
  > search calls Vertex AI Gemini (gemini-2.5-flash) with one tool_use
  > spec mapping user text to a structured filter dict — no API key, the
  > Cloud Run service account authenticates BigQuery, Vertex AI, and the
  > attached identity all at once. ENS reverse lookup uses web3.py
  > against a public RPC. Hosted on Cloud Run with a one-line
  > `gcloud run deploy --source=.` redeploy cycle.
- **GitHub Repositories**: `YoungsukHwang/erc8004-reality-check`

### Tech stack form

- Ethereum dev tools: `web3.py`
- Blockchain networks: Ethereum (mainnet)
- Programming languages: Python, SQL
- Web frameworks: Streamlit
- Databases: Google BigQuery
- Design tools: (leave blank)
- Other technologies: `google-genai`, `google-cloud-bigquery`,
  `streamlit-option-menu`, `altair`, `pandas`
- AI tools used:
  > Claude Code throughout — SQL decoding (offset/length ABI string
  > parsing for agent_uri, FROM_BASE64 inline JSON), Streamlit layout,
  > Vertex AI Gemini tool_use integration, ENS reverse-lookup module,
  > and the verify.py cross-check script. Vertex AI Gemini powers the
  > in-app natural-language search.

### Select prizes (max 3)

1. **GCP — Best On-Chain Agent Economy Application** ($5,000)
   Why we qualify: BigQuery is the data backbone (every number is one
   query against `bigquery-public-data.goog_blockchain_ethereum_mainnet_us`),
   we use the canonical Ethereum Foundation Identity + Reputation
   registry addresses, Validation gap is noted explicitly, and the
   frontend is a Streamlit dashboard hosted on Cloud Run with Vertex AI
   Gemini for NL search.
2. **ENS — Integrate ENS pool** ($6,000 split)
   Why we qualify: `app/ens_utils.py` is ENS-specific code. ENS reverse
   resolution adds a working identity layer that surfaces in the
   Owners tab and the Trustworthy+Payable shortlist, with real,
   live-resolved names (kevinlilili.eth, ethyagent.eth, jeffceo.eth).
   Not hard-coded.
3. (leave open — only add a 3rd if it actually fits)

### Video

- 2-4 minute video required. Our `DEMO.md` 90-second cut is a
  starting script; the 2-minute version simply pauses on each tab
  ~5 extra seconds. Light theme, 1280×800, QuickTime → MP4.
- Voice-over follows DEMO.md word-for-word — no music.
- Demo URL appears in last frame as text overlay.

### Future

Multi-select. Open to ESP / Compound Grants / Ethereum Support Program
introductions.

### Final checklist

- ✅ Project starts from scratch (built during ETHGlobal NY 2026)
- ✅ Uses GitHub with frequent commits
- ✅ Open source
- ✅ Not submitted to another hackathon
- ✅ Abides by event rules
- Final checkbox ("work built entirely during hackathon"): check
  manually when ready.

---

## 7. Headline soundbites (for video voice-over or copy)

- *"34,569 registrations. 105 pass the standard Sybil bar. 32 wallets
  ever received a USDC payment — that's 0.09 percent."*
- *"The top wallet alone registered 9,967 agents. Every single one has
  an empty agent_uri. None of the top three registrants set an ENS
  name."*
- *"3,173 feedback events share only 183 distinct feedbackURI hashes —
  seventeen times reuse on average. One hash appears 386 times from
  301 different wallets targeting only 39 agents."*
- *"After every filter, the entire registry collapses to six agents.
  Only two of those owners ever received a USDC transfer — Surf
  ($1,594.91) and Ethy AI ($13.45). Both are owned by ENS-named
  wallets: kevinlilili.eth and ethyagent.eth."*
- *"BigQuery, Cloud Run, Vertex AI, ENS. One service account does all
  the auth — no API key anywhere."*

---

## 8. Known caveats to mention (or avoid) in the writeup

- "Has on-chain card" (9,520) and "Has feedback" (1,652) **overlap but
  are not nested** — 1,164 rated agents have no card (top wallet's
  phantom-feedback case). Tab 1's funnel only contains genuine
  strict-subset stages.
- USDC reception is **owner-level**, not agent-level — does not slot
  into the agent-level funnel. Lives in the parallel "Activity &
  settlement" row.
- Validation Registry has **no mainnet address yet**. Acknowledged
  explicitly in the sidebar — not a missing feature.
- `plain_json` cards (2,164) look like a second ERC-8004 card pool but
  are mostly Twitter-style user profiles (`{name, bio, type:"user"}`)
  piggybacking on the registry. We deliberately do **not** absorb them
  into the rest of the counts.
- Two `score > 100` outliers in the data are `fixedDecimals` decoding
  artifacts; we flag them in a drill-down rather than silently
  filtering.

---

## 9. What to ask Claude in the new chat

Concrete asks that Claude can help with once you paste this:

1. "Tighten this short description to under 90 chars."
2. "Draft a 60-second video voice-over from the soundbites above."
3. "Suggest a logo concept (512×512) using only emoji + monospace text."
4. "Write the alt-text for each of the 4 screenshots."
5. "Generate a tweet-thread version of the headline soundbites."
6. "List 3-5 ways the project could continue past the hackathon for
   the Future section."
