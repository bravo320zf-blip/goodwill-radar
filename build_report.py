import os

HTML_CONTENT = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>⚡ Board Game Arbitrage Radar</title>
    <style>
        :root {
            --bg: #0b0f19; --card: #151d30; --border: #222f4c;
            --accent: #38bdf8; --profit: #22c55e; --warn: #f59e0b; --danger: #ef4444;
            --text: #f1f5f9; --muted: #94a3b8;
        }
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 24px; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--border); padding-bottom: 16px; margin-bottom: 20px; }
        h1 { margin: 0; font-size: 22px; color: var(--accent); }
        .pills { display: flex; gap: 8px; margin-top: 6px; }
        .pill { background: rgba(56, 189, 248, 0.1); border: 1px solid var(--accent); color: var(--accent); font-size: 11px; padding: 3px 8px; border-radius: 99px; }
        
        .top-nav { display: flex; gap: 12px; margin-bottom: 20px; }
        .nav-link { background: #1e293b; color: #fff; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 12px; font-weight: 600; border: 1px solid var(--border); }
        .nav-link:hover { border-color: var(--accent); color: var(--accent); }

        .importer-box { background: var(--card); border: 1px solid var(--border); padding: 16px; border-radius: 8px; margin-bottom: 20px; display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
        .importer-box input { background: #0b0f19; border: 1px solid var(--border); color: #fff; padding: 8px 12px; border-radius: 4px; font-size: 13px; }
        .importer-box input[type="text"] { flex-grow: 1; min-width: 250px; }
        .importer-box input[type="number"] { width: 90px; }
        .btn-add { background: var(--accent); color: #000; font-weight: 700; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; }
        .btn-add:hover { opacity: 0.9; }

        table { width: 100%; border-collapse: collapse; background: var(--card); border-radius: 8px; overflow: hidden; border: 1px solid var(--border); }
        th { background: #111726; color: var(--muted); font-size: 11px; text-transform: uppercase; padding: 12px 14px; text-align: left; border-bottom: 1px solid var(--border); }
        td { padding: 12px 14px; border-bottom: 1px solid var(--border); font-size: 13px; vertical-align: middle; }
        tr:hover td { background: #1a243c; }
        
        .item-title { font-weight: 600; font-size: 14px; color: #fff; }
        .comp-input { width: 80px; background: #0b0f19; border: 1px solid var(--border); color: #fff; padding: 4px 6px; border-radius: 4px; font-size: 13px; font-weight: 600; text-align: right; }
        .max-bid { color: var(--accent); font-weight: 800; font-size: 15px; }
        .profit { color: var(--profit); font-weight: 700; font-size: 14px; }
        .btn { display: inline-block; padding: 6px 10px; border-radius: 4px; font-size: 11px; font-weight: 700; text-decoration: none; margin-right: 4px; }
        .btn-gw { background: var(--warn); color: #000; }
        .btn-ebay { background: #2563eb; color: #fff; }
        .btn-del { background: transparent; border: 1px solid var(--border); color: var(--muted); padding: 4px 8px; border-radius: 4px; cursor: pointer; }
        .btn-del:hover { color: var(--danger); border-color: var(--danger); }
        .zone-pill { display: inline-block; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 700; margin-top: 4px; }
        .zone-green { background: rgba(34, 197, 94, 0.15); color: var(--profit); border: 1px solid var(--profit); }
        .zone-red { background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid var(--danger); }
    </style>
</head>
<body>
    <div class="header">
        <div>
            <h1>⚡ Board Game Arbitrage Radar</h1>
            <div class="pills">
                <span class="pill">Landed = Bid + \$15 FedEx + \$3 Handling</span>
                <span class="pill">eBay Fees = 13.25% + \$0.30 + \$10 Outbound Ship</span>
                <span class="pill">Target ROI = 20%</span>
            </div>
        </div>
    </div>

    <div class="top-nav">
        <a href="https://shopgoodwill.com/categories/board-games" target="_blank" class="nav-link">📂 Open SGW Board Games Category ↗</a>
        <a href="https://www.goodwillfinds.com/search/?q=board+game" target="_blank" class="nav-link">🛍️ Open GoodwillFinds Board Games ↗</a>
        <a href="https://www.ebay.com/sch/i.html?_nkw=vintage+board+game&LH_Sold=1&LH_Complete=1" target="_blank" class="nav-link">📈 eBay Recent Sold Games ↗</a>
    </div>

    <div class="importer-box">
        <strong>⚡ Quick Inspect:</strong>
        <input type="text" id="add-title" placeholder="Game Name (e.g. HeroQuest, Dark Tower, Nemesis)">
        <input type="number" id="add-bid" placeholder="Current Bid \$" value="15.00" step="1">
        <input type="number" id="add-comp" placeholder="eBay Sold \$" value="75.00" step="5">
        <button class="btn-add" onclick="addNewGame()">+ Add to Radar</button>
    </div>

    <table>
        <thead>
            <tr>
                <th>Target Game</th>
                <th>Current Bid</th>
                <th>Landed Cost</th>
                <th>eBay Sold Comp (\$)</th>
                <th>🎯 Max Allowed Bid</th>
                <th>Est. Net Profit</th>
                <th>ROI</th>
                <th>Actions</th>
            </tr>
        </thead>
        <tbody id="deal-table">
        </tbody>
    </table>

    <script>
        const DEFAULT_RADAR = [
            { name: "HeroQuest", curr_bid: 15.00, ebay_comp: 135.00 },
            { name: "Dark Tower", curr_bid: 25.00, ebay_comp: 220.00 },
            { name: "Heroscape", curr_bid: 18.00, ebay_comp: 95.00 },
            { name: "StarCraft board game", curr_bid: 35.00, ebay_comp: 210.00 },
            { name: "Space Hulk", curr_bid: 30.00, ebay_comp: 180.00 },
            { name: "Battlestar Galactica", curr_bid: 20.00, ebay_comp: 140.00 },
            { name: "Kingdom Death", curr_bid: 60.00, ebay_comp: 320.00 },
            { name: "Shadows of Brimstone", curr_bid: 25.00, ebay_comp: 110.00 },
            { name: "Warhammer Quest", curr_bid: 40.00, ebay_comp: 240.00 },
            { name: "Fireball Island", curr_bid: 20.00, ebay_comp: 125.00 },
            { name: "Mansions of Madness", curr_bid: 20.00, ebay_comp: 85.00 }
        ];

        let radarItems = JSON.parse(localStorage.getItem('boardgame_radar_v3')) || DEFAULT_RADAR;

        function calculateMetrics(currBid, compPrice) {
            const landedCost = currBid + 15.0 + 3.0; // \$15 FedEx + \$3 Handling
            if (compPrice <= 0) return { landedCost, maxBid: 0, profit: 0, roi: 0 };
            
            // Net eBay payout after 13.25% fee, \$0.30 fixed, and \$10 outbound postage
            const netEbay = (compPrice * 0.8675) - 0.30 - 10.0;
            const profit = netEbay - landedCost;
            const roi = (profit / landedCost) * 100;
            
            // Formula for Max Bid: [Net Payout / 1.20] - (FedEx Shipping + Handling)
            const maxBid = Math.max(0, (netEbay / 1.20) - 18.0);
            return { landedCost, maxBid, profit, roi };
        }

        function renderRows() {
            const tbody = document.getElementById("deal-table");
            tbody.innerHTML = radarItems.map((item, idx) => {
                const m = calculateMetrics(item.curr_bid, item.ebay_comp);
                const inZone = item.curr_bid <= m.maxBid;
                
                // Uses the standard non-crashing search query format
                const encoded = encodeURIComponent(item.name);
                const gwUrl = `https://shopgoodwill.com/search?st=${encoded}`;
                const ebayUrl = `https://www.ebay.com/sch/i.html?_nkw=${encoded}&LH_Sold=1&LH_Complete=1`;
                
                return `
                    <tr id="row-${idx}">
                        <td>
                            <div class="item-title">${item.name}</div>
                            <span class="zone-pill ${inZone ? 'zone-green' : 'zone-red'}">
                                ${inZone ? '🟢 IN BUY ZONE' : '🔴 OVER MAX BID'}
                            </span>
                        </td>
                        <td>
                            <input type="number" class="comp-input" value="${item.curr_bid.toFixed(2)}" step="1" onchange="updateBid(${idx}, this.value)">
                        </td>
                        <td>$${m.landedCost.toFixed(2)}</td>
                        <td>
                            <input type="number" class="comp-input" value="${item.ebay_comp.toFixed(2)}" step="5" onchange="updateComp(${idx}, this.value)">
                        </td>
                        <td>
                            <span class="max-bid">$${m.maxBid.toFixed(2)}</span>
                        </td>
                        <td>
                            <span class="profit" style="color: ${m.profit >= 0 ? '#22c55e' : '#ef4444'}">
                                ${m.profit >= 0 ? '+' : ''}$${m.profit.toFixed(2)}
                            </span>
                        </td>
                        <td>
                            <strong>${m.roi.toFixed(1)}%</strong>
                        </td>
                        <td>
                            <a href="${gwUrl}" target="_blank" class="btn btn-gw">Goodwill ↗</a>
                            <a href="${ebayUrl}" target="_blank" class="btn btn-ebay">eBay Sold ↗</a>
                            <button class="btn-del" onclick="deleteGame(${idx})">✕</button>
                        </td>
                    </tr>
                `;
            }).join('');
        }

        function updateBid(idx, val) {
            radarItems[idx].curr_bid = parseFloat(val) || 0;
            saveAndRender();
        }

        function updateComp(idx, val) {
            radarItems[idx].ebay_comp = parseFloat(val) || 0;
            saveAndRender();
        }

        function addNewGame() {
            const name = document.getElementById("add-title").value.trim();
            const bid = parseFloat(document.getElementById("add-bid").value) || 15.00;
            const comp = parseFloat(document.getElementById("add-comp").value) || 75.00;
            if (!name) return alert("Please enter a game name.");
            
            radarItems.unshift({ name, curr_bid: bid, ebay_comp: comp });
            document.getElementById("add-title").value = "";
            saveAndRender();
        }

        function deleteGame(idx) {
            radarItems.splice(idx, 1);
            saveAndRender();
        }

        function saveAndRender() {
            localStorage.setItem('boardgame_radar_v3', JSON.stringify(radarItems));
            renderRows();
        }

        renderRows();
    </script>
</body>
</html>
"""

def main():
    os.makedirs("public", exist_ok=True)
    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(HTML_CONTENT)
    print("Static Radar deployed successfully.")

if __name__ == "__main__":
    main()
