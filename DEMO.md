# Demo video script

Three cuts. The **2-minute** version is the submission video. The
**90-second** booth walk-through is a backup; the **30-second** booth
pitch is what you say while a judge is still walking up.

All cuts assume the dashboard is already open on the first tab and the
live URL is the Cloud Run deployment
(`https://erc8004-reality-check-…-uc.a.run.app`).

---

## 2-minute cut (ETHGlobal submission — required 2-4 min)

The framing for this cut is **"observatory, not scanner."** Existing
ERC-8004 sites count registrations; this is the internal-analytics
dashboard that opens the box. Detailed numbers live in the dashboard —
the voice-over names what each tab is *for*.

**[0:00 – 0:22]  Open on the brand row at the top of the page**

> "Hi, I'm Young — I've been working on data science at American
> Express, and I built ERC 8004 Reality Check to deep-dive into the
> ERC-8004 usage. 8004 Reality Check opens the box. This is the first
> line of analytics dashboard created from Google's Web3 ERC-8004
> dataset. It provides not only top-line numbers and a leaderboard,
> but also in-depth analytics that highlight how ERC-8004 is actually
> being used."

---

**[0:22 – 0:32]  Tab 1 — The Real Numbers**

> "The first tab is the funnel. Other scanners stop at the top line —
> 'thirty-four thousand agents registered.'"

*(Land on the funnel row so the viewer sees the strict chain narrow
left-to-right, ending on the success callout.)*

---

**[0:32 – 0:52]  Click "Who's Behind It"**

> "The second tab answers: who registered all of this? You'll see the
> Pareto distribution on owners, the external hosts that are run by a
> single wallet. The ENS column right next to the address turns
> anonymous hex into real identities wherever the owner has set one."

*(Open the top-wallet drill-down briefly so the raw-counts table is on
screen.)*

---

**[0:52 – 1:07]  Click "What Agents Actually Do"**

> "Third tab opens the agent cards. You'll find what shape the
> registrations actually take — empty entries, NFT wrappers, test
> spam, functional agents with real endpoints."

---

**[1:07 – 1:30]  Click "Reputation, Real or Fake"**

> "Fourth tab is reputation. The standard filter that every other
> scanner uses is 'three or more unique reviewers.' You'll find that
> filter here, but you'll also find what it misses — feedback URI
> hash collisions that catch coordinated wash campaigns where one
> piece of feedback was reused across hundreds of agents by hundreds
> of wallets. The drill-down expanders surface the specific clients
> that only ever hand out perfect scores."

---

**[1:30 – 1:50]  Click "Trustworthy + Payable"**

> "Fifth tab is the answer. It intersects every filter — Sybil bar,
> minimum reputation, x402 claim, and real on-chain USDC settlement —
> and shows you the agents that survive. The ENS column on the left
> is the credibility signal: the registry's largest anonymous
> registrants have no ENS at all, while the agents that actually got
> paid are owned by ENS-named wallets."

*(Highlight the `owner_ens` column.)*

---

**[1:50 – 2:10]  Click "Find Agents", type the example**

> "Sixth tab is search — both a free-text box powered by Vertex AI
> Gemini, and the same filters exposed as widgets so you can drive
> the search by hand. Watch — 'agents with at least 5 reviews and
> high reputation.' Gemini parses the sentence into structured
> filters and BigQuery returns the result. No API key, no secret
> file — the same service account that reads BigQuery calls Gemini
> and resolves ENS."

*(Press Enter, let the results render.)*

---

**[2:10 – 2:25]  Close**

> "Under the hood, it's BigQuery for the data, Cloud Run for the app,
> Vertex AI Gemini for natural-language search, and ENS for identity
> resolution — all running through one GCP service account. No API
> keys, no secret files. It's open source, and the repo and live demo
> are linked below."

---

## 90-second cut (booth + backup)

Same framing as the 2-minute cut, tighter. Use this if the submission
upload fails or a judge asks for the short version.

**[0:00 – 0:12]  Open**

> "I'm Young, working on data science at AmEx. ERC 8004 Reality Check
> opens the box on the agent registry — the first analytics dashboard
> built straight from Google's Web3 ERC-8004 dataset. Not a top-line
> counter; in-depth analytics on how the registry is actually used."

---

**[0:12 – 0:22]  Tab 1 — Funnel**

> "First tab is the funnel. Every step is a strict subset of the one
> above it, all the way down to the wallets that actually received a
> USDC payment. The chain confirming the claim."

---

**[0:22 – 0:35]  Tab 2 — Owners**

> "Second tab: who registered all this. Owner Pareto, bot-farm hosts
> (one wallet running many cards under one domain), and a drill-down
> on the single biggest registrant. The ENS column right next to the
> address turns anonymous wallets into real identities where the
> owner has set one."

---

**[0:35 – 0:48]  Tab 3 — Agents**

> "Third tab opens the agent cards. What shape are the registrations?
> Empty, NFT wrapper, test spam, functional with a real endpoint —
> all classified. The headline here is x402 claim versus reality:
> a `token_transfers` JOIN that checks who actually accepts payment."

---

**[0:48 – 1:01]  Tab 4 — Reputation**

> "Fourth tab is reputation. The standard Sybil filter that every
> other scanner uses is here, but you'll also find what it misses —
> feedbackURI hash collisions that catch coordinated wash campaigns,
> and a drill-down on clients that only ever hand out perfect scores."

---

**[1:01 – 1:15]  Tab 5 — Trustworthy + Payable**

> "Fifth tab is the answer. Intersect every filter — Sybil bar, score,
> x402 claim, real USDC — and the registry collapses to a handful of
> agents. The ENS column shows the credibility signal: the largest
> anonymous registrants have no ENS, the real ones do."

---

**[1:15 – 1:25]  Tab 6 — Search**

> "Sixth tab is search — free text powered by Vertex AI Gemini, same
> service account as BigQuery and ENS. No API key, no secrets."

---

**[1:25 – 1:30]  Close**

> "BigQuery, Cloud Run, Vertex AI Gemini, ENS. Open source. Repo and
> live demo linked."

---

## 30-second booth cut

For walking judges through the framing in one breath.

> "I'm Young, working on data science at AmEx. ERC 8004 Reality Check
> opens the box on the registry — the first in-depth analytics
> dashboard built straight from Google's Web3 ERC-8004 dataset. Six
> tabs that walk you from who registered, to what they actually are,
> to which ones got paid, to a Gemini-powered natural-language search.
> Same service account does BigQuery, Cloud Run, Vertex AI, and ENS —
> no API key anywhere. Open source, live demo linked."

---

## Final checklist (run through 30 min before recording)

1. **Cloud Run redeploy** — make sure the live URL serves the latest
   commit. From the repo root:
   ```bash
   gcloud run deploy erc8004-reality-check \
     --source=. --region=us-central1 --project="$PROJECT" \
     --service-account="$NEW_SA_EMAIL" --allow-unauthenticated \
     --memory=1Gi --cpu=1 --min-instances=0 --max-instances=2
   ```
   Wait for "Service URL" in the output before recording.
2. **Open the live URL in a clean browser window** — incognito if your
   normal window has extensions or login prompts that might pop in.
3. **Pre-warm the cache** — click through every tab once so subsequent
   loads are instant; the recording shouldn't include a 5-second
   spinner.
4. **Theme = Light** (Streamlit `⋮` → Settings → Light) — the red
   primary color reads cleanly against white.
5. **Window size = 1280×800** so the seven nav links sit on a single
   row and screenshot proportions match GitHub previews.
6. **Mic check** — 10-second test, listen back, adjust input gain.
7. **Close any apps that play notification sounds** (Slack, Mail,
   iMessage). Set Mac to Do Not Disturb.
8. **Practice once silently** (mouse moves only), then once with audio,
   then record the take. Three takes is plenty.

## Recording tips

- **macOS QuickTime** → File → New Screen Recording → Options → mic on.
- Run **at 1280×800** so the tabs all fit on a single row.
- **Light mode** in Streamlit ("⋮" → Settings → Theme → Light) — the
  red active-link pops more cleanly on white.
- Practice the cut **once** silent (mouse moves only), then **once**
  with audio, then **record**. Three takes is plenty.
- Keep the cursor still during voice-overs — moving it pulls the
  viewer's eye away from the metric you're reading.
- Export as MP4 H.264. Drop into the ETHGlobal submission form.

## What to point at on each tab

| Tab | First metric / element to highlight |
|---|---|
| The Real Numbers | The five funnel KPIs (left to right) |
| Who's Behind It | "Top 1 owner share" + the drill-down expander |
| What Agents Actually Do | The three x402 reality columns |
| Reputation, Real or Fake | Q4b URI collision table — row `0xc5d246…` |
| Trustworthy + Payable | The `owner_ens` column |
| Find Agents | The text box → result table |
| Cheat Sheet | The headline funnel row again, then the bottom one-liner |
