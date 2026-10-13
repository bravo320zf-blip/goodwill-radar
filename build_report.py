import os
import re
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.shopgoodwill.com",
    "Referer": "https://www.shopgoodwill.com/"
}

TARGET_GAMES = [
    "HeroQuest", "Dark Tower", "Heroscape", "StarCraft Board Game",
    "Space Hulk", "Battlestar Galactica", "Shadows of Brimstone",
    "Fireball Island", "Kingdom Death", "Warhammer Quest",
    "Dune Board Game", "Mansions of Madness", "Catan 3D", "Nemesis Board Game"
]

def clean_game_title(title):
    title = re.sub(r"(?i)\b(vintage|board game|complete|untested|as-is|lot of|sealed|used|rare|nib|cib)\b", "", title)
    return " ".join(re.sub(r"[^\w\s]", " ", title).split()[:4])

def fetch_ebay_sold(clean_title):
    encoded = requests.utils.quote(clean_title)
    url = f"https://www.ebay.com/sch/i.html?_nkw={encoded}&LH_Sold=1&LH_Complete=1&_sop=12"
    try:
        r = requests.get(url, headers={"User-Agent": HEADERS["User-Agent"]}, timeout=8)
        if r.status_code != 200: 
            return 0.0, 0
        soup = BeautifulSoup(r.text, "html.parser")
        prices = [float(re.search(r"\$([0-9,]+\.?[0-9]*)", e.get_text()).group(1).replace(",", "")) 
                  for e in soup.select(".s-item__price") if re.search(r"\$([0-9,]+\.?[0-9]*)", e.get_text())]
        prices = [p for p in prices if p >= 15.0]
        if not prices: 
            return 0.0, 0
        prices.sort()
        return prices[len(prices) // 2], len(prices)
    except Exception:
        return 0.0, 0

def scan_shopgoodwill():
    gw_api = "https://buyerapi.shopgoodwill.com/api/Search/ItemListing"
    seen_ids = set()
    deals = []
    
    for query in TARGET_GAMES:
        try:
            payload = {
                "searchText": query,
                "page": 1,
                "pageSize": 6,
                "sortColumn": 1, # Ending soonest
                "sortDescending": False
            }
            res = requests.post(gw_api, json=payload, headers=HEADERS, timeout=10)
            if res.status_code != 200:
                continue
            items = res.json().get("searchResults", {}).get("items", [])
            for itm in items:
                item_id = str(itm.get("itemId", ""))
                if not item_id or item_id in seen_ids:
                    continue
                seen_ids.add(item_id)
                
                title = itm.get("title", "")
                curr_bid = float(itm.get("currentPrice", 0.0))
                end_time = itm.get("remainingTime", "Active")
                img_url = itm.get("imageURL", "").replace("\\", "/")
                
                landed_cost = curr_bid + 15.0 + 3.0  # $15 FedEx + $3 Handling
                clean_name = clean_game_title(title)
                ebay_avg, comps = fetch_ebay_sold(clean_name)
                
                if comps >= 2 and ebay_avg > 0:
                    # Net eBay payout after 13.25% fee, $0.30 fixed, and $10 outbound postage reserve
                    net_ebay = (ebay_avg * 0.8675) - 0.30 - 10.0
                    profit = net_ebay - landed_cost
                    roi = (profit / landed_cost) * 100 if landed_cost > 0 else 0
                    
                    # Formula for Max Allowed Bid to hit 20% Net Profit:
                    max_bid = max(0.0, (net_ebay / 1.20) - 18.0)
                    
                    if roi >= 20.0 and profit >= 15.0:
                        deals.append({
                            "title": title,
                            "img": img_url,
                            "curr_bid": curr_bid,
                            "landed_cost": landed_cost,
                            "ebay_avg": ebay_avg,
                            "comps": comps,
                            "max_bid": max_bid,
                            "profit": profit,
                            "roi": round(roi, 1),
                            "end_time": end_time,
                            "gw_url": f"https://www.shopgoodwill.com/item/{item_id}",
                            "ebay_url": f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(clean_name)}&LH_Sold=1&LH_Complete=1"
                        })
            time.sleep(0.5)
        except Exception:
            continue
            
    deals.sort(key=lambda x: x["profit"], reverse=True)
    return deals[:15]

def generate_html(deals):
    rows = ""
    for d in deals:
        in_zone = "🟢 In Buy Zone" if d['curr_bid'] <= d['max_bid'] else "🔴 Over Max Bid"
        rows += f"""
        <tr>
            <td>
                <div class="item-cell">
                    <img src="{d['img']}" class="thumb" onerror="this.style.display='none'">
                    <div>
                        <div class="item-title">{d['title']}</div>
                        <div class="time-tag">Ends: {d['end_time']}</div>
                    </div>
                </div>
            </td>
            <td><strong>${d['curr_bid']:.2f}</strong></td>
            <td>${d['landed_cost']:.2f}</td>
            <td><strong>${d['ebay_avg']:.2f}</strong> <span class="muted">({d['comps']} sold)</span></td>
            <td><strong class="target-bid">${d['max_bid']:.2f}</strong><br><span class="zone-tag">{in_zone}</span></td>
            <td><strong class="profit">+${d['profit']:.2f}</strong></td>
            <td><span class="roi">{d['roi']}%</span></td>
            <td>
                <a href="{d['gw_url']}" target="_blank" class="btn btn-gw">Open Goodwill ↗</a>
                <a href="{d['ebay_url']}" target="_blank" class="btn btn-ebay">View Comps ↗</a>
            </td>
        </tr>
        """
        
    if not deals:
        rows = '<tr><td colspan="8" style="text-align:center; padding: 40px; color: #94a3b8;">No auctions currently meet the 20%+ ROI threshold. Check back on the next scheduled run.</td></tr>'

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Goodwill Board Game Radar</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0b0f19; color: #f1f5f9; margin: 0; padding: 24px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #222f4c; padding-bottom: 16px; margin-bottom: 20px; }}
        h1 {{ margin: 0; font-size: 22px; color: #38bdf8; }}
        .pills {{ display: flex; gap: 8px; margin-top: 6px; }}
        .pill {{ background: rgba(56, 189, 248, 0.1); border: 1px solid #38bdf8; color: #38bdf8; font-size: 12px; padding: 3px 8px; border-radius: 99px; }}
        table {{ width: 100%; border-collapse: collapse; background: #151d30; border-radius: 8px; overflow: hidden; border: 1px solid #222f4c; }}
        th {{ background: #111726; color: #94a3b8; font-size: 11px; text-transform: uppercase; padding: 12px 14px; text-align: left; border-bottom: 1px solid #222f4c; }}
        td {{ padding: 12px 14px; border-bottom: 1px solid #222f4c; font-size: 13px; vertical-align: middle; }}
        tr:hover td {{ background: #1a243c; }}
        .item-cell {{ display: flex; align-items: center; gap: 10px; max-width: 320px; }}
        .thumb {{ width: 44px; height: 44px; object-fit: cover; border-radius: 4px; background: #000; }}
        .item-title {{ font-weight: 600; line-height: 1.2; font-size: 13px; }}
        .time-tag {{ font-size: 11px; color: #22c55e; margin-top: 2px; }}
        .target-bid {{ color: #38bdf8; font-size: 15px; }}
        .zone-tag {{ font-size: 11px; }}
        .profit {{ color: #22c55e; font-size: 14px; }}
        .roi {{ background: rgba(34, 197, 94, 0.15); color: #22c55e; border: 1px solid #22c55e; padding: 2px 6px; border-radius: 4px; font-weight: 700; font-size: 11px; }}
        .btn {{ display: inline-block; padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-decoration: none; margin-right: 4px; }}
        .btn-gw {{ background: #f59e0b; color: #000; }}
        .btn-ebay {{ background: #2563eb; color: #fff; }}
        .muted {{ color: #94a3b8; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>⚡ Goodwill to eBay Board Game Radar</h1>
            <div class="pills">
                <span class="pill">Min 20% Net ROI</span>
                <span class="pill">FedEx $15 Included</span>
                <span class="pill">Auto-updates every 30m</span>
            </div>
        </div>
    </div>
    <table>
        <thead>
            <tr>
                <th>Active Item</th>
                <th>Current Bid</th>
                <th>Landed Cost</th>
                <th>eBay Comp</th>
                <th>Max Allowed Bid</th>
                <th>Net Profit</th>
                <th>ROI</th>
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
        f.write(html)

if __name__ == "__main__":
    deals = scan_shopgoodwill()
    generate_html(deals)
    print(f"Generated dashboard with {len(deals)} profitable deals.")
