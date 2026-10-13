import os
import re
import time
import json
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1"
}

# Negative keywords for mass-market worthless items where FedEx eats 100% of the value
EXCLUDE_TERMS = {
    "monopoly", "scrabble", "clue", "trivial pursuit", "candyland", 
    "chutes", "yahtzee", "bingo", "poker", "chess", "checkers",
    "scene it", "cranium", "apples to apples", "cards against humanity",
    "puzzle", "jigsaw", "dominoes", "connect 4", "battleship"
}

def clean_game_title(title):
    cleaned = re.sub(r"(?i)\b(vintage|board game|complete|untested|as-is|lot of|sealed|used|rare|nib|cib|edition|game|deluxe)\b", "", title)
    words = [w for w in re.sub(r"[^\w\s]", " ", cleaned).split() if len(w) > 2]
    return " ".join(words[:4])

def scrape_shopgoodwill_html():
    items = []
    seen_ids = set()
    
    # ShopGoodwill public category search URL: Category 457 (Board Games), Ending Soonest
    urls = [
        "https://www.shopgoodwill.com/categories/listing?st=&sg=&c=457&s=&lp=0&hp=45&sbn=false&spo=false&snpo=false&socs=false&sd=false&sca=false&sae=0&pn=1&sgst=0&sgcl=0&sortColumn=1&sortDescending=false",
        "https://www.shopgoodwill.com/categories/listing?st=vintage%20board%20game&sg=Keyword&c=&s=&lp=0&hp=45&sbn=false&spo=false&snpo=false&socs=false&sd=false&sca=false&sae=0&pn=1&sgst=0&sgcl=0&sortColumn=1&sortDescending=false"
    ]
    
    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                print(f"Failed to fetch {url}: status {r.status_code}")
                continue
            
            soup = BeautifulSoup(r.text, "html.parser")
            
            # Extract item tiles from standard ShopGoodwill grid
            product_cards = soup.select(".product-card, .feat-item, [data-item-id]")
            
            # If standard cards are not matched, extract using regex from embedded HTML state
            if not product_cards:
                # Fallback: parse raw product links inside HTML
                link_matches = soup.find_all("a", href=re.compile(r"/item/\d+"))
                for link in link_matches:
                    href = link.get("href", "")
                    id_match = re.search(r"/item/(\d+)", href)
                    if not id_match:
                        continue
                    item_id = id_match.group(1)
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    
                    title = link.get_text(strip=True) or link.get("title", "")
                    if not title or len(title) < 5:
                        continue
                        
                    clean_name = clean_game_title(title)
                    if any(bad in title.lower() for bad in EXCLUDE_TERMS):
                        continue
                        
                    items.append({
                        "id": item_id,
                        "title": title.replace('"', '&quot;'),
                        "clean_name": clean_name,
                        "curr_bid": 9.99,  # Default starter bid baseline
                        "img": "",
                        "time_left": "Active Auction",
                        "gw_url": f"https://www.shopgoodwill.com/item/{item_id}",
                        "ebay_url": f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(clean_name)}&LH_Sold=1&LH_Complete=1"
                    })
            else:
                for card in product_cards:
                    link_elem = card.select_one("a[href*='/item/']")
                    if not link_elem:
                        continue
                    href = link_elem.get("href", "")
                    id_match = re.search(r"/item/(\d+)", href)
                    if not id_match:
                        continue
                    item_id = id_match.group(1)
                    if item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)
                    
                    title = link_elem.get_text(strip=True) or card.select_one(".product-title, .title").get_text(strip=True)
                    if any(bad in title.lower() for bad in EXCLUDE_TERMS):
                        continue
                        
                    price_elem = card.select_one(".price, .product-price")
                    curr_bid = 9.99
                    if price_elem:
                        p_match = re.search(r"\$([0-9,]+\.?[0-9]*)", price_elem.get_text())
                        if p_match:
                            curr_bid = float(p_match.group(1).replace(",", ""))
                            
                    img_elem = card.select_one("img")
                    img_url = img_elem.get("src", "") if img_elem else ""
                    
                    time_elem = card.select_one(".countdown, .time-remaining")
                    time_left = time_elem.get_text(strip=True) if time_elem else "Active"
                    
                    clean_name = clean_game_title(title)
                    items.append({
                        "id": item_id,
                        "title": title.replace('"', '&quot;'),
                        "clean_name": clean_name,
                        "curr_bid": curr_bid,
                        "img": img_url,
                        "time_left": time_left,
                        "gw_url": f"https://www.shopgoodwill.com/item/{item_id}",
                        "ebay_url": f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(clean_name)}&LH_Sold=1&LH_Complete=1"
                    })
            time.sleep(1)
        except Exception as e:
            print(f"Error scraping {url}: {e}")
            
    return items[:40]

def generate_html(items):
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Goodwill Board Game Radar</title>
    <style>
        :root {{
            --bg: #0b0f19; --card: #151d30; --border: #222f4c;
            --accent: #38bdf8; --profit: #22c55e; --warn: #f59e0b;
        }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: #f1f5f9; margin: 0; padding: 20px; }}
        .header {{ display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 14px; margin-bottom: 20px; }}
        h1 {{ margin: 0; font-size: 22px; color: var(--accent); }}
        .pills {{ display: flex; gap: 8px; margin-top: 6px; }}
        .pill {{ background: rgba(56, 189, 248, 0.1); border: 1px solid var(--accent); color: var(--accent); font-size: 11px; padding: 3px 8px; border-radius: 99px; }}
        table {{ width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }}
        th {{ background: #111726; color: #94a3b8; font-size: 11px; text-transform: uppercase; padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); }}
        td {{ padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; }}
        tr:hover td {{ background: #1a243c; }}
        .item-cell {{ display: flex; align-items: center; gap: 10px; max-width: 340px; }}
        .thumb {{ width: 44px; height: 44px; object-fit: cover; border-radius: 4px; background: #000; flex-shrink: 0; }}
        .item-title {{ font-weight: 600; line-height: 1.2; font-size: 13px; }}
        .time-tag {{ font-size: 11px; color: var(--profit); margin-top: 2px; }}
        .comp-input {{ width: 75px; background: #0b0f19; border: 1px solid var(--border); color: #fff; padding: 4px 6px; border-radius: 4px; font-size: 13px; font-weight: 600; text-align: right; }}
        .max-bid {{ color: var(--accent); font-weight: 800; font-size: 14px; }}
        .profit {{ color: var(--profit); font-weight: 700; font-size: 14px; }}
        .btn {{ display: inline-block; padding: 6px 12px; border-radius: 4px; font-size: 11px; font-weight: 700; text-decoration: none; margin-right: 4px; }}
        .btn-gw {{ background: var(--warn); color: #000; }}
        .btn-ebay {{ background: #2563eb; color: #fff; }}
        .muted {{ color: #94a3b8; font-size: 11px; }}
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>⚡ Active Goodwill Board Game Arbitrage Radar</h1>
            <div class="pills">
                <span class="pill">Auto-Landed: Bid + \$15 FedEx + \$3 Handling</span>
                <span class="pill">eBay Fees: 13.25% + \$0.30 + \$10 Outbound Ship</span>
                <span class="pill">Min ROI Target: 20%</span>
            </div>
        </div>
    </div>

    <table>
        <thead>
            <tr>
                <th>Active Goodwill Auction</th>
                <th>Current Bid</th>
                <th>Landed Cost</th>
                <th>eBay Sold Comp (\$)</th>
                <th>🎯 Max Bid (for 20% ROI)</th>
                <th>Est. Net Profit</th>
                <th>Quick Actions</th>
            </tr>
        </thead>
        <tbody id="deal-table">
        </tbody>
    </table>

    <script>
        const items = {json.dumps(items)};

        function calculateMetrics(currBid, compPrice) {{
            const landedCost = currBid + 18.0; // \$15 FedEx + \$3 Handling
            if (compPrice <= 0) return {{ landedCost, maxBid: 0, profit: 0 }};
            
            // Net eBay Payout after 13.25% fee, \$0.30 fixed, and \$10 outbound postage
            const netEbay = (compPrice * 0.8675) - 0.30 - 10.0;
            const profit = netEbay - landedCost;
            
            // Algebraic formula for 20% ROI ceiling:
            const maxBid = Math.max(0, (netEbay / 1.20) - 18.0);
            return {{ landedCost, maxBid, profit }};
        }}

        function renderRows() {{
            const tbody = document.getElementById("deal-table");
            if (!items.length) {{
                tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding: 40px; color: #94a3b8;">No auctions active currently. Check back shortly.</td></tr>';
                return;
            }}
            tbody.innerHTML = items.map((item, idx) => {{
                const defaultComp = 45.0; // Standard median comp baseline
                const m = calculateMetrics(item.curr_bid, defaultComp);
                return `
                    <tr id="row-${{idx}}">
                        <td>
                            <div class="item-cell">
                                ${{item.img ? `<img src="\${{item.img}}" class="thumb" onerror="this.style.display='none'">` : ''}}
                                <div>
                                    <div class="item-title">${{item.title}}</div>
                                    <div class="time-tag">🟢 ${{item.time_left}}</div>
                                </div>
                            </div>
                        </td>
                        <td><strong>$${{item.curr_bid.toFixed(2)}}</strong></td>
                        <td id="landed-${{idx}}">$${{m.landedCost.toFixed(2)}}</td>
                        <td>
                            <input type="number" class="comp-input" id="comp-${{idx}}" value="${{defaultComp.toFixed(2)}}" step="5" onchange="updateRow(${{idx}}, ${{item.curr_bid}})">
                            <div class="muted">Click eBay to verify</div>
                        </td>
                        <td>
                            <span class="max-bid" id="maxbid-${{idx}}">$${{m.maxBid.toFixed(2)}}</span>
                        </td>
                        <td>
                            <span class="profit" id="profit-${{idx}}">+$${{m.profit.toFixed(2)}}</span>
                        </td>
                        <td>
                            <a href="${{item.gw_url}}" target="_blank" class="btn btn-gw">Goodwill ↗</a>
                            <a href="${{item.ebay_url}}" target="_blank" class="btn btn-ebay">Check eBay ↗</a>
                        </td>
                    </tr>
                `;
            }}).join('');
        }}

        function updateRow(idx, currBid) {{
            const comp = parseFloat(document.getElementById(`comp-${{idx}}`).value) || 0;
            const m = calculateMetrics(currBid, comp);
            
            const maxBidEl = document.getElementById(`maxbid-${{idx}}`);
            const profitEl = document.getElementById(`profit-${{idx}}`);
            
            maxBidEl.innerText = `$${{m.maxBid.toFixed(2)}}`;
            profitEl.innerText = `${{m.profit >= 0 ? '+' : ''}}$${{m.profit.toFixed(2)}}`;
            profitEl.style.color = m.profit >= 0 ? '#22c55e' : '#ef4444';
        }}

        renderRows();
    </script>
</body>
</html>
"""
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    items = scrape_shopgoodwill_html()
    generate_html(items)
    print(f"Generated dashboard with {len(items)} active Goodwill items.")
