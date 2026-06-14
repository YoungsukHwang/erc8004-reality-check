"""ERC-8004 Agent Explorer — Streamlit entry point.

Run with:
    streamlit run app/app.py
from /Users/YoungsukHwang/projects/ethglobal.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from bq import run_query
import queries as q
import nl_search


st.set_page_config(
    page_title="ERC 8004 Reality Check",
    page_icon="🔎",
    layout="wide",
)


# -----------------------------------------------------------------------------
# Sidebar — context
# -----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### ERC 8004 Reality Check")
    st.caption(
        "We index the noise. You see the signal.\n\n"
        "**Source:** `bigquery-public-data.goog_blockchain_ethereum_mainnet_us.logs`\n\n"
        "**Partition cut:** `block_timestamp >= 2026-01-28` (mainnet went live 2026-01-29)"
    )
    st.divider()
    st.markdown("**Contracts**")
    st.code(
        "IdentityRegistry   0x8004a169fb4a3325136eb29fa0ceb6d2e539a432\n"
        "ReputationRegistry 0x8004baa17c55a88189ae136b182e5fda19de9b63\n"
        "ValidationRegistry (no mainnet address — spec incomplete)",
        language="text",
    )


st.title("ERC 8004 Reality Check")
st.markdown(
    "Four scanners brag about big registration counts. "
    "We open the boxes to show what's inside."
)


tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "📊 Funnel",
    "👤 Owners",
    "🤖 Agents",
    "⭐ Reputation",
    "🎯 Trust + Pay",
    "🔍 Search",
    "📋 Summary",
])


# =============================================================================
# Tab 1 — The Real Numbers (Q1 Adoption + funnel)
# =============================================================================
with tab1:
    st.header("The Real Numbers")
    st.caption("Funnel: registered → has card → functional → rated → passes Sybil bar.")

    # ---- Funnel headline rows ----
    with st.spinner("Loading funnel..."):
        funnel = run_query(q.q_funnel()).iloc[0]
        rated_x402 = int(run_query(q.q_rated_x402_count()).iloc[0]["n_rated_x402"])
        usdc = run_query(q.q_x402_claim_vs_reality()).iloc[0]

    n_reg = int(funnel.n_registered)
    n_card = int(funnel.n_inline_json)
    n_rated = int(funnel.n_agents_rated)
    n_sybil = int(funnel.n_passes_sybil_bar)
    n_usdc = int(usdc.n_owners_received_usdc)
    usdc_amt = float(usdc.total_usdc_amount or 0)

    # ---- Strict subset funnel (each stage is a real subset of the previous one) ----
    st.markdown("**Funnel** — each step is a strict subset of the previous one.")
    f1, f2, f3, f4, f5 = st.columns(5)
    f1.metric("Registered", f"{n_reg:,}",
              help="All Identity Registered events since mainnet launch.")
    f2.metric("Has on-chain card", f"{n_card:,}",
              delta=f"{n_card/n_reg*100:.1f}% of registered",
              delta_color="off",
              help="agent_uri = data:application/json;base64,…")
    f3.metric("Has any feedback", f"{n_rated:,}",
              delta=f"{n_rated/n_reg*100:.2f}% of registered",
              delta_color="off",
              help="Distinct agents that received at least one NewFeedback event.")
    f4.metric("Passes Sybil bar (≥3)", f"{n_sybil:,}",
              delta=f"{n_sybil/n_reg*100:.3f}% of registered",
              delta_color="off",
              help="unique_clients ≥ 3 — the gist filter.")
    f5.metric("Owner received USDC", f"{n_usdc:,}",
              delta=f"${usdc_amt:,.0f} total",
              delta_color="off",
              help=f"x402=true owners that ever received a USDC transfer. "
                   f"{int(usdc.total_usdc_transfers):,} transfers, "
                   f"${usdc_amt:,.0f} aggregate.")

    # ---- Side attributes of the 9,520 card holders (NOT a funnel) ----
    st.markdown(
        f"**Card attributes** — parallel breakdowns of the {n_card:,} agents "
        "with an inline card. These are *not* a chain; they overlap but neither "
        "is a subset of the other."
    )
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Claims x402 support", f"{int(funnel.n_x402_claim):,}",
              delta=f"{funnel.n_x402_claim/n_card*100:.1f}% of cards",
              delta_color="off",
              help="Self-reported in the card JSON — needs no code or service.")
    a2.metric("Has service endpoint", f"{int(funnel.n_functional):,}",
              delta=f"{funnel.n_functional/n_card*100:.2f}% of cards",
              delta_color="off",
              help="services[] array non-empty.")
    a3.metric("Rated AND claims x402", f"{rated_x402:,}",
              delta="intersection",
              delta_color="off",
              help="Cards claiming x402 that also got at least one feedback event.")
    a4.metric("USDC total received", f"${usdc_amt:,.0f}",
              delta=f"to {n_usdc:,} wallets",
              delta_color="off")

    st.markdown(
        f"**Headline:** {n_reg:,} registrations claim, "
        f"**{n_usdc}** ({n_usdc/n_reg*100:.2f}%) ever received a real USDC "
        f"payment — and those owners together pulled in **${usdc_amt:,.0f}**. "
        "Each funnel stage narrows from claim to verifiable on-chain activity."
    )

    st.divider()

    # ---- Q1 Adoption ----
    with st.spinner("Loading daily Registered counts (Q1)..."):
        df_q1 = run_query(q.q1_adoption_daily())

    total_registered = int(df_q1["n_registered"].sum())
    launch_three_days = int(df_q1.head(3)["n_registered"].sum())
    days_live = int(df_q1.shape[0])

    c1, c2, c3 = st.columns(3)
    c1.metric("Total registered", f"{total_registered:,}")
    c2.metric("First 3 days", f"{launch_three_days:,}",
              help="Jan 29-31 — launch spike from backlog + bots")
    c3.metric("Days live", f"{days_live}")

    st.subheader("Daily Registered events (Q1)")
    st.bar_chart(df_q1.set_index("day")["n_registered"], height=240)
    st.caption(
        f"Launch backlog: {launch_three_days:,} of {total_registered:,} "
        f"({launch_three_days/total_registered*100:.0f}%) of all registrations happened in the first three days. "
        "Baseline afterwards is single-digit to low-hundreds per day."
    )

    st.subheader("Cumulative Registered")
    st.area_chart(df_q1.set_index("day")["cum_registered"], height=200)

    with st.expander("Raw daily counts"):
        st.dataframe(df_q1, width="stretch", hide_index=True)


# =============================================================================
# Tab 2 — Who's Behind It (owner concentration + bot-farm hosts)
# =============================================================================
with tab2:
    st.header("Who's Behind It")
    st.caption(
        "Pareto on owners + bot-farm fingerprint via external URI hosts. "
        "The four competing scanners count each registration as a distinct 'agent' — "
        "but most of them belong to a handful of wallets."
    )

    with st.spinner("Loading owner concentration..."):
        conc = run_query(q.q_owner_concentration()).iloc[0]
        df_owners = run_query(q.q_owner_top(20))
        df_hosts = run_query(q.q_external_uri_hosts(20))
        df_reg = run_query(q.q_registered_via(15))

    n_total = int(conc.n_total)
    n_owners = int(conc.n_owners)

    o0, o1, o2, o3, o4, o5 = st.columns(6)
    o0.metric("Total Registered", f"{n_total:,}",
              help="All Identity Registered events (same number Tab 1 / Tab 3 use as their denominator)")
    o1.metric("Distinct owners", f"{n_owners:,}")
    o2.metric("Avg agents per owner", f"{n_total / n_owners:.1f}")
    o3.metric("Top 1 owner share", f"{conc.top1 / n_total * 100:.1f}%",
              delta=f"{int(conc.top1):,} registrations", delta_color="off")
    o4.metric("Top 10 owners share", f"{conc.top10 / n_total * 100:.1f}%",
              delta=f"{int(conc.top10):,}", delta_color="off")
    o5.metric("Top 20 owners share", f"{conc.top20 / n_total * 100:.1f}%",
              delta=f"{int(conc.top20):,}", delta_color="off")

    st.markdown(
        f"**Headline:** {n_owners:,} owners produced {n_total:,} registrations — "
        f"but the top 20 of them accounted for {conc.top20 / n_total * 100:.0f}% of all activity. "
        f"The #1 wallet (`0xd5d6d96...`) registered {int(conc.top1):,} agents by itself."
    )

    st.divider()

    # ---- Drill-down on the #1 wallet ----
    TOP_WALLET = "0xd5d6d96fa23455ec5e3c00633f85f364d3f5a291"
    with st.expander(f"🔬 Drill-down: top wallet `{TOP_WALLET}`", expanded=False):
        with st.spinner("Loading top-owner deep dive..."):
            dd = run_query(q.q_owner_deep_dive(TOP_WALLET)).iloc[0]

        # Raw facts only — every number is directly derivable from the SQL.
        facts = pd.DataFrame({
            "field": [
                "Agents registered by this wallet",
                "agent_uri empty (NULL or '')",
                "agent_uri = data:application/json;base64,…",
                "agent_uri = https:// or http://",
                "agent_uri = ipfs://",
                "Inline JSON card decoded successfully",
                "Card with x402Support = true",
                "Card with services[] non-empty",
                "Card with nftOrigin set",
                "Distinct agents that received ≥ 1 NewFeedback event",
                "First registration",
                "Last registration",
            ],
            "value": [
                f"{int(dd.n_agents):,}",
                f"{int(dd.n_no_uri):,}",
                f"{int(dd.n_inline_base64):,}",
                f"{int(dd.n_http):,}",
                f"{int(dd.n_ipfs):,}",
                f"{int(dd.n_has_card):,}",
                f"{int(dd.n_x402_true):,}",
                f"{int(dd.n_functional):,}",
                f"{int(dd.n_nft_origin):,}",
                f"{int(dd.n_rated_in_owner):,}",
                f"{dd.first_registration:%Y-%m-%d %H:%M UTC}",
                f"{dd.last_registration:%Y-%m-%d %H:%M UTC}",
            ],
        })
        st.dataframe(facts, hide_index=True, width="stretch")
        st.caption(
            "Raw counts from `q_owner_deep_dive()` in queries.py. "
            "Read them as evidence, not as a verdict."
        )

    # ---- Top owners ----
    col_a, col_b = st.columns([3, 2])
    with col_a:
        st.subheader("Top 20 owners by registration count")
        st.dataframe(
            df_owners.assign(
                first_seen=df_owners["first_seen"].dt.strftime("%Y-%m-%d"),
                last_seen=df_owners["last_seen"].dt.strftime("%Y-%m-%d"),
            ),
            width="stretch",
            hide_index=True,
            height=520,
        )
    with col_b:
        st.subheader("Top owner share (visual)")
        chart_df = df_owners.head(20).copy()
        chart_df["owner_short"] = chart_df["owner"].str[:10] + "…"
        st.bar_chart(chart_df.set_index("owner_short")["n_registrations"], height=520)

    st.divider()

    # ---- External URI hosts (bot-farm fingerprint) ----
    st.subheader("External URI hosts — bot-farm fingerprint")
    st.caption(
        "Off-chain (https/http) `agent_uri` hosts grouped by host. "
        "`n_owners = 1` is the bot-farm signature — one wallet running many cards under one domain. "
        "`ag0.xyz` is the only multi-owner host, meaning it's a platform anyone can mint through."
    )
    col_c, col_d = st.columns([3, 2])
    with col_c:
        st.dataframe(df_hosts, width="stretch", hide_index=True, height=520)
    with col_d:
        host_chart = df_hosts.head(15).copy()
        st.bar_chart(host_chart.set_index("host")["n_registrations"], height=520)

    st.divider()

    # ---- registeredVia (only inline-JSON cards expose this) ----
    st.subheader("`registeredVia` — platform self-declared by inline JSON cards")
    st.caption(
        "Only inline-JSON cards expose this field; most cards leave it blank. "
        "The signal is weaker than `external URI hosts` above, but worth cross-checking."
    )
    st.dataframe(df_reg, width="stretch", hide_index=True)


# =============================================================================
# Tab 3 — What Agents Actually Do (live)
# =============================================================================
with tab3:
    st.header("What Agents Actually Do")
    st.caption(
        "On-chain agent cards (base64-encoded inline JSON) decoded and classified. "
        "Built from `Registered` events only — no off-chain HTTP fetches required."
    )

    with st.spinner("Loading headline KPIs..."):
        kpi = run_query(q.q_headline_kpis()).iloc[0]

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Registered", f"{int(kpi.n_registered):,}")
    c2.metric("Has inline JSON card", f"{int(kpi.n_inline_json):,}",
              help="Card stored on-chain as data:application/json;base64,...")
    c3.metric("Functional (has service endpoint)", f"{int(kpi.n_functional):,}",
              help="services[] array contains at least one entry with an endpoint")
    c4.metric("Claims x402 support", f"{int(kpi.n_x402_true):,}",
              help="Self-reported card field x402Support == true")
    c5.metric("Has nftOrigin", f"{int(kpi.n_nft_origin):,}",
              help="Card carries an nftOrigin block — agent is a wrapper around an NFT")

    st.divider()

    # -------- Row 1: agent_class + uri scheme --------
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("agent_class — what is each registration, really?")
        df_cls = run_query(q.q_agent_class_counts())
        total = int(df_cls["n_agents"].sum())
        df_cls["pct"] = (df_cls["n_agents"] / total * 100).round(2)
        st.dataframe(df_cls, width="stretch", hide_index=True)
        st.bar_chart(df_cls.set_index("agent_class")["n_agents"], height=240)
        st.caption(
            f"Total {total:,} registrations. "
            "Priority order: no_uri → external_uri → test_spam → functional → nft_wrapper → other_card. "
            "Only the `functional` row has a self-declared service endpoint."
        )

    with col_b:
        st.subheader("agent_uri scheme")
        df_scheme = run_query(q.q_uri_scheme_breakdown())
        st.bar_chart(df_scheme.set_index("scheme")["n"], height=240)

        # plain_json profile check — these turned out NOT to be ERC-8004 agents
        plain = run_query(q.q_plain_json_profile_check()).iloc[0]
        st.caption(
            f"`inline_base64` (9,521) is the only scheme we decode on-chain as a "
            f"proper ERC-8004 card. **`plain_json` (2,164) looked like a second "
            f"card pool but actually isn't** — {int(plain.n_twitter_style):,} of "
            f"{int(plain.n_plain):,} ({plain.n_twitter_style/plain.n_plain*100:.1f}%) "
            f"are Twitter-style user profiles (`{{name, bio, type:\"user\"}}`) with "
            f"zero x402, zero services, zero nftOrigin. Different use case piggybacking "
            f"on the same registry. The rest (`https`, `ipfs`, `http`, …) need off-chain "
            f"fetches and may be dead links. Tab 2 breaks the external URIs by host."
        )

    st.divider()

    # -------- Row 2: x402 + service.name --------
    col_c, col_d = st.columns(2)
    with col_c:
        st.subheader("x402 payment support — claim vs reality")
        df_x402 = run_query(q.q_x402_support())
        st.bar_chart(df_x402.set_index("x402_support")["n"], height=180)

        # Reality check — join token_transfers to see who actually received anything
        with st.spinner("Loading token_transfers reality check..."):
            reality = run_query(q.q_x402_claim_vs_reality()).iloc[0]

        n_owners = int(reality.n_x402_true_owners)
        n_any = int(reality.n_owners_received_any_erc20)
        n_usdc = int(reality.n_owners_received_usdc)
        usdc_amt = float(reality.total_usdc_amount or 0)

        rc1, rc2, rc3 = st.columns(3)
        rc1.metric("x402=true owners", f"{n_owners:,}",
                   help="Distinct wallets across all 4,645 true cards")
        rc2.metric("Received any ERC-20", f"{n_any:,}",
                   delta=f"{n_any/n_owners*100:.1f}% of claimers",
                   delta_color="off")
        rc3.metric("Received USDC", f"{n_usdc:,}",
                   delta=f"{n_usdc/n_owners*100:.2f}% of claimers",
                   delta_color="off",
                   help=f"${usdc_amt:,.0f} total across {int(reality.total_usdc_transfers):,} transfers")

        st.caption(
            f"**Headline:** {n_owners:,} owners marked themselves x402-payable. "
            f"Only **{n_usdc} ({n_usdc/n_owners*100:.2f}%)** ever received a USDC transfer "
            f"(${usdc_amt:,.0f} total). The x402Support flag is mostly bot-farm boilerplate — "
            f"{n_owners - n_any:,} of the {n_owners:,} claiming wallets have never received "
            "any ERC-20 token at all. "
            f"99.98% of `true` claims also have `registeredVia=null` (anonymous), while "
            "`khora.fun` (43/44 false) and `booa.app` (7/7 false) explicitly mark "
            "themselves non-payable."
        )

    with col_d:
        st.subheader("Service protocol slot (`services[].name`)")
        df_svc = run_query(q.q_top_service_names(15))
        st.bar_chart(df_svc.set_index("svc_name")["n"], height=240)
        st.caption(
            "OASF dominates because the standard agent-card template emits a single "
            "service entry named `OASF`. `mcp` / `a2a` / `custom` are the more "
            "specific protocol declarations."
        )

    st.divider()

    # -------- Row 3: skills + registeredVia --------
    col_e, col_f = st.columns(2)
    with col_e:
        st.subheader("Top OASF skill paths (services[].skills[])")
        df_skills = run_query(q.q_top_skills(20))
        st.dataframe(df_skills, width="stretch", hide_index=True, height=360)

    with col_f:
        st.subheader("registeredVia — which platform minted this card?")
        df_reg = run_query(q.q_registered_via(10))
        st.dataframe(df_reg, width="stretch", hide_index=True, height=360)
        st.caption(
            "Most cards leave `registeredVia` blank, so this only captures cards from "
            "platforms that brand themselves explicitly (khora.fun, booa.app)."
        )


# =============================================================================
# Tab 4 — Reputation, Real or Fake (Q3 + Q4)
# =============================================================================
with tab4:
    st.header("Reputation, Real or Fake")
    st.caption(
        "Q3 = the gist Sybil bar (unique_clients ≥ 3). "
        "Q4 = the wash campaigns the bar can't catch — same feedbackURI hash reused across "
        "many agents, often by clients that look independent on the surface."
    )

    # ------------ Reputation summary (Sybil-bar-agnostic) ------------
    st.subheader("Reputation overall (before the Sybil bar)")
    with st.spinner("Loading reputation summary..."):
        rep = run_query(q.q_reputation_summary()).iloc[0]
        score_stats = run_query(q.q_score_distribution()).iloc[0]

    r1, r2, r3, r4, r5 = st.columns(5)
    r1.metric("Total NewFeedback events", f"{int(rep.n_feedbacks):,}")
    r2.metric("Distinct agents rated", f"{int(rep.n_agents_rated):,}")
    r3.metric("Distinct reviewers", f"{int(rep.n_unique_reviewers):,}")
    r4.metric(
        "Distinct feedbackURI hashes",
        f"{int(rep.n_distinct_uri_hashes):,}",
        help=f"{rep.n_feedbacks:,} feedbacks share only {rep.n_distinct_uri_hashes} URI hashes "
             f"— mean {rep.n_feedbacks/rep.n_distinct_uri_hashes:.1f}× reuse per hash",
    )
    r5.metric(
        "Perfect-100 scores",
        f"{int(score_stats.n_perfect_100):,}",
        delta=f"{score_stats.n_perfect_100/score_stats.n*100:.0f}% of feedbacks",
        delta_color="off",
        help="Score inflation — a third of all feedbacks are exactly 100",
    )

    # Reviewer-count distribution (the long left tail the Sybil bar dismisses)
    st.markdown("**Where did the Sybil bar cut?**")
    with st.spinner("Loading reviewer-count distribution..."):
        df_rev = run_query(q.q_reviewer_count_distribution())

    # Pretty label order for the chart
    label_order = ["1_reviewer", "2_reviewers", "3_to_4_reviewers",
                   "5_to_9_reviewers", "10_plus_reviewers"]
    df_rev["bucket"] = pd.Categorical(df_rev["bucket"], categories=label_order, ordered=True)
    df_rev = df_rev.sort_values("bucket").reset_index(drop=True)

    cc1, cc2 = st.columns([2, 1])
    with cc1:
        st.bar_chart(df_rev.set_index("bucket")["n_agents"], height=240)
    with cc2:
        st.dataframe(df_rev, width="stretch", hide_index=True)

    n_one = int(df_rev.loc[df_rev["bucket"] == "1_reviewer", "n_agents"].sum())
    st.caption(
        f"**{n_one:,} agents have exactly one reviewer** "
        f"({n_one/rep.n_agents_rated*100:.0f}% of all rated agents) — the Sybil bar dismisses these "
        f"as noise, but they're still on every other scanner's count. Median score across "
        f"all {int(score_stats.n):,} scored feedbacks is {score_stats.p50:.0f}; "
        f"p90 is {score_stats.p90:.0f}; max is {score_stats.max_score:.0f} (2 outliers from a "
        f"fixedDecimals quirk in the data field)."
    )

    st.divider()

    # ------------ Q3 Leaderboard ------------
    st.subheader("Q3 — Leaderboard (agents with ≥ 3 unique reviewers)")
    with st.spinner("Loading Q3 leaderboard..."):
        df_q3_full = run_query(q.q3_leaderboard(min_unique_clients=3, limit=10000))

    c1, c2, c3 = st.columns(3)
    c1.metric("Agents passing the Sybil bar", f"{len(df_q3_full):,}",
              help="unique_clients ≥ 3 — the standard gist filter")
    c2.metric("Of total Registered", f"{len(df_q3_full)/34566*100:.2f}%",
              help="34,566 registrations → only this many got 3+ distinct reviewers")
    c3.metric("Median avg_score", f"{df_q3_full['avg_score'].median():.1f}")

    st.dataframe(
        df_q3_full.head(50),
        width="stretch",
        hide_index=True,
        height=420,
    )
    st.caption(
        "Top row (agent 10307) has 44 unique reviewers but max_score=1000 — score "
        "encoding has outliers (the fixedDecimals field in `data` can carry odd "
        "exponents). Worth flagging, not filtering."
    )

    st.divider()

    # ------------ Q4 Client dominance ------------
    st.subheader("Q4 — Client dominance (which wallet gives the most feedback?)")
    with st.spinner("Loading Q4 client dominance..."):
        df_q4 = run_query(q.q4_client_dominance(limit=20))

    st.dataframe(
        df_q4,
        width="stretch",
        hide_index=True,
        column_config={
            "uri_diversity_ratio": st.column_config.ProgressColumn(
                "uri diversity",
                help="distinct_feedback_uris / feedbacks_given. Low = the same "
                     "feedback URI was reused (wash). High = independent feedback.",
                min_value=0.0, max_value=1.0,
            ),
        },
    )
    st.caption(
        "Top client gave 1,215 feedbacks across 1,102 agents with **only 2 distinct feedback URIs** "
        "(diversity ratio 0.002). That's not 1,102 independent opinions — it's one opinion replayed. "
        "Note: client `0x668add...` (handoff §C smoking-gun) appears in row 4 with 224 feedbacks / 4 URIs."
    )

    st.divider()

    # ------------ Q4b feedbackURI hash collisions ------------
    st.subheader("Q4b — feedbackURI hash collisions (shared evaluation source)")
    with st.spinner("Loading Q4b URI collisions..."):
        df_q4b = run_query(q.q4_feedback_uri_collisions(limit=15))

    st.dataframe(df_q4b, width="stretch", hide_index=True)
    st.caption(
        "Each row = one feedbackURI hash reused across multiple feedbacks. "
        "The headline: hash `0xc5d246...` appears 386 times with **301 distinct clients** "
        "targeting 39 agents — that's a coordinated Sybil campaign disguised as 301 independent voices. "
        "Hash `0xd6be4ef8...` (handoff §C) shows up with 80 clients / 55 agents — the agent-22771 campaign."
    )

    st.divider()

    # ------------ Drill-downs ------------
    st.subheader("Drill-downs")

    with st.expander("🔍 Score > 100 outliers (decoding artifacts)", expanded=False):
        with st.spinner("Loading score outliers..."):
            df_out = run_query(q.q_score_outliers(100.0))
        st.dataframe(
            df_out.assign(
                block_timestamp=df_out["block_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S"),
            ),
            width="stretch", hide_index=True,
        )
        st.caption(
            f"{len(df_out)} feedback rows have score > 100. Both are on agent_id "
            f"`10307` (top of Q3 leaderboard). Root cause: the `fixedDecimals` exponent "
            "in the NewFeedback `data` field can carry odd values, multiplying the "
            "rendered score by 10× or 100×. Flag, don't filter."
        )

    with st.expander("🔍 Clients giving ONLY perfect 100 (wash signature)", expanded=False):
        with st.spinner("Loading perfect-100 client list..."):
            df_p100 = run_query(q.q_perfect_100_clients(min_feedbacks=5, limit=30))
        st.dataframe(df_p100, width="stretch", hide_index=True)
        st.caption(
            f"{len(df_p100)} wallets gave at least 5 feedbacks and every single one "
            f"scored exactly 100. Most narrow case: `0x9725899d...` — 9 feedbacks, "
            f"all 100, on **the same agent**, using **the same feedbackURI hash**. "
            "These wallets won't trip the unique_clients ≥ 3 bar by themselves, "
            "but their pattern is unmistakable."
        )


# =============================================================================
# Tab 5 — 🎯 Trustworthy + Payable (the prize-statement view)
# =============================================================================
with tab5:
    st.header("🎯 Trustworthy + Payable agents")
    st.caption(
        "The intersection of three filters: ≥ 3 unique reviewers, average score "
        "≥ 80, and a card claiming x402 support. Each row is then enriched with "
        "the owner's on-chain ERC-20 / USDC activity. Sorted so wallets that "
        "actually received USDC float to the top."
    )

    s1, s2 = st.columns(2)
    min_uc = s1.slider("Minimum unique reviewers", 1, 10, 3)
    min_avg = s2.slider("Minimum average score", 0.0, 100.0, 80.0, step=5.0)

    with st.spinner("Running the intersection query..."):
        df_tp = run_query(q.q_trustworthy_payable(min_uc, min_avg))

    n_match = len(df_tp)
    n_received_usdc = int((df_tp["n_usdc_transfers"] > 0).sum())
    n_received_erc20 = int((df_tp["n_erc20_transfers"] > 0).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Agents in intersection", f"{n_match:,}",
              help="Out of 34,566 registered agents")
    m2.metric("Owner received ERC-20", f"{n_received_erc20:,}")
    m3.metric("Owner received USDC", f"{n_received_usdc:,}",
              help="The strongest 'real economic activity' signal")
    m4.metric("Survival rate", f"{n_match/34566*100:.3f}%",
              help="Fraction of total Registered events that clear every bar")

    st.dataframe(
        df_tp,
        width="stretch",
        hide_index=True,
        column_config={
            "owner": st.column_config.TextColumn(width="small"),
            "description": st.column_config.TextColumn(width="medium"),
            "usdc_amount": st.column_config.NumberColumn(format="$%.2f"),
        },
    )

    if n_match > 0:
        top = df_tp.iloc[0]
        if top["n_usdc_transfers"] > 0:
            st.success(
                f"**Top result:** `{top['name']}` (agent {int(top['agent_id'])}) — "
                f"{int(top['unique_clients'])} reviewers, avg score {top['avg_score']}, "
                f"and the owner received **${float(top['usdc_amount']):.2f}** in "
                f"{int(top['n_usdc_transfers'])} USDC transfers."
            )
        else:
            st.warning(
                "Every intersection match claims x402 — but the top result still "
                "hasn't received a single USDC transfer. The claim/reality gap "
                "shows up even at the top of the leaderboard."
            )
    else:
        st.info(
            "No agents match the current sliders. Loosen `min_unique_clients` "
            "or `min_avg_score` to widen the net."
        )


# =============================================================================
# Tab 6 — 🔍 Find Agents (filter UI + NL search via Claude)
# =============================================================================
with tab6:
    st.header("🔍 Find Agents")
    st.caption(
        "Free-text natural-language search (powered by Vertex AI Gemini), or "
        "use the structured filters below. Both end up calling the same SQL — "
        "`q_agent_search()` in `queries.py`. Auth runs through the same "
        "service account that already reads BigQuery — no API key anywhere."
    )

    # ----- Natural-language box -----
    nl_text = st.text_input(
        "Natural-language search",
        placeholder='e.g. "agents with at least 5 reviews and high reputation"',
        key="nl_query",
    )

    nl_filters: dict | None = None
    if nl_text:
        if not nl_search.available():
            st.warning(
                "`google-genai` SDK is not installed. Add `google-genai>=2.8` to "
                "requirements.txt and redeploy."
            )
        else:
            try:
                with st.spinner("Asking Gemini to parse the request..."):
                    nl_filters = nl_search.parse_query(nl_text)
                if nl_filters:
                    st.success(f"Parsed filters: `{nl_filters}`")
                else:
                    st.error("Gemini couldn't extract a filter — try rephrasing.")
            except Exception as e:
                st.error(
                    f"Vertex AI call failed: `{e}`. Make sure the active service "
                    "account has `roles/aiplatform.user` and the Vertex AI API is "
                    "enabled in this project."
                )

    st.divider()

    # ----- Structured filters (always visible) -----
    st.markdown("**Structured filters** (used directly, or pre-filled from NL result)")
    nlf = nl_filters or {}

    fc1, fc2, fc3 = st.columns(3)
    agent_id_str = fc1.text_input(
        "agent_id (exact)",
        value=str(nlf.get("agent_id") or ""),
        placeholder="e.g. 10307",
    )
    owner_str = fc2.text_input(
        "owner address",
        value=nlf.get("owner") or "",
        placeholder="0x…",
    )
    name_contains = fc3.text_input(
        "name contains",
        value=nlf.get("name_contains") or "",
        placeholder="e.g. trader",
    )

    fc4, fc5, fc6 = st.columns(3)
    desc_contains = fc4.text_input(
        "description contains",
        value=nlf.get("description_contains") or "",
    )
    min_uc_s = fc5.number_input(
        "min unique reviewers",
        min_value=0,
        max_value=50,
        value=int(nlf.get("min_unique_clients") or 0),
    )
    min_score_s = fc6.number_input(
        "min avg score",
        min_value=0.0,
        max_value=100.0,
        value=float(nlf.get("min_avg_score") or 0.0),
        step=5.0,
    )

    fc7, fc8 = st.columns(2)
    x402_only = fc7.checkbox(
        "x402=true only",
        value=bool(nlf.get("x402_only", False)),
    )
    has_services_flag = fc8.checkbox(
        "Has services[] endpoint",
        value=bool(nlf.get("has_services", False)),
    )

    run = st.button("Search", type="primary")

    if run or nl_filters:
        kwargs = {
            "agent_id": int(agent_id_str) if agent_id_str.strip() else None,
            "owner": owner_str.strip() or None,
            "name_contains": name_contains.strip() or None,
            "description_contains": desc_contains.strip() or None,
            "min_unique_clients": int(min_uc_s) if min_uc_s > 0 else None,
            "min_avg_score": float(min_score_s) if min_score_s > 0 else None,
            "x402_only": x402_only,
            "has_services": has_services_flag,
            "limit": int(nlf.get("limit", 50)),
        }
        with st.spinner("Querying BigQuery..."):
            df_search = run_query(q.q_agent_search(**kwargs))

        st.markdown(f"**{len(df_search)} result(s)**")
        st.dataframe(df_search, width="stretch", hide_index=True, height=480)

        if len(df_search) == 0:
            st.info("No agents match these filters. Loosen the criteria.")


# =============================================================================
# Tab 7 — 📋 Cheat Sheet (every headline number on one screen)
# =============================================================================
with tab7:
    st.header("📋 Cheat Sheet — everything on one page")
    st.caption(
        "Every number here is also derived from one of the queries powering Tabs 1-4. "
        "Same cache, same denominators, same partition cut."
    )

    # All numbers come from already-cached queries — no extra BigQuery cost
    with st.spinner("Loading…"):
        funnel = run_query(q.q_funnel()).iloc[0]
        rated_x402 = int(run_query(q.q_rated_x402_count()).iloc[0]["n_rated_x402"])
        usdc = run_query(q.q_x402_claim_vs_reality()).iloc[0]
        conc = run_query(q.q_owner_concentration()).iloc[0]
        hosts = run_query(q.q_external_uri_hosts(5))
        rep = run_query(q.q_reputation_summary()).iloc[0]
        score_stats = run_query(q.q_score_distribution()).iloc[0]
        rev = run_query(q.q_reviewer_count_distribution())

    n_reg = int(funnel.n_registered)
    n_one_reviewer = int(rev.loc[rev["bucket"] == "1_reviewer", "n_agents"].sum())
    top_host = hosts.iloc[0]

    st.subheader("Funnel — claim → reality")
    c = st.columns(8)
    stages = [
        ("Registered", n_reg, None),
        ("Has card", funnel.n_inline_json, "27.5%"),
        ("Functional", funnel.n_functional, "0.65%"),
        ("Claims x402", funnel.n_x402_claim, "13.4%"),
        ("Has feedback", funnel.n_agents_rated, "4.8%"),
        ("Rated AND x402", rated_x402, "0.62%"),
        ("Sybil pass ≥3", funnel.n_passes_sybil_bar, "0.30%"),
        ("Received USDC", usdc.n_owners_received_usdc, "0.09%"),
    ]
    for col, (label, v, share) in zip(c, stages):
        col.metric(label, f"{int(v):,}", delta=share, delta_color="off")

    st.divider()

    st.subheader("Owner concentration")
    o = st.columns(4)
    o[0].metric("Distinct owners", f"{int(conc.n_owners):,}")
    o[1].metric("Top 1 share",  f"{conc.top1 / n_reg * 100:.1f}%",
                delta=f"{int(conc.top1):,}", delta_color="off")
    o[2].metric("Top 10 share", f"{conc.top10 / n_reg * 100:.1f}%",
                delta=f"{int(conc.top10):,}", delta_color="off")
    o[3].metric("Top 20 share", f"{conc.top20 / n_reg * 100:.1f}%",
                delta=f"{int(conc.top20):,}", delta_color="off")

    st.subheader("Bot-farm hosts (top external URI domains)")
    h = st.columns(min(5, len(hosts)))
    for i, row in hosts.head(5).iterrows():
        h[i].metric(
            row["host"],
            f"{int(row['n_registrations']):,}",
            delta=f"{int(row['n_owners'])} owner(s)",
            delta_color="off",
            help="n_owners == 1 is the bot-farm fingerprint",
        )

    st.divider()

    st.subheader("Reputation — what's real, what's wash")
    rep_cols = st.columns(5)
    rep_cols[0].metric("NewFeedback events", f"{int(rep.n_feedbacks):,}")
    rep_cols[1].metric("Distinct URI hashes", f"{int(rep.n_distinct_uri_hashes):,}",
                       delta=f"≈ {rep.n_feedbacks/rep.n_distinct_uri_hashes:.0f}× reuse",
                       delta_color="off")
    rep_cols[2].metric("1-reviewer agents", f"{n_one_reviewer:,}",
                       delta=f"{n_one_reviewer/rep.n_agents_rated*100:.0f}% of rated",
                       delta_color="off",
                       help="The long tail the Sybil bar discards")
    rep_cols[3].metric("Perfect-100 scores", f"{int(score_stats.n_perfect_100):,}",
                       delta=f"{score_stats.n_perfect_100/score_stats.n*100:.0f}% of feedbacks",
                       delta_color="off")
    rep_cols[4].metric("USDC actually paid",
                       f"${float(usdc.total_usdc_amount or 0):,.0f}",
                       delta=f"to {int(usdc.n_owners_received_usdc):,} wallets",
                       delta_color="off")

    st.divider()

    st.markdown(
        "### The one-line pitch\n"
        f"> *{n_reg:,} registrations. {int(funnel.n_passes_sybil_bar)} pass the Sybil bar "
        f"({funnel.n_passes_sybil_bar/n_reg*100:.2f}%). "
        f"{int(usdc.n_owners_received_usdc)} ever received a USDC payment "
        f"({usdc.n_owners_received_usdc/n_reg*100:.3f}%). "
        f"The top wallet alone registered {int(conc.top1):,} agents — every one of them empty.*"
    )
