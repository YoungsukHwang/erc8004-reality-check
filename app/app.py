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


tab1, tab2, tab3, tab4 = st.tabs([
    "The Real Numbers",
    "Who's Behind It",
    "What Agents Actually Do",
    "Reputation, Real or Fake",
])


# =============================================================================
# Tab 1 — The Real Numbers (Q1 Adoption + funnel)
# =============================================================================
with tab1:
    st.header("The Real Numbers")
    st.caption("Funnel: registered → has card → functional → rated → passes Sybil bar.")

    # ---- Funnel headline row ----
    with st.spinner("Loading funnel..."):
        funnel = run_query(q.q_funnel()).iloc[0]

    n_reg = int(funnel.n_registered)
    f1, f2, f3, f4, f5, f6 = st.columns(6)
    f1.metric("Registered", f"{n_reg:,}",
              help="All Identity Registered events since mainnet launch")
    f2.metric("Has on-chain card", f"{int(funnel.n_inline_json):,}",
              delta=f"{funnel.n_inline_json/n_reg*100:.1f}%", delta_color="off")
    f3.metric("Functional (has endpoint)", f"{int(funnel.n_functional):,}",
              delta=f"{funnel.n_functional/n_reg*100:.2f}%", delta_color="off")
    f4.metric("Has any feedback", f"{int(funnel.n_agents_rated):,}",
              delta=f"{funnel.n_agents_rated/n_reg*100:.1f}%", delta_color="off",
              help="Distinct agents that received at least one NewFeedback event")
    f5.metric("Passes Sybil bar (≥3)", f"{int(funnel.n_passes_sybil_bar):,}",
              delta=f"{funnel.n_passes_sybil_bar/n_reg*100:.2f}%", delta_color="off",
              help="unique_clients >= 3 — the gist filter")
    f6.metric("Claims x402", f"{int(funnel.n_x402_claim):,}",
              delta=f"{funnel.n_x402_claim/n_reg*100:.1f}%", delta_color="off",
              help="Self-reported card field x402Support == true")

    st.markdown(
        f"**Headline:** {n_reg:,} registrations → only **{int(funnel.n_passes_sybil_bar)}** "
        f"({funnel.n_passes_sybil_bar/n_reg*100:.2f}%) cleared the standard Sybil bar — "
        f"and those still get exposed in Tab 4."
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
