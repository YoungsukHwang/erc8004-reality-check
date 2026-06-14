"""Validated BigQuery SQL for ERC-8004 Explorer views.

Each function returns a SQL string ready for `bq.run_query()`. All queries
include the partition cut and signature filter (cheap on the free tier).

Key conventions (verified against raw inline JSON cards):
- Identity Registered topic layout: topics[1]=agent_id, topics[2]=owner (last 20 bytes)
- Reputation NewFeedback layout: topics[1]=agent_id, topics[2]=client, topics[3]=feedbackURI hash
- Inline card JSON uses `x402Support` (capital S), `services[].name` as protocol slot,
  `services[].skills` as a string array of OASF taxonomy paths, and `nftOrigin` dict
  on most cards.
"""
from __future__ import annotations

from bq import (
    IDENTITY_BASE_CTE,
    REPUTATION_BASE_CTE,
    INLINE_JSON_EXPR,
    X402_VALUE_EXPR,
    LOGS,
    TOKEN_TRANSFERS,
    REPUTATION_REGISTRY,
    SIG_NEW_FEEDBACK,
    PARTITION_CUT,
    USDC_ADDRESS,
)


# -----------------------------------------------------------------------------
# Shared decoded CTE — Identity Registered + inline card JSON
# -----------------------------------------------------------------------------

DECODED_IDENTITY_CTE = f"""
{IDENTITY_BASE_CTE},
decoded AS (
  SELECT
    block_timestamp, agent_id, owner, agent_uri,
    CASE
      WHEN STARTS_WITH(agent_uri, 'data:application/json;base64,')
        THEN {INLINE_JSON_EXPR}
      ELSE NULL
    END AS card_json
  FROM identity_base
)
"""


# -----------------------------------------------------------------------------
# Tab 3 — What Agents Actually Do
# -----------------------------------------------------------------------------

def q_agent_class_counts() -> str:
    """6-bucket classification across all 34,566 Registered events."""
    return f"""
    WITH {DECODED_IDENTITY_CTE},
    classified AS (
      SELECT
        agent_id, owner, agent_uri, card_json,
        LOWER(COALESCE(JSON_VALUE(card_json, '$.name'), '')) AS name_l,
        LOWER(COALESCE(JSON_VALUE(card_json, '$.description'), '')) AS desc_l,
        JSON_QUERY_ARRAY(card_json, '$.services') AS services_arr,
        JSON_VALUE(card_json, '$.nftOrigin.contract') AS nft_contract
      FROM decoded
    )
    SELECT
      CASE
        WHEN agent_uri IS NULL OR agent_uri = '' THEN 'no_uri'
        WHEN card_json IS NULL THEN 'external_uri'
        WHEN REGEXP_CONTAINS(name_l, r'\\btest\\b') OR REGEXP_CONTAINS(desc_l, r'\\btest\\b')
          THEN 'test_spam'
        WHEN ARRAY_LENGTH(services_arr) > 0 THEN 'functional'
        WHEN nft_contract IS NOT NULL THEN 'nft_wrapper'
        ELSE 'other_card'
      END AS agent_class,
      COUNT(*) AS n_agents,
      COUNT(DISTINCT owner) AS n_owners
    FROM classified
    GROUP BY agent_class
    ORDER BY n_agents DESC
    """


def q_x402_support() -> str:
    """Self-reported x402 payment support among inline JSON cards.
    Combines both 'x402Support' (6,929 cards) and 'x402support' (513 cards)
    spellings — verified disjoint, so no double-counting."""
    return f"""
    WITH {IDENTITY_BASE_CTE},
    decoded AS (
      SELECT {INLINE_JSON_EXPR} AS card_json
      FROM identity_base
      WHERE STARTS_WITH(agent_uri, 'data:application/json;base64,')
    )
    SELECT
      COALESCE({X402_VALUE_EXPR}, '(null)') AS x402_support,
      COUNT(*) AS n
    FROM decoded
    WHERE card_json IS NOT NULL
    GROUP BY x402_support
    ORDER BY n DESC
    """


def q_top_service_names(limit: int = 15) -> str:
    """Protocol slot — service.name (OASF / web / custom / mcp / a2a / ens / ...)."""
    return f"""
    WITH {IDENTITY_BASE_CTE},
    decoded AS (
      SELECT {INLINE_JSON_EXPR} AS card_json
      FROM identity_base
      WHERE STARTS_WITH(agent_uri, 'data:application/json;base64,')
    ),
    flat AS (
      SELECT LOWER(JSON_VALUE(svc, '$.name')) AS svc_name
      FROM decoded, UNNEST(COALESCE(JSON_QUERY_ARRAY(card_json, '$.services'), [])) AS svc
    )
    SELECT COALESCE(svc_name, '(null)') AS svc_name, COUNT(*) AS n
    FROM flat GROUP BY svc_name ORDER BY n DESC LIMIT {limit}
    """


def q_top_skills(limit: int = 20) -> str:
    """OASF skill taxonomy paths — flattened across services[].skills[]."""
    return f"""
    WITH {IDENTITY_BASE_CTE},
    decoded AS (
      SELECT {INLINE_JSON_EXPR} AS card_json
      FROM identity_base
      WHERE STARTS_WITH(agent_uri, 'data:application/json;base64,')
    ),
    flat AS (
      SELECT LOWER(sk) AS skill
      FROM decoded,
           UNNEST(COALESCE(JSON_QUERY_ARRAY(card_json, '$.services'), [])) AS svc,
           UNNEST(JSON_VALUE_ARRAY(svc, '$.skills')) AS sk
    )
    SELECT skill, COUNT(*) AS n
    FROM flat WHERE skill IS NOT NULL
    GROUP BY skill ORDER BY n DESC LIMIT {limit}
    """


def q_registered_via(limit: int = 10) -> str:
    """Self-declared registration platform (khora.fun, booa.app, ...)."""
    return f"""
    WITH {IDENTITY_BASE_CTE},
    decoded AS (
      SELECT owner, {INLINE_JSON_EXPR} AS card_json
      FROM identity_base
      WHERE STARTS_WITH(agent_uri, 'data:application/json;base64,')
    )
    SELECT
      COALESCE(JSON_VALUE(card_json, '$.registeredVia'), '(null)') AS registered_via,
      COUNT(*) AS n,
      COUNT(DISTINCT owner) AS n_owners
    FROM decoded
    WHERE card_json IS NOT NULL
    GROUP BY registered_via
    ORDER BY n DESC LIMIT {limit}
    """


def q_plain_json_profile_check() -> str:
    """Of the 2,164 plain_json cards, how many are Twitter-style user profiles
    instead of ERC-8004 agent cards? (Discovered during validation: 99.7%.)"""
    return f"""
    WITH {IDENTITY_BASE_CTE},
    plain AS (
      SELECT agent_uri AS card_json FROM identity_base
      WHERE STARTS_WITH(agent_uri, '{{')
    )
    SELECT
      COUNT(*) AS n_plain,
      COUNTIF(JSON_VALUE(card_json, '$.type') = 'user') AS n_twitter_style,
      COUNTIF(JSON_VALUE(card_json, '$.x402Support') IS NOT NULL
           OR JSON_VALUE(card_json, '$.x402support') IS NOT NULL) AS n_has_x402,
      COUNTIF(ARRAY_LENGTH(JSON_QUERY_ARRAY(card_json, '$.services')) > 0) AS n_has_services,
      COUNTIF(JSON_VALUE(card_json, '$.nftOrigin.contract') IS NOT NULL) AS n_has_nft_origin
    FROM plain
    """


def q_uri_scheme_breakdown() -> str:
    """Distribution of agent_uri schemes across all Registered events.
    'other' (~2,286) is broken down into plain_json, raw_xml_svg, quoted_empty,
    and other_text — most are still non-verifiable on-chain."""
    return f"""
    WITH {IDENTITY_BASE_CTE}
    SELECT
      CASE
        WHEN agent_uri IS NULL OR agent_uri = '' THEN 'none'
        WHEN STARTS_WITH(agent_uri, 'data:application/json;base64,') THEN 'inline_base64'
        WHEN STARTS_WITH(agent_uri, 'data:application/json') THEN 'inline_json_other'
        WHEN STARTS_WITH(agent_uri, 'data:') THEN 'data_other'
        WHEN STARTS_WITH(agent_uri, 'https://') THEN 'https'
        WHEN STARTS_WITH(agent_uri, 'http://') THEN 'http'
        WHEN STARTS_WITH(agent_uri, 'ipfs://') THEN 'ipfs'
        WHEN STARTS_WITH(agent_uri, '{{') THEN 'plain_json'
        WHEN STARTS_WITH(agent_uri, '<') THEN 'raw_xml_svg'
        WHEN agent_uri = '""' THEN 'quoted_empty'
        ELSE 'other_text'
      END AS scheme,
      COUNT(*) AS n
    FROM identity_base
    GROUP BY scheme
    ORDER BY n DESC
    """


def q_headline_kpis() -> str:
    """Single-row KPI roll-up for the top of tab 3."""
    return f"""
    WITH {DECODED_IDENTITY_CTE}
    SELECT
      COUNT(*) AS n_registered,
      COUNTIF(card_json IS NOT NULL) AS n_inline_json,
      COUNTIF(ARRAY_LENGTH(JSON_QUERY_ARRAY(card_json, '$.services')) > 0) AS n_functional,
      COUNTIF({X402_VALUE_EXPR} = 'true') AS n_x402_true,
      COUNTIF(JSON_VALUE(card_json, '$.nftOrigin.contract') IS NOT NULL) AS n_nft_origin
    FROM decoded
    """


# -----------------------------------------------------------------------------
# Q1 — Adoption: daily Registered count + cumulative
# -----------------------------------------------------------------------------

def q1_adoption_daily() -> str:
    return f"""
    WITH {IDENTITY_BASE_CTE},
    by_day AS (
      SELECT DATE(block_timestamp) AS day, COUNT(*) AS n_registered
      FROM identity_base
      GROUP BY day
    )
    SELECT
      day,
      n_registered,
      SUM(n_registered) OVER (ORDER BY day) AS cum_registered
    FROM by_day
    ORDER BY day
    """


# -----------------------------------------------------------------------------
# Q3 — Leaderboard: agents with >= 3 unique reviewers (gist Sybil bar)
# -----------------------------------------------------------------------------

def q3_leaderboard(min_unique_clients: int = 3, limit: int = 50) -> str:
    return f"""
    WITH {REPUTATION_BASE_CTE}
    SELECT
      agent_id,
      COUNT(*) AS n_feedbacks,
      COUNT(DISTINCT client) AS unique_clients,
      ROUND(AVG(score), 2) AS avg_score,
      ROUND(MIN(score), 2) AS min_score,
      ROUND(MAX(score), 2) AS max_score
    FROM reputation_base
    WHERE score IS NOT NULL
    GROUP BY agent_id
    HAVING COUNT(DISTINCT client) >= {min_unique_clients}
    ORDER BY avg_score DESC, unique_clients DESC
    LIMIT {limit}
    """


# -----------------------------------------------------------------------------
# Q4 — Wash detection: client dominance + feedbackURI hash duplication
#      (verbatim from handoff §B, signature prefix is '0x' — the '0x53' in
#       the original gist was a typo)
# -----------------------------------------------------------------------------

def q4_client_dominance(limit: int = 20) -> str:
    return f"""
    SELECT
      CONCAT('0x', SUBSTR(topics[SAFE_OFFSET(2)], 27)) AS client,
      COUNT(*) AS feedbacks_given,
      COUNT(DISTINCT SAFE_CAST(topics[SAFE_OFFSET(1)] AS INT64)) AS agents_rated,
      COUNT(DISTINCT topics[SAFE_OFFSET(3)]) AS distinct_feedback_uris,
      ROUND(
        SAFE_DIVIDE(COUNT(DISTINCT topics[SAFE_OFFSET(3)]), COUNT(*)),
        3
      ) AS uri_diversity_ratio
    FROM {LOGS}
    WHERE address = '{REPUTATION_REGISTRY}'
      AND topics[SAFE_OFFSET(0)] = '{SIG_NEW_FEEDBACK}'
      AND block_timestamp >= {PARTITION_CUT}
    GROUP BY client
    ORDER BY feedbacks_given DESC
    LIMIT {limit}
    """


# -----------------------------------------------------------------------------
# Funnel — single row roll-up across Identity + Reputation
# -----------------------------------------------------------------------------

def q_funnel() -> str:
    """Headline funnel from raw Registered events all the way down to
    'passed the Sybil bar' (unique_clients >= 3). Single row."""
    return f"""
    WITH {DECODED_IDENTITY_CTE},
    {REPUTATION_BASE_CTE},
    identity_stats AS (
      SELECT
        COUNT(*) AS n_registered,
        COUNTIF(card_json IS NOT NULL) AS n_inline_json,
        COUNTIF(ARRAY_LENGTH(JSON_QUERY_ARRAY(card_json, '$.services')) > 0)
          AS n_functional,
        COUNTIF({X402_VALUE_EXPR} = 'true') AS n_x402_claim
      FROM decoded
    ),
    reputation_stats AS (
      SELECT
        COUNT(*) AS n_feedbacks,
        COUNT(DISTINCT agent_id) AS n_agents_rated,
        COUNT(DISTINCT client) AS n_unique_reviewers
      FROM reputation_base
    ),
    sybil_pass AS (
      SELECT COUNT(*) AS n_passes_sybil_bar FROM (
        SELECT agent_id FROM reputation_base
        WHERE score IS NOT NULL
        GROUP BY agent_id HAVING COUNT(DISTINCT client) >= 3
      )
    )
    SELECT *
    FROM identity_stats, reputation_stats, sybil_pass
    """


# -----------------------------------------------------------------------------
# Reputation summary + the agents Sybil bar excludes
# -----------------------------------------------------------------------------

def q_reputation_summary() -> str:
    """Counts that don't depend on the Sybil bar."""
    return f"""
    WITH {REPUTATION_BASE_CTE}
    SELECT
      COUNT(*) AS n_feedbacks,
      COUNTIF(score IS NOT NULL) AS n_feedbacks_with_score,
      COUNT(DISTINCT agent_id) AS n_agents_rated,
      COUNT(DISTINCT client) AS n_unique_reviewers,
      COUNT(DISTINCT feedback_uri_hash) AS n_distinct_uri_hashes
    FROM reputation_base
    """


def q_reviewer_count_distribution() -> str:
    """How many agents have 1 / 2 / 3-4 / 5-9 / 10+ unique reviewers? The Sybil
    bar (>=3) hides the long left tail that the gist filter dismisses."""
    return f"""
    WITH {REPUTATION_BASE_CTE},
    per_agent AS (
      SELECT agent_id, COUNT(DISTINCT client) AS n_clients
      FROM reputation_base
      GROUP BY agent_id
    )
    SELECT
      CASE
        WHEN n_clients = 1 THEN '1_reviewer'
        WHEN n_clients = 2 THEN '2_reviewers'
        WHEN n_clients BETWEEN 3 AND 4 THEN '3_to_4_reviewers'
        WHEN n_clients BETWEEN 5 AND 9 THEN '5_to_9_reviewers'
        ELSE '10_plus_reviewers'
      END AS bucket,
      COUNT(*) AS n_agents,
      ROUND(AVG(n_clients), 2) AS avg_reviewers_in_bucket
    FROM per_agent
    GROUP BY bucket
    ORDER BY bucket
    """


def q_score_distribution() -> str:
    """Score quantiles across ALL feedbacks (not just Sybil-passing agents)."""
    return f"""
    WITH {REPUTATION_BASE_CTE},
    scored AS (
      SELECT score FROM reputation_base WHERE score IS NOT NULL
    )
    SELECT
      COUNT(*) AS n,
      ROUND(AVG(score), 2) AS avg_score,
      ROUND(APPROX_QUANTILES(score, 100)[OFFSET(10)], 2) AS p10,
      ROUND(APPROX_QUANTILES(score, 100)[OFFSET(50)], 2) AS p50,
      ROUND(APPROX_QUANTILES(score, 100)[OFFSET(90)], 2) AS p90,
      ROUND(APPROX_QUANTILES(score, 100)[OFFSET(99)], 2) AS p99,
      ROUND(MAX(score), 2) AS max_score,
      COUNTIF(score = 100) AS n_perfect_100,
      COUNTIF(score > 100) AS n_above_100_outliers
    FROM scored
    """


# -----------------------------------------------------------------------------
# Owner concentration (Tab 2)
# -----------------------------------------------------------------------------

def q_owner_top(limit: int = 20) -> str:
    """Top owners by registration count."""
    return f"""
    WITH {IDENTITY_BASE_CTE}
    SELECT
      owner,
      COUNT(*) AS n_registrations,
      COUNT(DISTINCT agent_id) AS n_distinct_agents,
      MIN(block_timestamp) AS first_seen,
      MAX(block_timestamp) AS last_seen
    FROM identity_base
    GROUP BY owner
    ORDER BY n_registrations DESC
    LIMIT {limit}
    """


def q_owner_concentration() -> str:
    """Top-N share of total registrations — Pareto on owner side."""
    return f"""
    WITH {IDENTITY_BASE_CTE},
    by_owner AS (
      SELECT owner, COUNT(*) AS n FROM identity_base GROUP BY owner
    ),
    ranked AS (
      SELECT owner, n, ROW_NUMBER() OVER (ORDER BY n DESC) AS rnk
      FROM by_owner
    )
    SELECT
      COUNT(*) AS n_owners,
      SUM(n) AS n_total,
      SUM(IF(rnk = 1, n, 0)) AS top1,
      SUM(IF(rnk <= 10, n, 0)) AS top10,
      SUM(IF(rnk <= 20, n, 0)) AS top20,
      SUM(IF(rnk <= 100, n, 0)) AS top100
    FROM ranked
    """


# -----------------------------------------------------------------------------
# External URI hosts — bot-farm fingerprint
# -----------------------------------------------------------------------------

def q_external_uri_hosts(limit: int = 20) -> str:
    """Top hosts for off-chain agent_uri (https/http). Surfaces bot farms."""
    return f"""
    WITH {IDENTITY_BASE_CTE}
    SELECT
      REGEXP_EXTRACT(agent_uri, r'^https?://([^/]+)') AS host,
      COUNT(*) AS n_registrations,
      COUNT(DISTINCT owner) AS n_owners
    FROM identity_base
    WHERE agent_uri LIKE 'http%'
    GROUP BY host
    ORDER BY n_registrations DESC
    LIMIT {limit}
    """


# -----------------------------------------------------------------------------
# Score outliers + perfect-100 wash patterns (Tab 4 drill-downs)
# -----------------------------------------------------------------------------

def q_score_outliers(threshold: float = 100.0) -> str:
    """Individual feedbacks with score > threshold — score decoding artifacts."""
    return f"""
    WITH {REPUTATION_BASE_CTE}
    SELECT
      block_timestamp,
      agent_id,
      client,
      score,
      transaction_hash
    FROM reputation_base
    WHERE score > {threshold}
    ORDER BY score DESC
    """


# -----------------------------------------------------------------------------
# x402 claim vs reality — joins token_transfers
# -----------------------------------------------------------------------------

def q_x402_claim_vs_reality() -> str:
    """How many x402=true owners actually received any ERC-20 / USDC transfer?

    Returns a single row with the headline gap: claim vs actually received.
    Partition cut on token_transfers keeps the scan inside the free tier.
    """
    return f"""
    WITH {IDENTITY_BASE_CTE},
    inline AS (
      SELECT owner, {INLINE_JSON_EXPR} AS card_json
      FROM identity_base
      WHERE STARTS_WITH(agent_uri, 'data:application/json;base64,')
    ),
    x402_true_owners AS (
      SELECT DISTINCT owner FROM inline WHERE {X402_VALUE_EXPR} = 'true'
    ),
    received AS (
      SELECT
        to_address AS owner,
        COUNT(*) AS n_transfers,
        COUNTIF(LOWER(address) = '{USDC_ADDRESS}') AS n_usdc,
        SUM(IF(LOWER(address) = '{USDC_ADDRESS}',
               SAFE_CAST(quantity AS NUMERIC) / 1e6, 0)) AS usdc_amount
      FROM {TOKEN_TRANSFERS}
      WHERE block_timestamp >= {PARTITION_CUT}
        AND event_type = 'ERC-20'
        AND to_address IN (SELECT owner FROM x402_true_owners)
      GROUP BY to_address
    )
    SELECT
      (SELECT COUNT(*) FROM x402_true_owners) AS n_x402_true_owners,
      COUNT(*) AS n_owners_received_any_erc20,
      COUNTIF(n_usdc > 0) AS n_owners_received_usdc,
      SUM(n_transfers) AS total_erc20_transfers,
      SUM(n_usdc) AS total_usdc_transfers,
      ROUND(SUM(usdc_amount), 2) AS total_usdc_amount
    FROM received
    """


# -----------------------------------------------------------------------------
# Rated + x402 — agents that received feedback AND claim x402 support
# (the missing funnel stage between "claims x402" and "received USDC")
# -----------------------------------------------------------------------------

def q_rated_x402_count() -> str:
    """Distinct agents that (a) received at least one NewFeedback event AND
    (b) carry an inline card with x402Support=true. The handoff §B Q4
    inner-join shape — matches the user's GIST."""
    return f"""
    WITH {DECODED_IDENTITY_CTE},
    rated_agents AS (
      SELECT DISTINCT SAFE_CAST(topics[SAFE_OFFSET(1)] AS INT64) AS agent_id
      FROM {LOGS}
      WHERE address = '{REPUTATION_REGISTRY}'
        AND topics[SAFE_OFFSET(0)] = '{SIG_NEW_FEEDBACK}'
        AND block_timestamp >= {PARTITION_CUT}
    )
    SELECT COUNT(DISTINCT d.agent_id) AS n_rated_x402
    FROM decoded d
    WHERE {X402_VALUE_EXPR} = 'true'
      AND d.agent_id IN (SELECT agent_id FROM rated_agents)
    """


# -----------------------------------------------------------------------------
# Owner deep-dive — what is inside one wallet's agent pool?
# -----------------------------------------------------------------------------

def q_agent_search(
    agent_id: int | None = None,
    owner: str | None = None,
    name_contains: str | None = None,
    description_contains: str | None = None,
    min_unique_clients: int | None = None,
    min_avg_score: float | None = None,
    x402_only: bool = False,
    has_services: bool = False,
    limit: int = 100,
) -> str:
    """Free-form filter over inline cards joined with reputation aggregates.
    Any param left as None / False is skipped."""
    where = []
    if agent_id is not None:
        where.append(f"d.agent_id = {int(agent_id)}")
    if owner:
        where.append(f"d.owner = '{owner.lower()}'")
    if name_contains:
        safe = name_contains.replace("'", "")
        where.append(f"LOWER(JSON_VALUE(d.card_json, '$.name')) LIKE '%{safe.lower()}%'")
    if description_contains:
        safe = description_contains.replace("'", "")
        where.append(f"LOWER(JSON_VALUE(d.card_json, '$.description')) LIKE '%{safe.lower()}%'")
    if x402_only:
        where.append(f"{X402_VALUE_EXPR} = 'true'")
    if has_services:
        where.append("ARRAY_LENGTH(JSON_QUERY_ARRAY(d.card_json, '$.services')) > 0")
    where_clause = " AND ".join(where) if where else "TRUE"

    having = []
    if min_unique_clients is not None:
        having.append(f"COUNT(DISTINCT r.client) >= {int(min_unique_clients)}")
    if min_avg_score is not None:
        having.append(f"AVG(r.score) >= {float(min_avg_score)}")
    having_clause = ("HAVING " + " AND ".join(having)) if having else ""

    return f"""
    WITH {DECODED_IDENTITY_CTE},
    {REPUTATION_BASE_CTE}
    SELECT
      d.agent_id,
      JSON_VALUE(d.card_json, '$.name') AS name,
      SUBSTR(JSON_VALUE(d.card_json, '$.description'), 1, 100) AS description,
      d.owner,
      ARRAY_LENGTH(JSON_QUERY_ARRAY(d.card_json, '$.services')) AS n_services,
      {X402_VALUE_EXPR} AS x402,
      COUNT(r.score) AS n_feedbacks,
      COUNT(DISTINCT r.client) AS unique_clients,
      ROUND(AVG(r.score), 2) AS avg_score
    FROM decoded d
    LEFT JOIN reputation_base r ON r.agent_id = d.agent_id
    WHERE {where_clause}
    GROUP BY d.agent_id, d.card_json, d.owner
    {having_clause}
    ORDER BY avg_score DESC NULLS LAST, unique_clients DESC NULLS LAST
    LIMIT {int(limit)}
    """


def q_trustworthy_payable(
    min_unique_clients: int = 3,
    min_avg_score: float = 80.0,
) -> str:
    """The one view that answers the prize statement directly:
    'rank agents by feedback AND reputation, highlight x402, discover
    trustworthy + payable.'

    Intersection of:
      - passes the Sybil bar (unique_clients >= 3)
      - decent average score (>= 80)
      - card claims x402Support = true
      - owner has received at least one ERC-20 transfer (real economic activity)
      - bonus: owner received USDC
    """
    return f"""
    WITH {DECODED_IDENTITY_CTE},
    {REPUTATION_BASE_CTE},
    rep_summary AS (
      SELECT
        agent_id,
        COUNT(*) AS n_feedbacks,
        COUNT(DISTINCT client) AS unique_clients,
        ROUND(AVG(score), 2) AS avg_score
      FROM reputation_base
      WHERE score IS NOT NULL
      GROUP BY agent_id
      HAVING COUNT(DISTINCT client) >= {min_unique_clients}
         AND AVG(score) >= {min_avg_score}
    ),
    candidate AS (
      SELECT
        d.agent_id,
        d.owner,
        JSON_VALUE(d.card_json, '$.name') AS name,
        SUBSTR(JSON_VALUE(d.card_json, '$.description'), 1, 80) AS description,
        ARRAY_LENGTH(JSON_QUERY_ARRAY(d.card_json, '$.services')) AS n_services,
        r.n_feedbacks, r.unique_clients, r.avg_score
      FROM decoded d
      JOIN rep_summary r USING (agent_id)
      WHERE {X402_VALUE_EXPR} = 'true'
    ),
    owner_money AS (
      SELECT
        to_address AS owner,
        COUNT(*) AS n_erc20_transfers,
        COUNTIF(LOWER(address) = '{USDC_ADDRESS}') AS n_usdc_transfers,
        SUM(IF(LOWER(address) = '{USDC_ADDRESS}',
               SAFE_CAST(quantity AS NUMERIC) / 1e6, 0)) AS usdc_amount
      FROM {TOKEN_TRANSFERS}
      WHERE block_timestamp >= {PARTITION_CUT}
        AND event_type = 'ERC-20'
        AND to_address IN (SELECT DISTINCT owner FROM candidate)
      GROUP BY owner
    )
    SELECT
      c.agent_id, c.name, c.description, c.owner,
      c.unique_clients, c.avg_score, c.n_feedbacks, c.n_services,
      COALESCE(m.n_erc20_transfers, 0) AS n_erc20_transfers,
      COALESCE(m.n_usdc_transfers, 0) AS n_usdc_transfers,
      ROUND(COALESCE(m.usdc_amount, 0), 2) AS usdc_amount
    FROM candidate c
    LEFT JOIN owner_money m USING (owner)
    ORDER BY
      (CASE WHEN m.n_usdc_transfers > 0 THEN 1 ELSE 0 END) DESC,
      c.avg_score DESC,
      c.unique_clients DESC
    """


def q_owner_deep_dive(owner_address: str) -> str:
    """Scheme / x402 / feedback / nftOrigin distribution within one owner's
    registered agents. Designed for the top-1 wallet (0xd5d6d96…) which
    alone owns 9,967 agents."""
    owner = owner_address.lower()
    return f"""
    WITH {DECODED_IDENTITY_CTE},
    owned AS (
      SELECT * FROM decoded WHERE owner = '{owner}'
    ),
    rated AS (
      SELECT DISTINCT SAFE_CAST(topics[SAFE_OFFSET(1)] AS INT64) AS agent_id
      FROM {LOGS}
      WHERE address = '{REPUTATION_REGISTRY}'
        AND topics[SAFE_OFFSET(0)] = '{SIG_NEW_FEEDBACK}'
        AND block_timestamp >= {PARTITION_CUT}
        AND SAFE_CAST(topics[SAFE_OFFSET(1)] AS INT64) IN (
          SELECT agent_id FROM owned
        )
    )
    SELECT
      COUNT(*) AS n_agents,
      COUNTIF(agent_uri IS NULL OR agent_uri = '') AS n_no_uri,
      COUNTIF(STARTS_WITH(agent_uri, 'data:application/json;base64,')) AS n_inline_base64,
      COUNTIF(STARTS_WITH(agent_uri, 'https://') OR STARTS_WITH(agent_uri, 'http://')) AS n_http,
      COUNTIF(STARTS_WITH(agent_uri, 'ipfs://')) AS n_ipfs,
      COUNTIF(card_json IS NOT NULL) AS n_has_card,
      COUNTIF({X402_VALUE_EXPR} = 'true') AS n_x402_true,
      COUNTIF(ARRAY_LENGTH(JSON_QUERY_ARRAY(card_json, '$.services')) > 0) AS n_functional,
      COUNTIF(JSON_VALUE(card_json, '$.nftOrigin.contract') IS NOT NULL) AS n_nft_origin,
      (SELECT COUNT(*) FROM rated) AS n_rated_in_owner,
      MIN(block_timestamp) AS first_registration,
      MAX(block_timestamp) AS last_registration
    FROM owned
    """


def q_perfect_100_clients(min_feedbacks: int = 5, limit: int = 20) -> str:
    """Clients whose entire feedback history is score=100. Strong wash signal."""
    return f"""
    WITH {REPUTATION_BASE_CTE},
    per_client AS (
      SELECT
        client,
        COUNT(*) AS n_feedbacks,
        COUNTIF(score = 100) AS n_perfect_100,
        COUNT(DISTINCT agent_id) AS n_agents,
        COUNT(DISTINCT feedback_uri_hash) AS n_distinct_uri_hashes
      FROM reputation_base
      WHERE score IS NOT NULL
      GROUP BY client
    )
    SELECT
      client,
      n_feedbacks,
      n_perfect_100,
      n_agents,
      n_distinct_uri_hashes
    FROM per_client
    WHERE n_feedbacks >= {min_feedbacks}
      AND n_perfect_100 = n_feedbacks
    ORDER BY n_feedbacks DESC
    LIMIT {limit}
    """


def q4_feedback_uri_collisions(limit: int = 15) -> str:
    """Inverse of Q4: which feedbackURI hashes are shared by multiple clients
    on multiple agents? This catches Sybil campaigns the unique_clients
    barrier misses."""
    return f"""
    WITH {REPUTATION_BASE_CTE}
    SELECT
      feedback_uri_hash,
      COUNT(*) AS feedback_count,
      COUNT(DISTINCT client) AS distinct_clients,
      COUNT(DISTINCT agent_id) AS distinct_agents
    FROM reputation_base
    GROUP BY feedback_uri_hash
    HAVING COUNT(*) > 1
    ORDER BY feedback_count DESC
    LIMIT {limit}
    """
