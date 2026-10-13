import os
import re
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*",
    "Content-Type": "application/json",
    "Origin": "https://www.shopgoodwill.com",
    "Referer": "https://www.shopgoodwill.com/"
}

EXCLUDE_TERMS = {
    "monopoly", "scrabble", "clue", "trivial pursuit", "candyland", 
    "chutes", "yahtzee", "bingo", "poker", "chess set", "checkers",
    "scene it", "cranium", "apples to apples", "cards against humanity"
}

def clean_game_title(title):
    cleaned = re.sub(r"(?i)\b(vintage|board game|complete|untested|as-is|lot of|sealed|used|rare|nib|cib|edition|game)\b", "", title)
    words = [w for w in re.sub(r"[^\w\s]", " ", cleaned).split() if len(w) > 2]
    return " ".join(words[:4])

def fetch_goodwill_auctions():
    gw_api = "https://buyerapi.shopgoodwill.com/api/Search/ItemListing"
    seen_ids = set()
    items_found = []

    queries = [
        {"searchText": "board game", "categoryId": 457},
        {"searchText": "tabletop game", "categoryId": 0},
        {"searchText": "vintage board game", "categoryId": 0},
        {"searchText": "miniatures game", "categoryId": 0}
    ]

    for q in queries:
        payload = {
            "searchText": q["searchText"],
            "categoryId": q["categoryId"],
            "page": 1,
            "pageSize": 25,
            "sortColumn": 1,  # Ending soonest
            "sortDescending": False
        }
        try:
            r = requests.post(gw_api, json=payload, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                raw_items = r.json().get("searchResults", {}).get("items", [])
                for itm in raw_items:
                    item_id = str(itm.get("itemId", ""))
                    if not item_id or item_id in seen_ids:
                        continue
                    seen_ids.add(item_id)

                    title = itm.get("title", "")
                    if any(bad in title.lower() for bad in EXCLUDE_TERMS):
                        continue

                    curr_bid = float(itm.get("currentPrice", 0.0))
                    if curr_bid > 55.0:
                        continue

                    clean_name = clean_game_title(title)
                    items_found.append({
                        "id": item_id,
                        "title": title.replace('"', '&quot;'),
                        "clean_name": clean_name,
                        "curr_bid": curr_bid,
                        "img": itm.get("imageURL", "").replace("\\", "/"),
                        "time_left": itm.get("remainingTime", "Ending Soon"),
                        "gw_url": f"https://www.shopgoodwill.com/item/{item_id}",
                        "ebay_url": f"https://www.ebay.com/sch/i.html?_nkw={requests.utils.quote(clean_name)}&LH_Sold=1&LH_Complete=1"
                    })
            time.sleep(0.5)
        except Exception as e:
            print(f"Error fetching {q['searchText']}: {e}")

    return items_found[:40]

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
        .item-cell {{ display: flex; align-items: center; gap: 10px; max-width: 320px; }}
        .thumb {{ width: 44px; height: 44px; object-fit: cover; border-radius: 4px; background: #000; flex-shrink: 0; }}
        .item-title {{ font-weight: 600; line-height: 1.2; font-size: 13px; }}
        .time-tag {{ font-size: 11px; color: var(--profit); margin-top: 2px; }}
        .comp-input {{ width: 75px; background: #0b0f19; border: 1px solid var(--border); color: #fff; padding: 4px 6px; border-radius: 4px; font-size: 13px; font-weight: 600; text-align: right; }}
        .max-bid {{ color: var(--accent); font-weight: 800; font-size: 14px; }}
        .profit {{ color: var(--profit); font-weight: 700; font-size: 14px; }}
        .btn {{ display: inline-block; padding: 5px 10px; border-radius: 4px; font-size: 11px; font-weight: 600; text-decoration: none; margin-right: 4px; }}
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
                <span class="pill">eBay Fees: 13.25% + \$0.30 + \$10 Ship Reserve</span>
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
        const items = {items};

        function calculateMetrics(currBid, compPrice) {{
            const landedCost = currBid + 15.0 + 3.0;
            if (compPrice <= 0) return {{ landedCost, maxBid: 0, profit: 0 }};
            
            // Net eBay Payout after 13.25% fee, \$0.30 fixed fee, and \$10 outbound box/postage reserve
            const netEbay = (compPrice * 0.8675) - 0.30 - 10.0;
            const profit = netEbay - landedCost;
            
            // Formula for Max Bid: [Net Payout / 1.20] - (FedEx Shipping + Handling)
            const maxBid = Math.max(0, (netEbay / 1.20) - 18.0);
            return {{ landedCost, maxBid, profit }};
        }}

        function renderRows() {{
            const tbody = document.getElementById("deal-table");
            tbody.innerHTML = items.map((item, idx) => {{
                // Default benchmark assumption: \$50 fair market value on unverified games
                const defaultComp = 50.0;
                const m = calculateMetrics(item.curr_bid, defaultComp);
                return `
                    <tr id="row-${{idx}}">
                        <td>
                            <div class="item-cell">
                                <img src="${{item.img}}" class="thumb" onerror="this.style.display='none'">
                                <div>
                                    <div class="item-title">${{item.title}}</div>
                                    <div class="time-tag">🟢 Ends: ${{item.time_left}}</div>
                                </div>
                            </div>
                        </td>
                        <td><strong>$${{item.curr_bid.toFixed(2)}}</strong></td>
                        <td id="landed-${{idx}}">$${{m.landedCost.toFixed(2)}}</td>
                        <td>
                            <input type="number" class="comp-input" id="comp-${{idx}}" value="${{defaultComp.toFixed(2)}}" step="5" onchange="updateRow(${{idx}}, ${{item.curr_bid}})">
                            <div class="muted">Edit after checking</div>
                        </td>
                        <td>
                            <span class="max-bid" id="maxbid-${{idx}}">$${{m.maxBid.toFixed(2)}}</span>
                        </td>
                        <td>
                            <span class="profit" id="profit-${{idx}}">+$${{m.profit.toFixed(2)}}</span>
                        </td>
                        <td>
                            <a href="${{item.gw_url}}" target="_blank" class="btn btn-gw">Goodwill ↗</a>
                            <a href="${{item.ebay_url}}" target="_blank" class="btn btn-ebay">Check Sold Comps ↗</a>
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
        # Serializes directly into JSON so the browser handles real-time recalculations
        import json
        f.write(html.replace("{items}", json.dumps(items)))

if __name__ == "__main__":
    deals = fetch_goodwill_auctions()
    generate_html(deals)
    print(f"Generated dashboard with {len(deals)} active Goodwill auctions.")
