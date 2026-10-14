import os
import re
import time
import html
import requests
from bs4 import BeautifulSoup

SCRAPEOPS_KEY = os.environ.get("SCRAPEOPS_API_KEY", "")

EXCLUDE_WORDS = {
    "monopoly", "scrabble", "clue", "trivial pursuit", "candyland", 
    "chutes", "yahtzee", "bingo", "poker", "chess", "checkers",
    "scene it", "cranium", "apples to apples", "cards against humanity",
    "puzzle", "jigsaw", "dominoes", "connect 4", "battleship", "twister"
}

def proxy_get(url):
    """Routes GET requests through ScrapeOps proxy to bypass datacenter IP bans."""
    if SCRAPEOPS_KEY:
        proxy_url = "https://proxy.scrapeops.io/v1/"
        params = {
            "api_key": SCRAPEOPS_KEY,
            "url": url,
            "residential": "true"
        }
        return requests.get(proxy_url, params=params, timeout=25)
    return requests.get(url, timeout=10)

def clean_title(title):
    raw = re.sub(r"(?i)\b(vintage|board game|complete|untested|as-is|lot of|sealed|used|rare|nib|cib|edition|game)\b", "", title)
    words = [w for w in re.sub(r"[^\w\s]", " ", raw).split() if len(w) > 2]
    return " ".join(words[:4])

def fetch_ebay_sold(clean_name):
    if not clean_name or len(clean_name) < 3:
        return 0.0, 0
    query = requests.utils.quote(clean_name)
    url = f"https://www.ebay.com/sch/i.html?_nkw={query}&LH_Sold=1&LH_Complete=1&_sop=12"
    
    try:
        r = proxy_get(url)
        if r.status_code != 200:
            return 0.0, 0
        soup = BeautifulSoup(r.text, "html.parser")
        prices = []
        for e in soup.select(".s-item__price"):
            m = re.search(r"\$([0-9,]+\.?[0-9]*)", e.get_text())
            if m:
                val = float(m.group(1).replace(",", ""))
                if val >= 15.0: # Filter out single replacement dice/cards
                    prices.append(val)
        if len(prices) < 2:
            return 0.0, len(prices)
        prices.sort()
        return prices[len(prices) // 2], len(prices)
    except Exception:
        return 0.0, 0

def fetch_goodwill_live():
    """Hits ShopGoodwill using the residential proxy to bypass Cloudflare WAF."""
    deals = []
    seen = set()
    
    # Target search URLs on ShopGoodwill
    search_queries = ["board game", "vintage board game", "HeroQuest", "Warhammer"]
    
    for term in search_queries:
        encoded = requests.utils.quote(term)
        target_url = f"https://shopgoodwill.com/search?st={encoded}&sortColumn=1&sortDescending=false"
        
        try:
            r = proxy_get(target_url)
            if r.status_code != 200:
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Extract items from page links
            links = soup.find_all("a", href=re.compile(r"/item/\d+"))
            for a in links:
                href = a.get("href", "")
                m_id = re.search(r"/item/(\d+)", href)
                if not m_id:
                    continue
                item_id = m_id.group(1)
                if item_id in seen:
                    continue
                seen.add(item_id)
                
                title = a.get_text(strip=True) or a.get("title", "")
                if len(title) < 5 or any(b in title.lower() for b in EXCLUDE_WORDS):
                    continue
                
                clean_name = clean_title(title)
                ebay_comp, count = fetch_ebay_sold(clean_name)
                
                # Assume standard starting bid if not rendered in HTML
                curr_bid = 9.99
                landed_cost = curr_bid + 15.0 + 3.0 # $15 FedEx + $3 Handling
                
                if count >= 2 and ebay_comp > landed_cost:
                    net_ebay = (ebay_comp * 0.8675) - 0.30 - 10.0 # Fees + Outbound ship
                    profit = net_ebay - landed_cost
                    roi = (profit / landed_cost) * 100 if landed_cost > 0 else 0
                    max_bid = max(0.0, (net_ebay / 1.20) - 18.0)
                    
                    if roi >= 20.0 and profit >= 10.0:
                        deals.append({
                            "title": title,
                            "id": item_id,
                            "curr_bid": curr_bid,
                            "landed": landed_cost,
                            "ebay_comp": ebay_comp,
                            "comps_count": count,
                            "max_bid": max_bid,
                            "profit": profit,
                            "roi": round(roi, 1),
                            "clean_name": clean_name
                        })
            time.sleep(1.0)
        except Exception as e:
            print(f"Error checking {term}: {e}")
            
    deals.sort(key=lambda x: x["profit"], reverse=True)
    return deals[:20]

def build_dashboard(deals):
    rows = ""
    for d in deals:
        safe_title = html.escape(d['title'])
        gw_url = f"https://shopgoodwill.com/item/{d['id']}"
        ebay_url = f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(d['clean_name'])}&LH_Sold=1&LH_Complete=1"
        in_zone = "🟢 In Buy Zone" if d['curr_bid'] <= d['max_bid'] else "🔴 Over Max Bid"
        
        rows += f"""
        <tr>
            <td>
                <strong>{safe_title}</strong>
                <div style="font-size:11px;color:#22c55e;">🟢 Active Auction (ID: {d['id']})</div>
            </td>
            <td>${d['curr_bid']:.2f}</td>
            <td>${d['landed']:.2f}</td>
            <td><strong>${d['ebay_comp']:.2f}</strong> <span style="font-size:11px;color:#94a3b8">({d['comps_count']} sold)</span></td>
            <td><strong style="color:#38bdf8;font-size:15px;">${d['max_bid']:.2f}</strong><br><span style="font-size:11px;">{in_zone}</span></td>
            <td><strong style="color:#22c55e;font-size:15px;">+${d['profit']:.2f}</strong></td>
            <td><span style="background:rgba(34,197,94,0.15);color:#22c55e;border:1px solid #22c55e;padding:2px 6px;border-radius:4px;font-weight:700;">{d['roi']}%</span></td>
            <td>
                <a href="{gw_url}" target="_blank" style="background:#f59e0b;color:#000;padding:6px 10px;border-radius:4px;text-decoration:none;font-size:11px;font-weight:700;display:inline-block;margin-right:4px;">Bid on SGW ↗</a>
                <a href="{ebay_url}" target="_blank" style="background:#2563eb;color:#fff;padding:6px 10px;border-radius:4px;text-decoration:none;font-size:11px;font-weight:700;display:inline-block;">View Comps ↗</a>
            </td>
        </tr>
        """
        
    if not deals:
        rows = '<tr><td colspan="8" style="text-align:center;padding:50px;color:#94a3b8;">Scanning active inventory. Next scan runs automatically at the top of the hour.</td></tr>'

    html_out = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="300">
    <title>⚡ Cloud Board Game Radar</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222f4c; padding-bottom: 16px; margin-bottom: 20px; }}
        h1 {{ margin: 0; font-size: 22px; color: #38bdf8; }}
        .pill {{ background: rgba(56, 189, 248, 0.1); border: 1px solid #38bdf8; color: #38bdf8; font-size: 11px; padding: 3px 8px; border-radius: 99px; margin-right: 6px; }}
        table {{ width: 100%; border-collapse: collapse; background: #151d30; border-radius: 8px; overflow: hidden; border: 1px solid #222f4c; }}
        th {{ background: #111726; color: #94a3b8; font-size: 11px; text-transform: uppercase; padding: 12px 14px; text-align: left; border-bottom: 1px solid #222f4c; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid #222f4c; font-size: 13px; vertical-align: middle; }}
        tr:hover td {{ background: #1a243c; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>⚡ Cloud Board Game Arbitrage Radar</h1>
            <div style="margin-top:6px;">
                <span class="pill">Min 20% Net ROI</span>
                <span class="pill">FedEx $15 + Handling Included</span>
                <span class="pill">100% Serverless Cloud Execution</span>
            </div>
        </div>
    </div>
    <table>
        <thead>
            <tr>
                <th>Live Goodwill Item</th>
                <th>Current Bid</th>
                <th>Landed Cost</th>
                <th>eBay Sold Comp</th>
                <th>🎯 Max Bid (for 20% ROI)</th>
                <th>Est. Net Profit</th>
                <th>Est. ROI</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
</body>
</html>
"""
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html_out)

if __name__ == "__main__":
    deals = fetch_goodwill_live()
    build_dashboard(deals)
