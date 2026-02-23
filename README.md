# ADO 1% - Hungarian Tax 1% Donation Analysis

Interactive dashboard analyzing Hungary's personal income tax 1% donation system, where taxpayers can direct 1% of their income tax to a civil organization of their choice.

**Live site: [ado1stat.hu](https://ado1stat.hu)**

## What is this?

In Hungary, every taxpayer can donate 1% of their personal income tax to a registered civil organization. In 2025, **1.83 million people** donated a total of **20.3 billion HUF** (~50 million EUR) to over 37,000 organizations.

This project visualizes the top 10,000 recipient organizations (covering 88% of all donations) through interactive charts:

- **Map** - Geographic distribution of organizations across Hungary
- **Sunburst chart** - Hierarchical category breakdown (click to drill down)
- **Time series (per org)** - Yearly donation trends for individual organizations
- **Time series (per category)** - Aggregated category trends over the years
- **Scatter plot** - Donation amount vs estimated average donor salary
- **City search** - Find organizations near any Hungarian city

## How it was built

This was a hobby project built over **two weekends**, almost entirely with AI-assisted coding ("vibe coding") using [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

The pipeline:
1. **Scraping** - Automated data collection from [civil.info.hu](https://civil.info.hu) for 10,000 organizations
2. **Classification** - LLM-based categorization of organizations into ~55 subcategories using Claude Haiku API
3. **Visualization** - Interactive Plotly Dash dashboard
4. **Deployment** - Self-hosted on a small VPS

Total project cost: ~40,750 HUF (~100 EUR) including API calls, hosting, and domain.

## Tech stack

- **Dashboard**: Python, [Plotly Dash](https://dash.plotly.com/), Dash Bootstrap Components
- **Scraping**: Python, Playwright (headless browser)
- **Classification**: Claude API (Haiku model)
- **Server**: Gunicorn + Nginx on a Hetzner VPS
- **AI assistant**: Claude Code (Sonnet 4.5) for all coding tasks

## Project structure

```
scripts/
  scraping/          # Web scrapers for civil.info.hu
  classification/    # LLM-based organization categorization
  visualization/     # Dashboard app (dashboard_app.py is the main file)
  fixes/             # Data cleaning and correction scripts
data/                # Scraped data, categories CSV, city data
organizations_by_adoszam/  # Per-organization JSON files (10,000)
pages/               # Markdown content for info pages
imgs/                # Images for the fun facts page
```

## Running locally

```bash
pip install -r requirements.txt
python scripts/visualization/dashboard_app.py
```

The dashboard will be available at `http://localhost:8092/`.

## Data sources

- **[NAV](https://nav.gov.hu)** - Official list of civil organizations receiving tax 1% donations (2025)
- **[civil.info.hu](https://civil.info.hu)** - Organization details (address, mission statement) and historical donation data

All data used is publicly available.

## License

See [LICENSE](LICENSE) file.
