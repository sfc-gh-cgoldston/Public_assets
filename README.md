# Axios — Reporter Intelligence Engine (RIE) Cost Estimator

An interactive Streamlit app for estimating Snowflake infrastructure costs for the **Reporter Intelligence Engine (RIE)** — Axios's AI-powered newsroom assistant that surfaces story signals, audience intelligence, and reporter productivity insights.

## Overview

This estimator models the 7 core Snowflake service components of the RIE architecture:

| Tab | Service | Billing Model |
|-----|---------|---------------|
| Snowpipe | Snowpipe Streaming | Credits per GB ingested |
| Storage | Optimized Storage | $/TB/month |
| Dynamic Tables | Pipeline compute | Warehouse credits |
| Cortex Search | Hybrid search index | Credits per 1M tokens |
| ML Models | Forecasting & anomaly detection | Warehouse credits |
| LLM / Agent | Cortex LLM inference | Credits per 1M tokens |
| Warehouse | Analyst/BI query compute + egress | Credits/hour + $/GB |

## Running Locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

The app runs on `http://localhost:8501` by default.

## Configuration

All pricing inputs are adjustable in the app UI. Key global settings in the sidebar:

- **Credit cost ($/credit)** — Set to Axios's contracted rate (default: $1.89)
- **Storage cost ($/TB/month)** — Default: $23.00 (Snowflake list price)
- **Scenario Presets** — Conservative / Expected / Aggressive starting points

Individual tabs contain sliders for workload parameters (data volume, query rates, model counts, etc.). All costs update live as you adjust inputs.

## Cost Summary

The top of the page shows a live rollup across all 7 components:
- Monthly and annual totals
- Per-component breakdown table
- Bar chart by service

## Pricing Assumptions

- Snowpipe Streaming: 3.7 credits/TB (0.0037 credits/GB) of uncompressed data
- Cortex Search: ~0.033 credits/1M tokens (index and query)
- LLM: Credit rates per model (e.g., claude-sonnet-4-6: 1.65 input / 8.25 output credits/1M tokens)
- Warehouse sizes: XS=1, S=2, M=4, L=8, XL=16, 2XL=32, 3XL=64 credits/hour
- Egress: $0.01/GB (same-region), $0.09/GB (cross-region)

All estimates use Snowflake list pricing as a baseline. Actual costs depend on contracted rates, Snowflake edition, and cloud region.

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub (public or private)
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select this repo → set main file to `streamlit_app.py`
4. Deploy — Streamlit provides a shareable URL

## Project Structure

```
axios-rie-cost-estimator/
├── streamlit_app.py        # Main application
├── requirements.txt        # Python dependencies
├── .streamlit/
│   └── config.toml         # Snowflake theme (colors, font)
└── README.md
```
