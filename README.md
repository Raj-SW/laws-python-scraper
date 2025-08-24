## Laws Python Scraper

A robust, memory-efficient scraper that:
- Logs in to a protected portal
- Crawls a paginated judgments table
- Streams and parses PDF judgments
- Upserts extracted data into a Supabase table

### Quick start (local)
1. Copy `.env.example` to `.env` and fill values.
2. Create a virtual environment and install deps:
```
python -m venv .venv
. .venv/Scripts/activate
pip install -r requirements.txt
python -m playwright install --with-deps
```
3. Run:
```
python -m scraper.cli
```

### Environment
See `.env.example` for all variables. Minimum:
- `LOGIN_URL`, `TARGET_URL`, `LOGIN_USERNAME`, `LOGIN_PASSWORD`
- `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `TABLE_NAME`

### Deploy on EasyPanel
- Use the included `Dockerfile`.
- Set environment variables from `.env.example` in EasyPanel UI.
- The container runs `python -m scraper.cli`.

### Notes
- The scraper throttles requests and uses streaming downloads to keep memory low.
- Failed operations are retried with exponential backoff.

