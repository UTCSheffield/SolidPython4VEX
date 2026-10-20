"""Build parts/catalog.json from the VEX CAD search page. Run locally, not in CI/Codespaces.

    pip install .[scrape]  (plus `playwright install chromium`, or use --browser msedge)
    python scripts/scrape_vex_catalog.py --out-dir vex_scrape [--download-step]

Stage 1 loads the search page in a visible browser (solve any CAPTCHA by hand), captures the
Algolia query the page makes for the CAD index, and replays it for every results page.
Raw hits go to hits_raw.json so field mapping can be adjusted without re-scraping.
Stage 2 visits each hit's shop page for SKU, price and STEP download link.
"""
import argparse
import json
import re
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SEARCH_URL = (
    "https://www.vexrobotics.com/catalogsearch/result/?q=__empty__&vex_site=cads"
    "&vex_m2_vexroboticsuk_cads%5BrefinementList%5D%5Bproduct_lines%5D%5B0%5D=VEX%20V5"
)
STEP_LINK = re.compile(r"\.(step|stp|zip)(\?|$)", re.I)


def collect_hits(page, delay):
    captured = {}

    def on_request(req):
        if "algolia" in req.url and req.method == "POST" and "cads" in (req.post_data or ""):
            captured.setdefault("req", req)

    page.on("request", on_request)
    page.goto(SEARCH_URL)
    for _ in range(60):
        if "req" in captured:
            break
        page.wait_for_timeout(500)
    if "req" not in captured:
        raise SystemExit("No Algolia CAD query seen; is the page blocked (CAPTCHA)?")

    req = captured["req"]
    body = json.loads(req.post_data)
    queries = body.get("requests", [])
    idx = next(i for i, q in enumerate(queries) if "cads" in q.get("indexName", ""))
    hits, pg = [], 0
    while True:
        queries[idx]["params"] = re.sub(r"&?page=\d+", "", queries[idx].get("params", "")) + f"&page={pg}"
        resp = page.request.post(req.url, data=json.dumps(body), headers=req.headers)
        result = resp.json()["results"][idx]
        hits += result["hits"]
        pg += 1
        if pg >= result.get("nbPages", 0):
            return hits
        time.sleep(delay)


def scrape_product(page, url):
    page.goto(url, wait_until="domcontentloaded")
    info = {"sku": "", "price": None, "currency": "", "step_url": ""}
    for node in page.locator('script[type="application/ld+json"]').all_text_contents():
        try:
            data = json.loads(node)
        except ValueError:
            continue
        for d in data if isinstance(data, list) else [data]:
            if isinstance(d, dict) and d.get("@type") == "Product":
                info["sku"] = d.get("sku", "")
                offers = d.get("offers") or {}
                offers = offers[0] if isinstance(offers, list) else offers
                if offers.get("price") not in (None, ""):
                    info["price"] = float(offers["price"])
                info["currency"] = offers.get("priceCurrency", "")
    for href in page.locator("a[href]").evaluate_all("els => els.map(e => e.href)"):
        if STEP_LINK.search(href) or "step" in href.lower():
            info["step_url"] = href
            break
    return info


def slugify(text):
    return re.sub(r"[^A-Za-z0-9]+", "_", text).strip("_")


def download_from_hits(ctx, hits, out, delay):
    """Download each hit's download_link; resumable. Uses the browser session to pass Cloudflare."""
    step_dir = out / "step"
    step_dir.mkdir(exist_ok=True)
    catalog = []
    for i, h in enumerate(hits, 1):
        name = slugify(f"{h['slug']}_{h['name']}")
        entry = {
            "name": name, "sku": h["slug"], "description": h["name"],
            "shop_url": h["url"], "step_url": h["download_link"],
            "price": None, "currency": "USD",
        }
        catalog.append(entry)
        if any(step_dir.glob(f"{name}.*")):
            continue
        resp = ctx.request.get(h["download_link"])
        if not resp.ok:
            print(f"[{i}/{len(hits)}] FAILED {resp.status} {name}")
            continue
        disp = resp.headers.get("content-disposition", "")
        m = re.search(r'filename="?([^";]+)', disp)
        ext = Path(m.group(1)).suffix if m else ".zip"
        (step_dir / f"{name}{ext}").write_bytes(resp.body())
        print(f"[{i}/{len(hits)}] {name}{ext}")
        time.sleep(delay)
    (out / "catalog.json").write_text(json.dumps(catalog, indent=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default="vex_scrape")
    ap.add_argument("--delay", type=float, default=2.0, help="seconds between requests")
    ap.add_argument("--download-step", action="store_true")
    ap.add_argument("--from-hits", action="store_true",
                    help="skip product pages; download download_link from existing hits_raw.json")
    ap.add_argument("--browser", default="chromium", choices=["chromium", "msedge", "chrome"],
                    help="msedge/chrome use the installed browser (no playwright install needed)")
    args = ap.parse_args()
    out = Path(args.out_dir)
    out.mkdir(exist_ok=True)

    with sync_playwright() as p:
        kwargs = {} if args.browser == "chromium" else {"channel": args.browser}
        ctx = p.chromium.launch_persistent_context(str(out / "profile"), headless=False, **kwargs)
        page = ctx.new_page()
        if args.from_hits:
            page.goto(SEARCH_URL)  # establishes the Cloudflare session; solve any CAPTCHA here
            page.wait_for_timeout(5000)
            hits = json.loads((out / "hits_raw.json").read_text())
            download_from_hits(ctx, hits, out, args.delay)
            ctx.close()
            return
        hits = collect_hits(page, args.delay)
        (out / "hits_raw.json").write_text(json.dumps(hits, indent=1))
        print(f"{len(hits)} CAD hits")

        catalog = []
        for h in hits:
            time.sleep(args.delay)
            info = scrape_product(page, h["url"])
            name = re.sub(r"[^A-Za-z0-9]+", "_", h["name"]).strip("_")
            catalog.append({
                "name": name, "sku": info["sku"], "description": h["name"],
                "shop_url": h["url"], "step_url": info["step_url"],
                "price": info["price"], "currency": info["currency"] or "USD",
            })
            if args.download_step and info["step_url"]:
                data = ctx.request.get(info["step_url"]).body()
                (out / "step").mkdir(exist_ok=True)
                (out / "step" / f"{name}{Path(info['step_url'].split('?')[0]).suffix}").write_bytes(data)
            (out / "catalog.json").write_text(json.dumps(catalog, indent=1))
        ctx.close()
    print("Wrote", out / "catalog.json", "- copy to src/solidpython4vex/parts/catalog.json")


if __name__ == "__main__":
    main()
