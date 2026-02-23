# civil_parse.py
from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import unicodedata
from typing import Dict, Any, Optional, Tuple

from playwright.async_api import async_playwright, Page, Locator

SEARCH_URL = "https://civil.info.hu/civil_szervezet_kereso/index"


# -----------------------
# Utilities
# -----------------------
def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def norm_name(s: str) -> str:
    """Accent-insensitive-ish normalization for matching Hungarian org names."""
    s = _norm(s).casefold()
    s = "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9]+", " ", s)
    return _norm(s)


async def _maybe_accept_cookies(page: Page) -> None:
    """Best-effort cookie/consent dismissal."""
    candidates = [
        page.get_by_role("button", name=re.compile(r"(Összes elfogad|Mindent elfogad|Accept all)", re.I)),
        page.get_by_role("button", name=re.compile(r"(Elfogad|Rendben|OK|Accept)", re.I)),
    ]
    for btn in candidates:
        try:
            if await btn.count() > 0:
                await btn.first.click(timeout=1500)
                await page.wait_for_timeout(300)
                return
        except Exception:
            pass


async def _find_szervezet_input(page: Page) -> Locator:
    """
    Robustly find the "Szervezet neve" input on the SEARCH page.
    (We don't rely on get_by_label because some pages don't bind labels properly.)
    """
    # Try label if it works
    try:
        loc = page.get_by_label(re.compile(r"Szervezet neve", re.I))
        if await loc.count() > 0:
            return loc.first
    except Exception:
        pass

    # Placeholder
    loc = page.locator('input[placeholder*="Szervezet" i][placeholder*="neve" i]')
    if await loc.count() > 0:
        return loc.first

    # name/id contains szervezet
    loc = page.locator('input[name*="szervezet" i], input[id*="szervezet" i]')
    if await loc.count() > 0:
        return loc.first

    # last resort: first text input inside the search form area
    # (many pages have a single primary filter input)
    form = page.locator("form").first
    if await form.count() > 0:
        loc = form.locator('input[type="text"], input:not([type])').first
        if await loc.count() > 0:
            return loc

    # absolute fallback
    loc = page.locator('input[type="text"], input:not([type])').first
    if await loc.count() > 0:
        return loc

    raise RuntimeError("Could not locate the search input for 'Szervezet neve'.")


async def _click_szures(page: Page) -> None:
    btn = page.get_by_role("button", name=re.compile(r"^Szűrés$", re.I))
    if await btn.count() > 0:
        await btn.first.click()
        return
    # fallback by text
    btn2 = page.get_by_text(re.compile(r"^\s*Szűrés\s*$", re.I))
    if await btn2.count() > 0:
        await btn2.first.click()
        return
    raise RuntimeError("Could not find 'Szűrés' button.")


async def _wait_results(page: Page, timeout_ms: int = 25000) -> Locator:
    await page.wait_for_selector("table tbody tr", timeout=timeout_ms)
    return page.locator("table tbody tr")


async def _extract_row_meta(row: Locator) -> Dict[str, str]:
    """Extract (Név, Adószám, Cím) from a search-results row."""
    meta: Dict[str, str] = {}
    tds = row.locator("td")
    c = await tds.count()
    if c >= 1:
        meta["search_name"] = _norm(await tds.nth(0).inner_text())
    if c >= 2:
        meta["search_adoszam"] = _norm(await tds.nth(1).inner_text())
    if c >= 3:
        meta["search_cim"] = _norm(await tds.nth(2).inner_text())
    return meta


async def _open_row_profile(row: Locator) -> None:
    """Click inside row to open profile."""
    link = row.locator("a").first
    if await link.count() > 0:
        await link.click()
    else:
        await row.locator("td").first.click()


async def _go_back_to_search(page: Page) -> None:
    """
    Profile page includes a "Vissza a civil keresőbe" link (per your HTML).
    Use it to return to results deterministically.
    """
    back = page.get_by_role("link", name=re.compile(r"Vissza a civil keresőbe", re.I))
    if await back.count() > 0:
        await back.first.click()
        await page.wait_for_timeout(600)
        return
    # fallback: navigate directly
    await page.goto(SEARCH_URL, wait_until="domcontentloaded")
    await page.wait_for_timeout(600)


# -----------------------
# Parsing profile page (based on the HTML you pasted)
# -----------------------
async def _get_profile_teljes_nev(page: Page) -> str:
    """
    From your HTML:
      <div id="baseDataContainer">
        <label>Teljes név</label>
        <strong>...</strong>
    We'll locate the label containing 'Teljes név' and read the strong in the same row.
    """
    base = page.locator("#baseDataContainer")
    if await base.count() == 0:
        return ""

    row = base.locator("xpath=.//div[contains(@class,'form-group')][.//label[contains(normalize-space(.),'Teljes név')]]").first
    if await row.count() == 0:
        return ""

    strong = row.locator("strong").first
    if await strong.count() == 0:
        return ""

    return _norm(await strong.inner_text())


async def _extract_kv_from_publicorgrows(container: Locator) -> Dict[str, str]:
    """
    The profile page uses:
      <div class="form-group row publicorgrow">
        <label ...>Key</label>
        <div ...><strong>Value</strong></div>
      </div>
    We'll parse those.
    """
    out: Dict[str, str] = {}
    rows = container.locator(".publicorgrow")
    n = await rows.count()
    for i in range(n):
        r = rows.nth(i)
        label = r.locator("label").first
        val = r.locator("strong").first
        k = _norm(await label.inner_text()) if await label.count() else ""
        v = _norm(await val.inner_text()) if await val.count() else ""
        if k:
            out[k] = v
    return out


async def _click_tab(page: Page, tab_name: str) -> None:
    """
    In your HTML, tabs are <a class="nav-link" ...>Alapadatok</a>, etc.
    We'll click by visible text.
    """
    tab = page.locator("ul.nav-custom-tabs a.nav-link", has_text=re.compile(rf"^{re.escape(tab_name)}$", re.I)).first
    if await tab.count() == 0:
        # fallback
        tab = page.get_by_role("link", name=re.compile(rf"^{re.escape(tab_name)}$", re.I)).first
    if await tab.count() == 0:
        raise RuntimeError(f"Could not find tab '{tab_name}'.")
    await tab.click()
    await page.wait_for_timeout(300)


async def _extract_kv_from_details_panel(page: Page, details_id: str) -> Dict[str, str]:
    """
    Alapadatok panel:  #details1
    NAV 1% panel:      #details2
    We'll parse publicorgrows in that panel, and also capture "Nincs adat." messages.
    """
    panel = page.locator(f"#{details_id}")
    if await panel.count() == 0:
        return {}

    # If it only has "Nincs adat."
    txt = _norm(await panel.inner_text())
    if "Nincs adat." in txt:
        return {"_info": "Nincs adat."}

    # Parse key/values
    kv = await _extract_kv_from_publicorgrows(panel)
    if kv:
        return kv

    # Fallback: parse label/strong anywhere in panel
    # (handles other minor layout variants)
    out: Dict[str, str] = {}
    groups = panel.locator("div.form-group")
    n = await groups.count()
    for i in range(n):
        g = groups.nth(i)
        lab = g.locator("label").first
        st = g.locator("strong").first
        k = _norm(await lab.inner_text()) if await lab.count() else ""
        v = _norm(await st.inner_text()) if await st.count() else ""
        if k:
            out[k] = v
    return out


# -----------------------
# Main scrape logic
# -----------------------
async def scrape_for_name(
    name: str,
    headless: bool = True,
    max_rows_to_try: int = 10,
    slow_mo_ms: int = 0,
    debug_dir: str = "debug_artifacts",
) -> Dict[str, Any]:
    os.makedirs(debug_dir, exist_ok=True)
    qn = norm_name(name)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless, slow_mo=slow_mo_ms if slow_mo_ms > 0 else None)
        page = await browser.new_page()
        await page.set_viewport_size({"width": 1400, "height": 900})

        await page.goto(SEARCH_URL, wait_until="domcontentloaded")
        await _maybe_accept_cookies(page)

        # Fill and search
        try:
            await page.wait_for_selector("input", timeout=20000)
            inp = await _find_szervezet_input(page)

            await inp.click()
            await inp.press("Control+A")
            await inp.press("Backspace")
            await inp.type(name, delay=10)

            await _click_szures(page)
            rows = await _wait_results(page, timeout_ms=25000)
        except Exception as exc:
            ts = int(time.time())
            await page.screenshot(path=os.path.join(debug_dir, f"fail_search_{ts}.png"), full_page=True)
            html = await page.content()
            with open(os.path.join(debug_dir, f"fail_search_{ts}.html"), "w", encoding="utf-8") as f:
                f.write(html)
            await browser.close()
            return {
                "query": name,
                "status": "failed_search",
                "error": f"{type(exc).__name__}: {exc}",
                "page_url": page.url,
                "debug_png": os.path.join(debug_dir, f"fail_search_{ts}.png"),
                "debug_html": os.path.join(debug_dir, f"fail_search_{ts}.html"),
                "scraped_at_epoch": ts,
            }

        # Try rows one by one until profile 'Teljes név' matches query
        n_rows = await rows.count()
        to_try = min(max_rows_to_try, n_rows)

        for i in range(to_try):
            row = rows.nth(i)
            meta = await _extract_row_meta(row)

            # Open profile
            try:
                await _open_row_profile(row)
                await page.wait_for_timeout(600)
            except Exception as exc:
                continue

            # Verify profile name
            profile_name = await _get_profile_teljes_nev(page)
            if profile_name and (qn in norm_name(profile_name) or norm_name(profile_name) in qn):
                # Matched — extract data
                result: Dict[str, Any] = {
                    "query": name,
                    "status": "ok",
                    "matched_row_index": i,
                    "matched_teljes_nev": profile_name,
                    "page_url": page.url,
                    "scraped_at_epoch": int(time.time()),
                    **meta,
                }

                # Azonosító adatok block
                base = page.locator("#baseDataContainer")
                result["azonosito_adatok"] = await _extract_kv_from_publicorgrows(base) if await base.count() else {}

                # Tabs
                try:
                    await _click_tab(page, "Alapadatok")
                    result["alapadatok"] = await _extract_kv_from_details_panel(page, "details1")
                except Exception as exc:
                    result["alapadatok_error"] = f"{type(exc).__name__}: {exc}"

                try:
                    await _click_tab(page, "NAV 1%")
                    result["nav_1_percent"] = await _extract_kv_from_details_panel(page, "details2")
                except Exception as exc:
                    result["nav_1_percent_error"] = f"{type(exc).__name__}: {exc}"

                await browser.close()
                return result

            # Not matched -> go back and try next row
            await _go_back_to_search(page)

            # Important: after going back, the results table might need a moment
            # and the DOM handles might be stale; re-find rows.
            try:
                await page.wait_for_timeout(300)
                rows = await _wait_results(page, timeout_ms=25000)
            except Exception:
                # If results disappeared, re-run the search quickly
                try:
                    inp = await _find_szervezet_input(page)
                    await inp.click()
                    await inp.press("Control+A")
                    await inp.press("Backspace")
                    await inp.type(name, delay=10)
                    await _click_szures(page)
                    rows = await _wait_results(page, timeout_ms=25000)
                except Exception:
                    pass

        # No match found
        ts = int(time.time())
        await page.screenshot(path=os.path.join(debug_dir, f"no_profile_match_{ts}.png"), full_page=True)
        html = await page.content()
        with open(os.path.join(debug_dir, f"no_profile_match_{ts}.html"), "w", encoding="utf-8") as f:
            f.write(html)

        await browser.close()
        return {
            "query": name,
            "status": "no_profile_match",
            "tried_rows": to_try,
            "page_url": page.url,
            "debug_png": os.path.join(debug_dir, f"no_profile_match_{ts}.png"),
            "debug_html": os.path.join(debug_dir, f"no_profile_match_{ts}.html"),
            "scraped_at_epoch": ts,
        }


def main() -> None:
    # Ensure Proactor policy on Windows
    if sys.platform.startswith("win") and hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    ap = argparse.ArgumentParser(description="Scrape civil.info.hu profile: Azonosító adatok + Alapadatok + NAV 1%")
    ap.add_argument("name", help="Value for 'Szervezet neve'")
    ap.add_argument("--headless", action="store_true", help="Run browser headless")
    ap.add_argument("--max-rows", type=int, default=10, help="How many search result rows to try until profile matches")
    ap.add_argument("--slowmo", type=int, default=0, help="Slow motion in ms for debugging (e.g., 100)")
    ap.add_argument("--out", default="", help="Optional output JSON file path")
    ap.add_argument("--debug-dir", default="debug_artifacts", help="Folder for debug screenshots/html")
    args = ap.parse_args()

    data = asyncio.run(
        scrape_for_name(
            args.name,
            headless=args.headless,
            max_rows_to_try=args.max_rows,
            slow_mo_ms=args.slowmo,
            debug_dir=args.debug_dir,
        )
    )

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    else:
        print(json.dumps(data, ensure_ascii=False))


if __name__ == "__main__":
    main()
