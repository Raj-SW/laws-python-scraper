import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    login_url: str
    target_url: str
    username: str
    password: str

    supabase_url: str
    supabase_service_key: str
    table_name: str

    start_page: int
    end_page: int | None

    max_retries: int
    download_timeout_ms: int
    page_delay_ms: int
    batch_size: int
    headless: bool

    log_level: str


def get_bool(env_value: str | None, default: bool) -> bool:
    if env_value is None:
        return default
    return env_value.strip().lower() in {"1", "true", "yes", "y"}


def load_settings() -> Settings:
    load_dotenv(override=False)

    login_url = os.getenv("LOGIN_URL", "").strip()
    target_url = os.getenv("TARGET_URL", "").strip()
    username = os.getenv("LOGIN_USERNAME", "").strip()
    password = os.getenv("LOGIN_PASSWORD", "").strip()

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    supabase_service_key = os.getenv("SUPABASE_SERVICE_KEY", os.getenv("SUPABASE_ANON_KEY", "")).strip()
    table_name = os.getenv("TABLE_NAME", "judgments").strip()

    start_page = int(os.getenv("START_PAGE", "1") or 1)
    end_page_val = os.getenv("END_PAGE", "").strip()
    end_page = int(end_page_val) if end_page_val else None

    max_retries = int(os.getenv("MAX_RETRIES", "5") or 5)
    download_timeout_ms = int(os.getenv("DOWNLOAD_TIMEOUT", "60000") or 60000)
    page_delay_ms = int(os.getenv("PAGE_DELAY", "20000") or 20000)
    batch_size = int(os.getenv("BATCH_SIZE", "10") or 10)
    headless = get_bool(os.getenv("HEADLESS", "true"), True)

    log_level = os.getenv("LOG_LEVEL", "info").strip()

    if not (login_url and target_url and username and password):
        raise RuntimeError("Missing required LOGIN_URL, TARGET_URL, LOGIN_USERNAME or LOGIN_PASSWORD")
    if not (supabase_url and supabase_service_key):
        raise RuntimeError("Missing required SUPABASE_URL or SUPABASE_SERVICE_KEY")

    return Settings(
        login_url=login_url,
        target_url=target_url,
        username=username,
        password=password,
        supabase_url=supabase_url,
        supabase_service_key=supabase_service_key,
        table_name=table_name,
        start_page=start_page,
        end_page=end_page,
        max_retries=max_retries,
        download_timeout_ms=download_timeout_ms,
        page_delay_ms=page_delay_ms,
        batch_size=batch_size,
        headless=headless,
        log_level=log_level,
    )

