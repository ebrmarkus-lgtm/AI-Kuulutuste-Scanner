# AI Kuulutuste Skänner Pro

A Streamlit dashboard that collects and presents selected public listings and
offers for Estonian users. The interface is in Estonian.

## Run locally

Use Python 3.10 or newer.

```bash
python -m venv .venv
```

Activate the environment:

- macOS/Linux: `source .venv/bin/activate`
- Windows PowerShell: `.venv\Scripts\Activate.ps1`

Install dependencies and start the app:

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

## Refresh and pagination

The app's live sources are cached for one hour and the browser session triggers
an hourly rerun. On that rerun, configured live sources refresh together; a
failure from one provider is shown for that section and does not stop the
others. Lists show 25 results initially, with **Näita veel 25** and **Näita
kõiki** controls. The counts are based on the current search and category
filters.

Automatic refresh requires an open browser session. Streamlit does not keep a
sessionless process running in the background; use a separate scheduled worker
if data must refresh while nobody has the app open.

## Optional Facebook RSS feed

The free-items section can read an RSS feed URL from the
`FACEBOOK_GROUP_RSS_URL` environment variable or Streamlit secrets. For local
development, create `.streamlit/secrets.toml`:

```toml
FACEBOOK_GROUP_RSS_URL = "https://example.com/your-feed.xml"
```

Do not commit `.streamlit/secrets.toml` or private feed URLs to GitHub.

## Data notes

- The gardening section fetches active Hange.ee listings and links each card to
  the individual offer page. It filters listings by gardening-related words, so
  a relevant offer may be missed if its title and summary use different wording.
- The app also fetches listings from Kinnisvara24 and AutoScout24 and embeds the
  ratings page. These sites may change their page markup and block automated
  requests.
- Facebook free-item listings refresh only when `FACEBOOK_GROUP_RSS_URL` is
  configured.
- The grocery section currently contains static sample data; prices are not
  verified as current.
- Fuel prices and parking information do not have a connected data source yet.

Check each provider's terms and robots policy before deploying a scraper
publicly. Do not present sample data as current or verified offers.
