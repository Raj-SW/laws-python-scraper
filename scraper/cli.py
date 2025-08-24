import asyncio
from .config import load_settings
from .logger import setup_logger
from .scraper import run_scraper


def main() -> None:
    settings = load_settings()
    logger = setup_logger(settings.log_level)
    logger.info("Starting scraper (headless=%s)", settings.headless)
    asyncio.run(run_scraper(settings))


if __name__ == "__main__":
    main()

