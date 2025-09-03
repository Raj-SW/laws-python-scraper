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

Optional:

- `TOTP_ENDPOINT` — HTTP(S) endpoint returning the current 2FA code after the first Submit on the MauPass 2FA page. The scraper will GET this URL and expects either JSON with one of the keys `code`, `totp`, `token`, `otp` or a plain text body containing the code. Example: `https://n8n.islandai.co/webhook-test/6a705dfe-98a3-4aec-a7b5-d4fc06e71718`

### Deploy on EasyPanel

- Use the included `Dockerfile`.
- Set environment variables from `.env.example` in EasyPanel UI.
- The container runs `python -m scraper.cli`.

### Notes

- The scraper throttles requests and uses streaming downloads to keep memory low.
- Failed operations are retried with exponential backoff.
