#!/usr/bin/env python3
"""
fetch_figures.py
----------------
Pulls S.H.Figuarts release / pre-order / pricing data from AmiAmi's public
(unauthenticated) JSON API for a fixed set of anime franchises, normalizes it
into a clean schema, and writes it to data.json.

This is designed to run inside GitHub Actions on a schedule. GitHub Actions
has unrestricted internet access, so it can reach api.amiami.com (which a
browser cannot, due to CORS, and which some sandboxes block via firewall).

If AmiAmi is unreachable or returns nothing, the script preserves any existing
data.json rather than wiping it, and merges in entries from manual_figures.json
so the site never goes blank.

No API key secret is required: AmiAmi's public endpoint uses a well-known
header value (X-User-Key: amiami_dev).
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API_BASE = "https://api.amiami.com/api/v1.0"
USER_KEY = "amiami_dev"

# Franchises to track. "id" is a stable slug used by the web app.
# Order controls display order.
FRANCHISES = [
    {"id": "jojo",     "name": "JoJo's Bizarre Adventure", "search": "JoJo"},
    {"id": "onepiece", "name": "One Piece",                "search": "One Piece"},
    {"id": "bleach",   "name": "Bleach",                   "search": "Bleach"},
    {"id": "jjk",      "name": "Jujutsu Kaisen",           "search": "Jujutsu Kaisen"},
    {"id": "mha",      "name": "My Hero Academia",         "search": "My Hero Academia"},
    {"id": "csm",      "name": "Chainsaw Man",             "search": "Chainsaw Man"},
]

# Brands to track. For each brand we run one search per franchise.
# "match" is the list of lowercase substrings that confirm an item is this brand
# (AmiAmi search is fuzzy, so we filter the results by product name).
# "label" is the short tag shown on each card in the web app.
BRANDS = [
    {
        "id": "shf",
        "label": "Figuarts",
        "query_prefix": "S.H.Figuarts",
        "match": ["s.h.figuarts", "shfiguarts", "s.h. figuarts"],
    },
    {
        "id": "medicos",
        "label": "Medicos",
        # Medicos's main line is "Super Action Statue"; some items are branded
        # only as "Medicos". Searching both maximizes coverage.
        "query_prefix": "Super Action Statue",
        "match": ["super action statue", "medicos"],
    },
]

# Whether to include AmiAmi's pre-owned / secondhand listings. Medicos has many
# older figures only available used, so this is on. New items are always included.
INCLUDE_USED = True

HEADERS = {
    "X-User-Key": USER_KEY,
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Referer": "https://www.amiami.com/",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

# AmiAmi image paths are relative; prefix with this.
IMG_PREFIX = "https://img.amiami.com"


def api_get(path, params):
    """GET a JSON document from the AmiAmi API. Returns dict or None on failure."""
    qs = urllib.parse.urlencode(params)
    url = f"{API_BASE}/{path}?{qs}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"  ! request failed: {type(e).__name__}: {e}", file=sys.stderr)
        return None


def map_status(item):
    """
    Translate AmiAmi's various availability flags into our display states:
    'preorder', 'upcoming', 'available', 'soldout', 'used'.
    AmiAmi's schema is not perfectly documented and changes over time, so we
    check several fields defensively.
    """
    stock = item.get("instock_flg")
    preorder = item.get("preorder")
    salestat = (item.get("salestatus") or "").lower()
    salestat_detail = (item.get("saletext") or "").lower()
    cond = item.get("condition_flg")  # AmiAmi flags pre-owned items
    text = f"{salestat} {salestat_detail}"

    # Pre-owned / secondhand listing
    if cond == 1 or "pre-owned" in text or "preowned" in text or "used" in text:
        return "used"
    # Sold out / closed
    if any(k in text for k in ["sold out", "closed", "unavailable", "end of sale"]):
        return "soldout"
    # Pre-order open
    if preorder or "pre-order" in text or "preorder" in text:
        return "preorder"
    # In stock / available
    if stock == 1 or "in stock" in text or "available" in text:
        return "available"
    # Announced but not yet orderable
    if "back-order" in text or "back order" in text or "tentative" in text or "provisional" in text:
        return "upcoming"
    # Fallback: if there is a future release date and no stock, call it upcoming
    return "upcoming"


def normalize(item, franchise, brand):
    """Convert a raw AmiAmi item into our clean schema."""
    gcode = item.get("gcode") or ""
    thumb = item.get("thumb_url") or item.get("main_image_url") or ""
    if thumb and thumb.startswith("/"):
        thumb = IMG_PREFIX + thumb
    price = item.get("c_price_taxed") or item.get("price") or item.get("min_price")
    list_price = item.get("price") or item.get("c_price_taxed")
    return {
        "id": gcode,
        "franchise": franchise["id"],
        "brand": brand["id"],
        "brand_label": brand["label"],
        "name": (item.get("gname") or "").strip(),
        "status": map_status(item),
        "price_jpy": price,
        "list_price_jpy": list_price,
        "release_date": item.get("releasedate") or "",
        "image": thumb,
        "url": f"https://www.amiami.com/eng/detail/?gcode={gcode}" if gcode else "",
        "source": "amiami",
        "updated": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }


def fetch_brand_franchise(brand, franchise):
    """Fetch all of one brand's items for one franchise, paging through results."""
    query = f"{brand['query_prefix']} {franchise['search']}"
    print(f"Fetching {brand['label']} / {franchise['name']} ...")
    results = []
    page = 1
    per_page = 50
    while True:
        params = {
            "s_keywords": query,
            "pagecnt": page,
            "pagemax": per_page,
            "lang": "eng",
        }
        # s_st_condition_flg=1 tells AmiAmi to include pre-owned listings too
        if INCLUDE_USED:
            params["s_st_condition_flg"] = 1
        data = api_get("items", params)
        if not data or not data.get("RSuccess"):
            break
        items = data.get("items") or []
        if not items:
            break
        for it in items:
            name = (it.get("gname") or "").lower()
            if any(m in name for m in brand["match"]):
                results.append(normalize(it, franchise, brand))
        total = data.get("search_result", {}).get("total_results", 0)
        if page * per_page >= total or page > 20:
            break
        page += 1
        time.sleep(1.0)  # be polite to the API
    print(f"  -> {len(results)} {brand['label']} items")
    return results


def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out_path = os.path.join(here, "data.json")
    manual_path = os.path.join(here, "manual_figures.json")

    all_figures = []
    any_success = False
    seen = set()

    for fr in FRANCHISES:
        for brand in BRANDS:
            items = fetch_brand_franchise(brand, fr)
            if items:
                any_success = True
            for it in items:
                # Dedupe by gcode (an item can appear in multiple searches)
                if it["id"] and it["id"] not in seen:
                    seen.add(it["id"])
                    all_figures.append(it)
            time.sleep(1.2)

    # Merge manual additions/overrides (matched by id). Manual wins.
    manual = load_json(manual_path, [])
    if manual:
        by_id = {f["id"]: f for f in all_figures}
        for m in manual:
            by_id[m["id"]] = {**by_id.get(m["id"], {}), **m}
        all_figures = list(by_id.values())

    # If the live fetch failed entirely, keep the previous data so the site
    # doesn't go blank. Only overwrite when we actually got something.
    if not any_success and not manual:
        print("No data fetched and no manual data; preserving existing data.json.",
              file=sys.stderr)
        existing = load_json(out_path, None)
        if existing is not None:
            return 0
        # nothing at all — write an empty but valid structure
        all_figures = []

    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "franchises": [{"id": f["id"], "name": f["name"]} for f in FRANCHISES],
        "figures": all_figures,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(all_figures)} figures to data.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
