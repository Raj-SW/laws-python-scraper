from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional, AsyncIterable, Tuple

from playwright.async_api import async_playwright, Browser, Page
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import Settings
from .logger import setup_logger
from .pdf_utils import extract_text_from_pdf, count_pdf_pages
from .supabase_client import SupabaseHelper


@dataclass
class Judgment:
    title: str
    document_number: str
    delivered_on: str
    pdf_url: str
    pdf_preview_url: str
    page_index: int


class CourtScraper:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = setup_logger(settings.log_level)
        self.sb = SupabaseHelper(
            settings.supabase_url, settings.supabase_service_key, settings.table_name
        )

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser: Browser = await self.playwright.chromium.launch(
            headless=self.settings.headless, args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        self.context = await self.browser.new_context(accept_downloads=True)
        self.page: Page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    @retry(wait=wait_exponential(multiplier=1, min=1, max=10), stop=stop_after_attempt(5))
    async def login(self) -> None:
        s = self.settings
        self.logger.info("Navigating to login page")
        await self.page.goto(s.login_url, wait_until="domcontentloaded")
        await self.page.fill("#userEmail-id", s.username)
        await self.page.fill("#plainTextPassword", s.password)
        # Submit via pressing Enter in password field
        await self.page.press("#plainTextPassword", "Enter")
        await self.page.wait_for_load_state("networkidle")
        # Handle MauPass 2FA send security code step if present
        try:
            if "maupass.govmu.org/Account/SendSecurityCode" in (self.page.url or ""):
                self.logger.info("2FA SendSecurityCode detected; clicking Submit and waiting")
                selector = "div.kt-login__actions input[type='submit'][value='Submit']"
                await self.page.wait_for_selector(selector, timeout=15000)
                await self.page.click(selector)
                await self.page.wait_for_load_state("networkidle")
                # Small pause to observe transition after requesting code
                await asyncio.sleep(2)

                # After requesting security code, attempt to fetch TOTP from external endpoint
                if self.settings.totp_endpoint:
                    try:
                        self.logger.info("Fetching TOTP code from endpoint")
                        resp = await self.context.request.get(self.settings.totp_endpoint, timeout=15000)
                        if not resp.ok:
                            raise RuntimeError(f"TOTP endpoint returned {resp.status}")
                        # Try to parse as JSON first, else plain text
                        code: str | None = None
                        try:
                            data = await resp.json()
                            # Accept common keys
                            for k in ("code", "totp", "token", "otp"):
                                v = data.get(k)
                                if isinstance(v, str) and v.strip():
                                    code = v.strip()
                                    break
                        except Exception:
                            text_val = (await resp.text() or "").strip()
                            if text_val:
                                code = text_val
                        if not code:
                            raise RuntimeError("No TOTP code found in endpoint response")

                        # Log the raw TOTP code for debugging/visibility (avoid in production)
                        self.logger.info("TOTP code retrieved (length=%d)", len(code))
                        self.logger.info("TOTP code: %s", code)
                        self.logger.info("Waiting 2s before entering TOTP to observe flow")
                        await asyncio.sleep(2)

                        self.logger.info("Entering TOTP code into #Code")
                        # Wait for Code input to be visible
                        await self.page.wait_for_selector("#Code, input#Code[name='Code']", timeout=20000)
                        await self.page.fill("#Code", code)
                        self.logger.info("TOTP code entered; waiting 1s before submitting")
                        await asyncio.sleep(1)
                        # Click Submit on the verification page
                        submit_selector = "input[type='submit'].btn.btn-primary.btn-elevate.kt-login__btn-primary, input[type='submit'][value='Submit']"
                        await self.page.wait_for_selector(submit_selector, timeout=15000)
                        self.logger.info("Clicking final Submit for TOTP verification")
                        await self.page.click(submit_selector)
                        await self.page.wait_for_load_state("networkidle")
                        # Small pause to observe the post-submit state
                        await asyncio.sleep(2)

                        # Check whether we appear to have left the 2FA page
                        still_on_2fa = "SendSecurityCode" in (self.page.url or "")
                        try:
                            code_field = await self.page.query_selector("#Code")
                        except Exception:
                            code_field = None
                        if not still_on_2fa and not code_field:
                            self.logger.info("TOTP verification successful; continuing")
                        else:
                            self.logger.warning("TOTP verification may not have completed; still on 2FA page")
                    except Exception as e:
                        self.logger.error(f"TOTP handling failed: {e}")
        except Exception as e:
            self.logger.warning(f"2FA SendSecurityCode step skipped or failed: {e}")
        self.logger.info("Login complete")

    async def navigate_to_page(self, page_index: int) -> None:
        url = f"{self.settings.target_url}?page={page_index}"
        await self.page.goto(url, wait_until="domcontentloaded")
        await self.page.wait_for_load_state("networkidle")

    async def iterate_rows(self) -> AsyncIterable[Judgment]:
        # Use stable class selectors instead of column positions
        rows = await self.page.query_selector_all("table tbody tr")
        for row in rows:
            title_el = await row.query_selector("td.views-field-title, td.views-field.views-field-title")
            doc_el = await row.query_selector("td.views-field-field-document-number-hidden")
            date_el = await row.query_selector("td.views-field-field-delivered-on")

            title = (await title_el.inner_text()).strip() if title_el else ""
            doc_no = (await doc_el.inner_text()).strip() if doc_el else ""
            delivered_on = (await date_el.inner_text()).strip() if date_el else ""

            # Extract preview URL from anchor inside the document-number cell
            preview_href = None
            try:
                preview_link_el = await row.query_selector("td.views-field-field-document-number-hidden a")
                if preview_link_el:
                    preview_href = await preview_link_el.get_attribute("href")
            except Exception:
                preview_href = None
            if preview_href:
                pdf_preview_url = preview_href if preview_href.startswith("http") else f"https://supremecourt.govmu.org{preview_href}"
            else:
                pdf_preview_url = ""

            link_el = await row.query_selector("td.views-field-nothing-1 a.faDownload, td .faDownload")
            if not link_el:
                continue
            href = await link_el.get_attribute("href")
            if not href:
                continue
            pdf_url = href if href.startswith("http") else f"https://supremecourt.govmu.org{href}"
            yield Judgment(title=title, document_number=doc_no, delivered_on=delivered_on, pdf_url=pdf_url, pdf_preview_url=pdf_preview_url, page_index=0)

    async def download_pdf_bytes(self, url: str) -> Tuple[bytes, str]:
        # Use context's request for lightweight download
        resp = await self.context.request.get(url, timeout=self.settings.download_timeout_ms)
        if not resp.ok:
            raise RuntimeError(f"Failed to download PDF: {resp.status}")
        # Try to infer filename from headers, else fallback to URL id
        filename = "judgment.pdf"
        try:
            cd = resp.headers.get("content-disposition") or resp.headers.get("Content-Disposition")
            if cd and "filename=" in cd:
                filename = cd.split("filename=")[-1].strip('"\' ')
            else:
                filename = url.rstrip("/").split("/")[-1] + ".pdf"
        except Exception:
            filename = url.rstrip("/").split("/")[-1] + ".pdf"
        return await resp.body(), filename

    async def process_judgment(self, j: Judgment) -> None:
        try:
            pdf_bytes, file_name = await self.download_pdf_bytes(j.pdf_url)
            text = extract_text_from_pdf(pdf_bytes)
            pages = count_pdf_pages(pdf_bytes)

            # Parse date safely: expected formats like 22/08/2025
            def parse_date(value: str) -> str | None:
                for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
                    try:
                        dt = datetime.strptime(value.strip(), fmt)
                        return dt.strftime("%Y-%m-%d %H:%M:%S")
                    except Exception:
                        continue
                return None

            judgment_dt = parse_date(j.delivered_on) if j.delivered_on else None
            extracted_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            record = {
                # Map to judgments7 schema
                "case_number": j.document_number or None,
                "case_title": j.title or None,
                "judgment_date": judgment_dt,
                "file_name": file_name,
                "content": text,
                "page_count": pages,
                "page_number": j.page_index + 1,
                "extracted_at": extracted_at,
                "download_url": j.pdf_url,
            "pdf_preview_url": j.pdf_preview_url or None,
            }
            self.sb.insert_judgment(record)
        except Exception as e:
            self.logger.error(f"Failed processing {j.pdf_url}: {e}")

    async def run(self) -> None:
        await self.login()
        start = max(self.settings.start_page - 1, 0)
        end: Optional[int] = self.settings.end_page

        page_index = start
        while True:
            if end is not None and page_index > end - 1:
                break
            self.logger.info(f"Scraping page {page_index + 1}")
            await self.navigate_to_page(page_index)
            tasks = []
            async for j in self.iterate_rows():
                j.page_index = page_index
                tasks.append(asyncio.create_task(self.process_judgment(j)))
                if len(tasks) >= self.settings.batch_size:
                    await asyncio.gather(*tasks)
                    tasks.clear()
                    await asyncio.sleep(self.settings.page_delay_ms / 1000)

            if tasks:
                await asyncio.gather(*tasks)

            # Move to next page via "next" link if END_PAGE not set
            if end is None:
                next_link = await self.page.query_selector("nav.pager li.pager__item--next a")
                if not next_link:
                    break
                page_index += 1
            else:
                page_index += 1


async def run_scraper(settings: Settings) -> None:
    async with CourtScraper(settings) as cs:
        await cs.run()

