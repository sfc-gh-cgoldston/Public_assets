import streamlit as st
import pandas as pd

st.set_page_config(
    page_title="Axios RIE Cost Estimator",
    page_icon=":material/calculate:",
    layout="wide",
)

st.html("""
<style>
  /* Larger base font for readability */
  .stApp, .stApp p, .stApp li { font-size: 16px !important; }
  /* Widget labels */
  .stSlider label, .stNumberInput label,
  .stSelectbox label, .stCheckbox label,
  .stRadio label { font-size: 15px !important; font-weight: 500; }
  /* Subheaders and section titles */
  .stApp h2 { font-size: 1.6rem !important; }
  .stApp h3 { font-size: 1.3rem !important; }
  /* Metric values bigger */
  [data-testid="stMetricValue"] { font-size: 2rem !important; }
  [data-testid="stMetricLabel"] { font-size: 0.9rem !important; font-weight: 500; }
  /* Tab labels */
  .stTabs [data-baseweb="tab"] { font-size: 14px !important; padding: 8px 14px; }
  /* Sidebar labels */
  .stSidebar .stMarkdown h2 { font-size: 1.3rem !important; }
  .stSidebar .stMarkdown h3 { font-size: 1.1rem !important; }
  .stSidebar label { font-size: 14px !important; }
  /* Caption text */
  .stCaption, [data-testid="stCaptionContainer"] { font-size: 14px !important; }
</style>
""")

# ─── HELPERS ─────────────────────────────────────────────────────────────────

def warehouse_credits_per_hour(size: str) -> float:
    return {"XS": 1, "S": 2, "M": 4, "L": 8, "XL": 16, "2XL": 32, "3XL": 64}.get(size, 1)

def fmt_usd(v: float) -> str:
    return f"${v:,.0f}"

def fmt_credits(v: float) -> str:
    return f"{v:,.1f}"

# ─── SIDEBAR: GLOBAL SETTINGS ────────────────────────────────────────────────

with st.sidebar:
    st.markdown("## Global Settings")

    credit_cost = st.number_input(
        "Credit cost ($/credit)",
        min_value=1.0, max_value=10.0, value=1.89, step=0.01,
        help="Snowflake on-demand list price is ~$2–4/credit depending on edition & region. Adjust for contracted rate.",
    )

    storage_cost_per_tb = st.number_input(
        "Storage cost ($/TB/month)",
        min_value=5.0, max_value=50.0, value=23.00, step=1.0,
    )

    st.markdown("---")
    st.markdown("### Scenario Presets")
    scenario = st.selectbox(
        "Load scenario",
        ["Custom", "Conservative", "Expected", "Aggressive"],
        index=0,
        help="Presets adjust slider defaults as a starting point.",
    )

    scenario_defaults = {
        "Conservative": dict(rows_per_sec=500, retention=6, num_models=5, agent_calls=200),
        "Expected":     dict(rows_per_sec=2000, retention=12, num_models=15, agent_calls=1000),
        "Aggressive":   dict(rows_per_sec=10000, retention=24, num_models=40, agent_calls=10000),
        "Custom":       dict(rows_per_sec=1000, retention=12, num_models=10, agent_calls=500),
    }
    sd = scenario_defaults[scenario]

    st.markdown("---")
    st.caption("All estimates use Snowflake list pricing. Adjust the credit cost above to reflect contracted rates.")

# ─── HEADER ──────────────────────────────────────────────────────────────────

st.markdown("# Axios — Reporter Intelligence Engine (RIE)")
st.markdown("### Snowflake Cost Estimator")
st.caption(
    "Adjust variables in each tab to model infrastructure costs. "
    "Monthly and annual totals update in real time."
)

summary_slot = st.empty()
st.markdown("---")

# ─── TABS ─────────────────────────────────────────────────────────────────────

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "Snowpipe",
    "Storage",
    "Dynamic Tables",
    "Cortex Search",
    "ML Models",
    "LLM / Agent",
    "Warehouse",
])

# ─── TAB 1: SNOWPIPE STREAMING ───────────────────────────────────────────────

with tab1:
    st.subheader("Snowpipe Streaming Ingestion")
    st.caption("5 external sources ingested continuously via Snowpipe Streaming.")

    c1, c2 = st.columns(2)
    with c1:
        num_sources = st.slider("Number of streaming sources", 1, 10, 5)
        avg_rows_per_sec = st.slider(
            "Avg rows/second per source", 100, 100_000, sd["rows_per_sec"], step=100,
        )
        avg_row_bytes = st.slider("Avg row size (bytes)", 100, 10_000, 500, step=100)
        ingestion_hours_per_day = st.slider("Active ingestion hours/day", 1, 24, 24)
        streaming_credit_rate = st.number_input(
            "Credits per GB ingested (Snowpipe Streaming)",
            min_value=0.0001, max_value=5.0, value=0.0037, step=0.0001,
            format="%.4f",
            help="Snowpipe Streaming serverless billing: 3.7 credits/TB = 0.0037 credits/GB of uncompressed data ingested.",
        )

    gb_per_source_per_day = (avg_rows_per_sec * avg_row_bytes * ingestion_hours_per_day * 3600) / 1e9
    total_gb_per_day = gb_per_source_per_day * num_sources
    snowpipe_credits_monthly = total_gb_per_day * streaming_credit_rate * 30
    snowpipe_cost_monthly = snowpipe_credits_monthly * credit_cost

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("GB/day per source", f"{gb_per_source_per_day:,.2f}")
            st.metric("Total GB/day (all sources)", f"{total_gb_per_day:,.2f}")
            st.metric("Total GB/month", f"{total_gb_per_day * 30:,.1f}")
            st.metric("Credits/month", fmt_credits(snowpipe_credits_monthly))
            st.metric("Monthly cost", fmt_usd(snowpipe_cost_monthly))

# ─── TAB 2: STORAGE ──────────────────────────────────────────────────────────

with tab2:
    st.subheader("Storage")
    st.caption("Raw ingested data, transformed tables, ML feature tables, and document stores.")

    c1, c2 = st.columns(2)
    with c1:
        raw_gb_per_day = st.number_input("Raw data growth (GB/day)", 1.0, 50_000.0, 50.0, step=1.0)
        retention_months = st.slider("Data retention (months)", 1, 36, sd["retention"])
        compression_ratio = st.slider(
            "Compression ratio", 1.0, 10.0, 3.0, step=0.5,
            help="Snowflake typically achieves 3x–7x compression on structured data.",
        )
        processed_multiplier = st.slider(
            "Derived data multiplier",
            0.5, 5.0, 1.5, step=0.1,
            help="Dynamic table outputs, ML feature tables, aggregations relative to compressed raw.",
        )
        doc_store_gb = st.number_input(
            "Document store size (GB — gov't transcripts etc.)", 0.0, 50_000.0, 200.0,
        )

    raw_total_gb = raw_gb_per_day * 30 * retention_months
    compressed_gb = raw_total_gb / compression_ratio
    processed_gb = compressed_gb * processed_multiplier
    total_storage_gb = compressed_gb + processed_gb + doc_store_gb
    total_storage_tb = total_storage_gb / 1024
    storage_cost_monthly = total_storage_tb * storage_cost_per_tb

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("Raw data accumulated (compressed)", f"{compressed_gb:,.0f} GB")
            st.metric("Derived/processed data", f"{processed_gb:,.0f} GB")
            st.metric("Documents", f"{doc_store_gb:,.0f} GB")
            st.metric("Total storage", f"{total_storage_gb:,.0f} GB  ({total_storage_tb:.2f} TB)")
            st.metric("Monthly cost", fmt_usd(storage_cost_monthly))

# ─── TAB 3: DYNAMIC TABLES ───────────────────────────────────────────────────

with tab3:
    st.subheader("Dynamic Tables / Transformation Pipeline")
    st.caption("Automated pipeline from raw ingest → clean → feature tables for ML input.")

    c1, c2 = st.columns(2)
    with c1:
        num_dt_layers = st.slider("Number of pipeline layers", 1, 5, 3)
        num_dts_per_layer = st.slider("Avg dynamic tables per layer", 1, 30, 5)
        dt_wh_size = st.selectbox("Refresh warehouse size", ["XS", "S", "M", "L", "XL"], index=1)
        avg_refresh_sec = st.slider("Avg refresh runtime per DT (seconds)", 5, 3600, 30)

        st.markdown("**Target lag per layer:**")
        layer_lags = []
        default_lags = [5, 15, 60, 240, 1440]
        for i in range(num_dt_layers):
            lag = st.slider(
                f"Layer {i+1} target lag (minutes)", 1, 1440,
                default_lags[min(i, 4)], key=f"dt_lag_{i}",
            )
            layer_lags.append(lag)

    dt_cph = warehouse_credits_per_hour(dt_wh_size)
    dt_credits_monthly = 0.0
    for lag in layer_lags:
        refreshes_per_day = (24 * 60) / lag
        dt_credits_monthly += (refreshes_per_day * num_dts_per_layer * (avg_refresh_sec / 3600)) * dt_cph * 30

    dt_cost_monthly = dt_credits_monthly * credit_cost

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("Total dynamic tables", num_dt_layers * num_dts_per_layer)
            st.metric("Warehouse credits/hour", f"{dt_cph:.0f}  ({dt_wh_size})")
            st.metric("Credits/month", fmt_credits(dt_credits_monthly))
            st.metric("Monthly cost", fmt_usd(dt_cost_monthly))

# ─── TAB 4: CORTEX SEARCH ────────────────────────────────────────────────────

with tab4:
    st.subheader("Cortex Search")
    st.caption("Vector embeddings and semantic search over government transcripts and document stores.")

    c1, c2 = st.columns(2)
    with c1:
        num_docs = st.number_input("Total documents to index", 100, 10_000_000, 50_000, step=1_000)
        avg_doc_words = st.slider("Avg words per document", 100, 50_000, 5_000, step=500)
        monthly_reindex_pct = st.slider(
            "% of corpus re-indexed per month (new/updated docs)", 0, 100, 10,
        )
        search_queries_per_day = st.slider("Search queries per day", 0, 500_000, 500, step=100)
        cs_index_cost_per_1m_tokens = st.number_input(
            "Index cost ($/1M tokens)", 0.01, 10.0, 0.10, step=0.01,
            help="Approximate Cortex Search indexing cost — confirm with Snowflake pricing.",
        )
        cs_query_cost_per_1k = st.number_input(
            "Query cost ($/1K queries)", 0.001, 5.0, 0.001, step=0.001, format="%.4f",
        )

    tokens_per_word = 1.3
    total_tokens_m = num_docs * avg_doc_words * tokens_per_word / 1e6
    reindex_tokens_m = total_tokens_m * (monthly_reindex_pct / 100)
    cs_index_cost = reindex_tokens_m * cs_index_cost_per_1m_tokens
    cs_query_cost = (search_queries_per_day * 30 / 1_000) * cs_query_cost_per_1k
    cortex_search_cost_monthly = cs_index_cost + cs_query_cost

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("Total corpus tokens (M)", f"{total_tokens_m:,.1f}")
            st.metric("Monthly re-index tokens (M)", f"{reindex_tokens_m:,.1f}")
            st.metric("Monthly index cost", f"${cs_index_cost:,.2f}")
            st.metric("Monthly query cost", f"${cs_query_cost:,.4f}")
            st.metric("Monthly total", fmt_usd(cortex_search_cost_monthly))
        st.caption("Cortex Search pricing: confirm current rates at docs.snowflake.com")

# ─── TAB 5: ML MODELS ────────────────────────────────────────────────────────

with tab5:
    st.subheader("ML Model Compute")
    st.caption(
        "Anomaly detection, forecasting, and trend models. "
        "Warehouse-based compute — Cortex ML or custom models run on Snowpark."
    )

    c1, c2 = st.columns(2)
    with c1:
        num_models = st.slider("Total number of ML models", 1, 100, sd["num_models"])
        ml_wh_size = st.selectbox(
            "ML warehouse size", ["XS", "S", "M", "L", "XL", "2XL"], index=2, key="ml_wh",
        )
        avg_model_runtime_min = st.slider("Avg model runtime (minutes)", 1, 480, 30)

        st.markdown("**Frequency distribution of model runs:**")
        pct_hourly  = st.slider("% of models — hourly", 0, 100, 10)
        pct_daily   = st.slider("% of models — daily",  0, 100, 50)
        pct_weekly  = st.slider("% of models — weekly", 0, 100, 30)
        pct_monthly_r = st.slider("% of models — monthly", 0, 100, 10)

    ml_cph = warehouse_credits_per_hour(ml_wh_size)
    runtime_h = avg_model_runtime_min / 60

    runs_per_month = (
        num_models * (pct_hourly  / 100) * 24 * 30
        + num_models * (pct_daily   / 100) * 30
        + num_models * (pct_weekly  / 100) * 4
        + num_models * (pct_monthly_r / 100) * 1
    )
    ml_credits_monthly = runs_per_month * runtime_h * ml_cph
    ml_cost_monthly = ml_credits_monthly * credit_cost

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("Est. model runs/month", f"{runs_per_month:,.0f}")
            st.metric("Warehouse credits/hour", f"{ml_cph:.0f}  ({ml_wh_size})")
            st.metric("Credits/month", fmt_credits(ml_credits_monthly))
            st.metric("Monthly cost", fmt_usd(ml_cost_monthly))
        st.info(
            "Tip: models with different audiences (editorial vs. business) "
            "may run at different frequencies and on different warehouse sizes. "
            "Duplicate this estimate per model group for finer granularity."
        )

# ─── TAB 6: LLM / AGENT ──────────────────────────────────────────────────────

with tab6:
    st.subheader("LLM & Agent Inference")
    st.caption(
        "Pre-seeded agent calls using the ML-generated dataset. "
        "Supports both Snowflake Cortex and external OpenAI."
    )

    c1, c2 = st.columns(2)
    with c1:
        llm_provider = st.selectbox(
            "LLM provider",
            ["Snowflake Cortex", "OpenAI API (external)"],
        )
        agent_calls_per_day = st.slider(
            "Agent invocations per day", 0, 500_000, sd["agent_calls"], step=100,
        )
        avg_input_tokens  = st.slider("Avg input tokens per call",  100, 200_000, 5_000, step=100)
        avg_output_tokens = st.slider("Avg output tokens per call",  50,  20_000,   500, step=50)

        CORTEX_MODELS = {
            "claude-sonnet-4-6":       dict(input_cr=1.65, output_cr=8.25),
            "claude-4-sonnet":         dict(input_cr=1.50, output_cr=7.50),
            "snowflake-llama-3.3-70b": dict(input_cr=0.29, output_cr=0.29),
            "llama3.1-70b":            dict(input_cr=1.21, output_cr=1.21),
            "llama3.1-405b":           dict(input_cr=3.00, output_cr=3.00),
            "mistral-large2":          dict(input_cr=1.95, output_cr=1.95),
        }

        if llm_provider == "Snowflake Cortex":
            cortex_model = st.selectbox("Cortex model", list(CORTEX_MODELS.keys()))
            m = CORTEX_MODELS[cortex_model]
            input_cost_per_1m  = m["input_cr"]  * credit_cost
            output_cost_per_1m = m["output_cr"] * credit_cost
            st.caption(
                f"At ${credit_cost:.2f}/credit → "
                f"Input: ${input_cost_per_1m:.3f}/1M tokens | "
                f"Output: ${output_cost_per_1m:.3f}/1M tokens"
            )
            is_external_llm = False
        else:
            st.info(
                "OpenAI costs are billed outside Snowflake. "
                "Included here for a complete total-cost view."
            )
            input_cost_per_1m  = st.number_input("OpenAI input $/1M tokens",  0.01, 100.0,  5.00, step=0.10)
            output_cost_per_1m = st.number_input("OpenAI output $/1M tokens", 0.01, 100.0, 15.00, step=0.10)
            is_external_llm = True

    total_input_tokens_m_monthly  = agent_calls_per_day * 30 * avg_input_tokens  / 1e6
    total_output_tokens_m_monthly = agent_calls_per_day * 30 * avg_output_tokens / 1e6
    llm_cost_monthly = (
        total_input_tokens_m_monthly  * input_cost_per_1m
        + total_output_tokens_m_monthly * output_cost_per_1m
    )

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("Input tokens/month (M)", f"{total_input_tokens_m_monthly:,.2f}")
            st.metric("Output tokens/month (M)", f"{total_output_tokens_m_monthly:,.2f}")
            st.metric("Monthly cost", fmt_usd(llm_cost_monthly))
            if is_external_llm:
                st.warning("Billed by OpenAI — not a Snowflake credit charge.")

# ─── TAB 7: WAREHOUSE & EGRESS ───────────────────────────────────────────────

with tab7:
    st.subheader("General Warehouse Compute & Data Egress")
    st.caption(
        "Ad-hoc analyst queries and data pushed to internal Postgres after ML runs."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Analyst / Query Warehouse**")
        q_wh_size = st.selectbox("Warehouse size", ["XS", "S", "M", "L", "XL"], index=1, key="qwh")
        q_wh_hours_per_day = st.slider("Active hours/day", 0.5, 24.0, 8.0, step=0.5)
        auto_suspend_eff = st.slider(
            "Auto-suspend efficiency (%)", 10, 90, 50,
            help="Estimated % of scheduled hours the warehouse is actually consuming credits (not idle/suspended).",
        )

        st.markdown("**Egress to Postgres**")
        egress_gb_per_run = st.number_input("GB per ML-to-Postgres push", 0.0, 1_000.0, 5.0)
        egress_runs_per_day = st.slider("Pushes per day", 0, 200, 4)
        is_cross_region = st.checkbox(
            "Cross-region egress",
            help="Same-region AWS data transfer ~$0.01/GB; cross-region ~$0.09/GB.",
        )

    q_cph = warehouse_credits_per_hour(q_wh_size)
    effective_hours = q_wh_hours_per_day * (auto_suspend_eff / 100)
    query_credits_monthly = effective_hours * q_cph * 30
    query_cost_monthly = query_credits_monthly * credit_cost

    egress_rate = 0.09 if is_cross_region else 0.01
    egress_gb_monthly = egress_gb_per_run * egress_runs_per_day * 30
    egress_cost_monthly = egress_gb_monthly * egress_rate

    with c2:
        with st.container(border=True):
            st.markdown("**Estimates**")
            st.metric("Effective warehouse hours/day", f"{effective_hours:.1f}")
            st.metric("Query warehouse credits/month", fmt_credits(query_credits_monthly))
            st.metric("Query cost/month", fmt_usd(query_cost_monthly))
            st.metric("Egress GB/month", f"{egress_gb_monthly:,.1f}")
            st.metric("Egress cost/month", f"${egress_cost_monthly:,.2f}")

# ─── SUMMARY SECTION ─────────────────────────────────────────────────────────

snowflake_components = {
    "Snowpipe Streaming":         snowpipe_cost_monthly,
    "Storage":                    storage_cost_monthly,
    "Dynamic Tables":             dt_cost_monthly,
    "Cortex Search":              cortex_search_cost_monthly,
    "ML Model Compute":           ml_cost_monthly,
    "LLM / Agent (Snowflake)":    llm_cost_monthly if not is_external_llm else 0.0,
    "Query Warehouse":            query_cost_monthly,
    "Data Egress":                egress_cost_monthly,
}

external_components = {
    "OpenAI API (external)": llm_cost_monthly if is_external_llm else 0.0,
}
external_components = {k: v for k, v in external_components.items() if v > 0}

total_snowflake_monthly = sum(snowflake_components.values())
total_external_monthly  = sum(external_components.values())
total_monthly = total_snowflake_monthly + total_external_monthly

with summary_slot.container():
    st.markdown("## Cost Summary")

    with st.container(horizontal=True):
        st.metric("Snowflake Monthly",  fmt_usd(total_snowflake_monthly), border=True)
        st.metric("Snowflake Annual",   fmt_usd(total_snowflake_monthly * 12), border=True)
        if external_components:
            st.metric("OpenAI Monthly",  fmt_usd(total_external_monthly), border=True)
            st.metric("OpenAI Annual",   fmt_usd(total_external_monthly * 12), border=True)
        st.metric("Total Monthly",  fmt_usd(total_monthly), border=True)
        st.metric("Total Annual",   fmt_usd(total_monthly * 12), border=True)

    st.markdown("---")

    all_components = {**snowflake_components, **external_components}
    active = {k: v for k, v in all_components.items() if v > 0}

    if active:
        col_a, col_b = st.columns(2)
        with col_a:
            df_breakdown = pd.DataFrame({
                "Component":    list(active.keys()),
                "Monthly ($)":  [f"${v:,.0f}" for v in active.values()],
                "Annual ($)":   [f"${v * 12:,.0f}" for v in active.values()],
                "% of Total":   [
                    f"{(v / total_monthly * 100):.1f}%" if total_monthly > 0 else "—"
                    for v in active.values()
                ],
            })
            with st.container(border=True):
                st.markdown("**Cost Breakdown by Component**")
                st.dataframe(df_breakdown, hide_index=True, use_container_width=True)

        with col_b:
            df_chart = (
                pd.DataFrame({"Component": list(active.keys()), "Monthly Cost": list(active.values())})
                .sort_values("Monthly Cost", ascending=False)
            )
            with st.container(border=True):
                st.markdown("**Monthly Cost Distribution**")
                st.bar_chart(df_chart, x="Component", y="Monthly Cost", use_container_width=True)

    st.caption(
        "Estimates use Snowflake list pricing as of 2025. "
        "Actual costs depend on contracted rates, Snowflake edition (Standard/Enterprise/Business Critical), "
        "cloud region, and workload efficiency. Consult your Snowflake account team for a formal quote."
    )
