"""
👑 MEETBOT IPO DEEP INTELLIGENCE & RISK/PROFIT ENGINE
=====================================================
Analyzes ANY requested IPO name on-demand:
1. Searches live market databases (Chittorgarh, IPOWatch, InvestorGain, Google News).
2. Scrapes key financial data: Price band, lot size, dates, issue structure (Fresh vs OFS),
   financial trends (Revenue, PAT, EBITDA, Net Worth), and valuation KPIs (P/E, RoE, RoNW).
3. Analyzes Profit Potential (GMP in ₹ and %, estimated listing gain for 1 lot).
4. Audits Key Risks & Red Flags (Valuation stretch, OFS promoter cash-out, retail trap, sector risks).
5. Issues definitive Godfather Verdict (APPLY / WATCHLIST / AVOID) tailored strictly for Meet Panchal.
"""

import sys
import re
import urllib.parse
import base64
import logging
from typing import Dict, Any, Optional, List, Tuple
import requests
from bs4 import BeautifulSoup
import warnings
from bs4 import XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

import config
import scraper
from scraper import IPODetails, check_parent_company

logger = logging.getLogger("IPOIntelligence")

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Accept-Language': 'en-US,en;q=0.9',
}

def clean_company_query(raw_query: str) -> str:
    """Cleans up queries like 'money view Ltd ipo name' -> 'money view'."""
    q = raw_query.lower()
    # Remove command prefixes or query filler words
    for prefix in ["/ipo", "/check", "/verdict", "/analyze"]:
        if q.startswith(prefix):
            q = q[len(prefix):].strip()

    noise_words = [
        "ipo", "ltd", "limited", "name", "share", "stock", "company",
        "private", "pvt", "details", "check", "tell", "me", "about",
        "review", "gmp", "apply", "or", "not", "risk", "profit", "status"
    ]
    for word in noise_words:
        q = re.sub(rf'\b{word}\b', '', q)

    q = re.sub(r'[^a-zA-Z0-9\s]', ' ', q)
    q = re.sub(r'\s+', ' ', q).strip()
    return q if q else raw_query.strip()


def decode_bing_url(u_param: str) -> str:
    """Decodes Bing redirect parameter u=a1... to original URL."""
    try:
        b64 = u_param[2:] if u_param.startswith('a1') else u_param
        b64 += '=' * ((4 - len(b64) % 4) % 4)
        return base64.b64decode(b64).decode('utf-8', errors='ignore')
    except Exception:
        return ""


def find_chittorgarh_ipo_url(search_term: str) -> Optional[str]:
    """Finds Chittorgarh IPO detail URL via direct dashboard inspection or Bing search."""
    clean_t = search_term.lower().replace(" ", "")

    # 1. Quick check from Chittorgarh mainline report
    try:
        r = requests.get('https://www.chittorgarh.com/report/mainline-ipo-list-in-india-bse-nse/83/', headers=HEADERS, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True).lower().replace(" ", "")
                if '/ipo/' in href and any(c.isdigit() for c in href):
                    if clean_t in text or clean_t in href.lower().replace("-", ""):
                        return href if href.startswith('http') else f"https://www.chittorgarh.com{href}"
    except Exception as e:
        logger.debug(f"Chittorgarh report check note: {e}")

    # 2. Check Chittorgarh dashboard
    try:
        r = requests.get('https://www.chittorgarh.com/ipo/ipo_dashboard.asp', headers=HEADERS, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for a in soup.find_all('a', href=True):
                href = a['href']
                text = a.get_text(strip=True).lower().replace(" ", "")
                if '/ipo/' in href and any(c.isdigit() for c in href):
                    if clean_t in text or clean_t in href.lower().replace("-", ""):
                        return href if href.startswith('http') else f"https://www.chittorgarh.com{href}"
    except Exception as e:
        logger.debug(f"Chittorgarh dashboard check note: {e}")

    # 3. Targeted Bing search
    try:
        q = f"site:chittorgarh.com/ipo/ {search_term} ipo"
        url = f"https://www.bing.com/search?q={urllib.parse.quote(q)}"
        r = requests.get(url, headers=HEADERS, timeout=5)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for b in soup.find_all('li', class_='b_algo'):
                h2 = b.find('h2')
                if not h2:
                    continue
                a = h2.find('a')
                if not a or 'href' not in a.attrs:
                    continue
                href = a['href']
                if 'chittorgarh.com/ipo/' in href:
                    return href
                if 'u=' in href:
                    m = re.search(r'[?&]u=([^&]+)', href)
                    if m:
                        dec = decode_bing_url(m.group(1))
                        if 'chittorgarh.com/ipo/' in dec:
                            return dec
    except Exception as e:
        logger.debug(f"Bing URL extraction note: {e}")

    return None


def scrape_chittorgarh_profile(url: str) -> Dict[str, Any]:
    """Scrapes financial metrics, KPIs, and structure from Chittorgarh IPO page."""
    details = {
        "title": "",
        "sector": "",
        "price_band": "",
        "lower_price": 0.0,
        "upper_price": 0.0,
        "lot_size": 0,
        "total_cost": 0.0,
        "open_date": "",
        "close_date": "",
        "listing_date": "",
        "issue_size": "",
        "fresh_issue": "",
        "ofs": "",
        "pe_pre": "",
        "pe_post": "",
        "roe": "",
        "ronw": "",
        "financials": [],
        "description": "",
        "is_sme": False
    }

    try:
        r = requests.get(url, headers=HEADERS, timeout=8)
        if r.status_code != 200:
            return details

        soup = BeautifulSoup(r.text, 'html.parser')
        details["title"] = soup.title.string.split("IPO")[0].strip() if soup.title else ""
        if "sme" in url.lower() or (soup.title and "sme" in soup.title.string.lower()):
            details["is_sme"] = True

        # Extract company overview description
        for p in soup.find_all('p'):
            txt = p.get_text(strip=True)
            if len(txt) > 80 and not details["description"] and "chittorgarh" not in txt.lower():
                details["description"] = txt

        for t in soup.find_all('table'):
            txt = t.get_text()

            # 1. Issue & Date Table
            if "Price Band" in txt or "Lot Size" in txt or "IPO Date" in txt:
                for row in t.find_all('tr'):
                    cols = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
                    if len(cols) >= 2:
                        k, v = cols[0], cols[1]
                        if "IPO Date" in k:
                            details["open_date"] = v
                        elif "Listing Date" in k:
                            details["listing_date"] = v
                        elif "Price Band" in k:
                            details["price_band"] = v
                            nums = re.findall(r'\d+(?:\.\d+)?', v.replace(',', ''))
                            if len(nums) >= 2:
                                details["lower_price"] = float(nums[0])
                                details["upper_price"] = float(nums[1])
                            elif len(nums) == 1:
                                details["lower_price"] = details["upper_price"] = float(nums[0])
                        elif "Lot Size" in k:
                            m_lot = re.search(r'\d+', v.replace(',', ''))
                            if m_lot:
                                details["lot_size"] = int(m_lot.group())

            # 2. Issue Size Table (Fresh vs OFS)
            if "Total Issue Size" in txt or "Fresh Issue" in txt or "Offer for Sale" in txt:
                for row in t.find_all('tr'):
                    cols = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
                    if len(cols) >= 2:
                        k, v = cols[0], cols[1]
                        if "Total Issue Size" in k:
                            details["issue_size"] = v
                        elif "Fresh Issue" in k:
                            details["fresh_issue"] = v
                        elif "Offer for Sale" in k:
                            details["ofs"] = v

            # 3. Financial Table (Revenue, PAT, EBITDA, Net Worth)
            if ("Profit After Tax" in txt or "PAT" in txt) and "Total Income" in txt:
                rows = t.find_all('tr')
                if len(rows) >= 3:
                    headers_row = [td.get_text(strip=True) for td in rows[0].find_all(['th', 'td'])]
                    for r_idx in range(1, min(len(rows), 8)):
                        cols = [td.get_text(strip=True) for td in rows[r_idx].find_all(['th', 'td'])]
                        if cols:
                            m_name = cols[0]
                            val_latest = cols[1] if len(cols) >= 2 else ""
                            val_prev = cols[2] if len(cols) >= 3 else ""
                            details["financials"].append({
                                "metric": m_name,
                                "latest": val_latest,
                                "prev": val_prev,
                                "period": headers_row[1] if len(headers_row) > 1 else ""
                            })

            # 4. Valuation & KPIs
            if "P/E" in txt or "ROE" in txt or "RoNW" in txt:
                for row in t.find_all('tr'):
                    cols = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
                    if len(cols) >= 2:
                        k = cols[0]
                        if "P/E" in k:
                            details["pe_pre"] = cols[1]
                            if len(cols) >= 3:
                                details["pe_post"] = cols[2]
                        elif "ROE" in k:
                            details["roe"] = cols[1]
                        elif "RoNW" in k:
                            details["ronw"] = cols[1]

        # Determine lot cost
        if details["lot_size"] > 0 and details["upper_price"] > 0:
            details["total_cost"] = round(details["lot_size"] * details["upper_price"], 2)
        elif details["upper_price"] > 0:
            details["lot_size"] = max(1, int(15000 / details["upper_price"]))
            details["total_cost"] = round(details["lot_size"] * details["upper_price"], 2)

    except Exception as e:
        logger.warning(f"Error scraping Chittorgarh page {url}: {e}")

    return details


def fetch_live_news_and_market_signals(search_term: str) -> Dict[str, Any]:
    """Fetches real-time news headlines, GMP signals, and subscription numbers."""
    url = f"https://news.google.com/rss/search?q={urllib.parse.quote(search_term + ' IPO')}&hl=en-IN&gl=IN&ceid=IN:en"
    result = {
        "gmp_val": 0.0,
        "gmp_percent": 0.0,
        "subscription": 0.0,
        "headlines": [],
        "sentiment_score": 0 # positive if > 0
    }

    try:
        r = requests.get(url, headers=HEADERS, timeout=6)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            for it in soup.find_all('item')[:12]:
                title = it.find('title').get_text(strip=True) if it.find('title') else ''
                desc = it.find('description').get_text(strip=True) if it.find('description') else ''
                full_text = f"{title} {desc}"

                # GMP % match (e.g. "GMP signals 41%", "GMP at 38%", "GMP surges 50%")
                if result["gmp_percent"] == 0.0:
                    m_pct = re.search(r'GMP\s*(?:signals|at|of|surges|jumps)?\s*(\d+(?:\.\d+)?)\s*%', full_text, re.IGNORECASE)
                    if m_pct:
                        result["gmp_percent"] = float(m_pct.group(1))

                # GMP in Rs (e.g. "GMP of Rs 85", "GMP at ₹14")
                if result["gmp_val"] == 0.0:
                    m_val = re.search(r'GMP\s*(?:at|of|is)?\s*(?:Rs\.?|₹)\s*(\d+(?:\.\d+)?)', full_text, re.IGNORECASE)
                    if m_val:
                        result["gmp_val"] = float(m_val.group(1))

                # Subscription match (e.g. "subscribed 6 times", "hits 10.4x")
                if result["subscription"] == 0.0:
                    m_sub = re.search(r'subscri(?:bed|ption)?\s*(?:reaches|hits|at|over)?\s*(\d+(?:\.\d+)?)\s*(?:x|times)', full_text, re.IGNORECASE)
                    if m_sub:
                        result["subscription"] = float(m_sub.group(1))

                # Sentiment tags
                lower_text = full_text.lower()
                if any(w in lower_text for w in ["robust", "surges", "strong", "huge demand", "subscribed over", "gain"]):
                    result["sentiment_score"] += 1
                elif any(w in lower_text for w in ["sluggish", "cold", "fails", "weak", "avoid", "caution", "risk"]):
                    result["sentiment_score"] -= 1

                if title and title not in result["headlines"]:
                    result["headlines"].append(title)
    except Exception as e:
        logger.warning(f"Error fetching Google News for {search_term}: {e}")

    return result


def fetch_investorgain_gmp_table() -> List[Dict[str, Any]]:
    """Fetches InvestorGain live GMP table as fallback or corroboration."""
    items = []
    try:
        r = requests.get('https://www.investorgain.com/report/live-ipo-gmp/331/', headers=HEADERS, timeout=6)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            table = soup.find('table')
            if table:
                rows = table.find_all('tr')
                for row in rows[1:]:
                    cols = [td.get_text(strip=True) for td in row.find_all(['th', 'td'])]
                    if len(cols) >= 5:
                        name = cols[0]
                        gmp_str = cols[1]
                        price_str = cols[4]
                        
                        # Extract GMP number and percent
                        m_gmp = re.search(r'₹\s*(\d+)', gmp_str)
                        m_pct = re.search(r'\((\d+(?:\.\d+)?)%\)', gmp_str)
                        m_price = re.search(r'\d+(?:\.\d+)?', price_str)
                        
                        gmp_num = float(m_gmp.group(1)) if m_gmp else 0.0
                        pct_num = float(m_pct.group(1)) if m_pct else 0.0
                        price_num = float(m_price.group()) if m_price else 100.0

                        items.append({
                            "name": name,
                            "gmp": gmp_num,
                            "gmp_percent": pct_num,
                            "price": price_num
                        })
    except Exception as e:
        logger.debug(f"InvestorGain scrape note: {e}")
    return items


def analyze_ipo_comprehensive(user_query: str) -> Dict[str, Any]:
    """
    Core function that aggregates data from all sources and runs deep profit vs risk audit.
    """
    clean_term = clean_company_query(user_query)
    logger.info(f"Auditing IPO: query='{user_query}' -> clean_term='{clean_term}'")

    # 1. Check local bot cache & benchmark list first
    cached_ipo = scraper.get_ipo_by_name(clean_term)

    # 2. Check Chittorgarh profile
    chittor_url = find_chittorgarh_ipo_url(clean_term)
    chittor_data = scrape_chittorgarh_profile(chittor_url) if chittor_url else {}

    # 3. Check Google News live signals
    news_signals = fetch_live_news_and_market_signals(clean_term)

    # 4. Check InvestorGain table
    ig_items = fetch_investorgain_gmp_table()
    ig_match = next((item for item in ig_items if clean_term.lower() in item["name"].lower()), None)

    # Combine data fields
    name = chittor_data.get("title") or (cached_ipo.name if cached_ipo else user_query.strip().title())
    if not name or name == clean_term.title():
        name = f"{clean_term.title()} IPO"

    # Price & Lot
    upper_price = chittor_data.get("upper_price") or (cached_ipo.upper_price if cached_ipo else 0.0)
    lower_price = chittor_data.get("lower_price") or (cached_ipo.lower_price if cached_ipo else upper_price)
    price_band = chittor_data.get("price_band") or (cached_ipo.price_band if cached_ipo else "")
    if not price_band and upper_price > 0:
        price_band = f"₹{int(lower_price)} - ₹{int(upper_price)}" if lower_price != upper_price else f"₹{int(upper_price)}"

    lot_size = chittor_data.get("lot_size") or (cached_ipo.lot_size if cached_ipo else 0)
    if lot_size <= 0 and upper_price > 0:
        lot_size = max(1, int(15000 / upper_price))

    total_cost = chittor_data.get("total_cost") or (cached_ipo.total_cost if cached_ipo else 0.0)
    if total_cost <= 0 and upper_price > 0:
        total_cost = round(upper_price * lot_size, 2)

    # GMP determination
    gmp_percent = 0.0
    gmp_val = 0.0
    if news_signals.get("gmp_percent", 0.0) > 0:
        gmp_percent = news_signals["gmp_percent"]
        if upper_price > 0:
            gmp_val = round((gmp_percent / 100.0) * upper_price, 2)
    elif news_signals.get("gmp_val", 0.0) > 0:
        gmp_val = news_signals["gmp_val"]
        if upper_price > 0:
            gmp_percent = round((gmp_val / upper_price) * 100.0, 2)
    elif ig_match and ig_match.get("gmp_percent", 0.0) > 0:
        gmp_percent = ig_match["gmp_percent"]
        gmp_val = ig_match["gmp"]
    elif cached_ipo:
        gmp_percent = cached_ipo.gmp_percent
        gmp_val = cached_ipo.gmp

    est_profit = round(gmp_val * lot_size, 2) if (gmp_val > 0 and lot_size > 0) else round((gmp_percent / 100.0) * total_cost, 2)

    # Subscription
    subscription = news_signals.get("subscription", 0.0)
    if subscription == 0.0 and cached_ipo:
        subscription = cached_ipo.total_sub

    # Dates
    open_date = chittor_data.get("open_date") or (cached_ipo.open_date if cached_ipo else "Announced / Upcoming")
    listing_date = chittor_data.get("listing_date") or (cached_ipo.listing_date if cached_ipo else "To be announced")

    # Parent company / Shareholder Quota
    parent_company, has_quota = check_parent_company(name)
    if cached_ipo and cached_ipo.parent_company:
        parent_company = cached_ipo.parent_company
        has_quota = True

    # SME detection
    is_sme = chittor_data.get("is_sme", False) or (total_cost > 30000) or ("sme" in name.lower())

    # ==========================================
    # PROFITABILITY & RISK ASSESSMENT LOGIC
    # ==========================================
    profit_signals: List[str] = []
    risk_factors: List[str] = []

    # 1. GMP Profit Potential Evaluation
    if gmp_percent >= 35.0:
        profit_signals.append(f"🔥 <b>Exceptional GMP ({gmp_percent:.1f}%):</b> Expected listing pop of +₹{est_profit:,.0f} per lot. High margin of safety.")
    elif gmp_percent >= 25.0:
        profit_signals.append(f"🟢 <b>Strong Profit Potential ({gmp_percent:.1f}%):</b> Meets MeetBot's threshold (≥ 25%). Estimated gain: +₹{est_profit:,.0f}.")
    elif gmp_percent >= 15.0:
        profit_signals.append(f"🟡 <b>Moderate Listing Gain ({gmp_percent:.1f}%):</b> Modest gain ~₹{est_profit:,.0f}, but vulnerable to listing-day market volatility.")
        risk_factors.append(f"⚠️ <b>Low Margin of Safety:</b> GMP is under 25%. A small dip in secondary indices could erase listing profits.")
    elif gmp_percent > 0:
        risk_factors.append(f"🔴 <b>Subdued Premium ({gmp_percent:.1f}%):</b> Margin of safety is virtually zero. High probability of discount listing.")
    else:
        risk_factors.append("🔴 <b>Zero / Flat GMP:</b> Grey market reports no premium. High capital erosion risk on debut.")

    # 2. Institutional (QIB) & Subscription Evaluation
    if subscription >= 15.0:
        profit_signals.append(f"🏛️ <b>Heavy Institutional Backing ({subscription:.1f}x):</b> Strong demand from anchor funds & big players guarantees post-listing price support.")
    elif subscription >= 5.0:
        profit_signals.append(f"📊 <b>Healthy Subscription ({subscription:.1f}x):</b> Overall issue safely oversubscribed.")
    elif subscription > 0:
        risk_factors.append(f"⚠️ <b>Tepid Overall Demand ({subscription:.1f}x):</b> Waiting for institutional QIB surge on final closing day.")

    # 3. Issue Structure (Fresh Capital vs Offer for Sale / OFS)
    fresh = chittor_data.get("fresh_issue", "")
    ofs = chittor_data.get("ofs", "")
    if fresh and ofs:
        # Check if OFS is dominant
        m_fresh = re.search(r'₹\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*Cr', fresh)
        m_ofs = re.search(r'₹\s*(\d+(?:,\d+)?(?:\.\d+)?)\s*Cr', ofs)
        if m_fresh and m_ofs:
            val_fresh = float(m_fresh.group(1).replace(',', ''))
            val_ofs = float(m_ofs.group(1).replace(',', ''))
            if val_fresh > val_ofs:
                profit_signals.append(f"💼 <b>Growth-Focused Issue:</b> Fresh Issue (₹{val_fresh:.0f} Cr) exceeds OFS (₹{val_ofs:.0f} Cr). Funds go directly into business expansion.")
            else:
                risk_factors.append(f"⚠️ <b>High OFS Component:</b> Existing promoters/VCs are offloading ₹{val_ofs:.0f} Cr shares. Less growth capital retained by the company.")
    elif ofs and not fresh:
        risk_factors.append("⚠️ <b>100% OFS Dump:</b> Entire IPO proceeds go to selling shareholders; ₹0 enters the company's books.")

    # 4. Financial Health & Valuation Evaluation
    financials = chittor_data.get("financials", [])
    revenue_growth_found = False
    pat_growth_found = False
    for f in financials:
        metric = f["metric"].lower()
        latest = f["latest"]
        prev = f["prev"]
        if ("income" in metric or "revenue" in metric) and latest and prev:
            try:
                l_num = float(re.findall(r'\d+(?:\.\d+)?', latest.replace(',', ''))[0])
                p_num = float(re.findall(r'\d+(?:\.\d+)?', prev.replace(',', ''))[0])
                if l_num > p_num:
                    pct = round(((l_num - p_num) / p_num) * 100, 1)
                    profit_signals.append(f"📈 <b>Topline Growth:</b> Revenue grew +{pct}% YoY to ₹{latest} Cr.")
                    revenue_growth_found = True
            except Exception:
                pass
        if ("profit after tax" in metric or "pat" in metric) and latest:
            try:
                l_num = float(re.findall(r'\d+(?:\.\d+)?', latest.replace(',', ''))[0])
                if l_num > 0:
                    profit_signals.append(f"💰 <b>Profitable Operations:</b> Reported positive net profit (PAT) of ₹{latest} Cr.")
                    pat_growth_found = True
                else:
                    risk_factors.append(f"🔴 <b>Loss-Making Operations:</b> Company is operating at a net loss (PAT: ₹{latest} Cr).")
            except Exception:
                pass

    pe_pre = chittor_data.get("pe_pre", "")
    pe_post = chittor_data.get("pe_post", "")
    if pe_post:
        try:
            pe_val = float(re.findall(r'\d+(?:\.\d+)?', pe_post)[0])
            if pe_val > 60:
                risk_factors.append(f"⚠️ <b>Aggressive Valuation:</b> Post-issue P/E of {pe_val:.1f}x leaves little upside room on the table.")
            elif pe_val > 0:
                profit_signals.append(f"⚖️ <b>Reasonable Valuation:</b> Post-issue P/E of {pe_val:.1f}x priced fairly against industry peers.")
        except Exception:
            pass

    # 5. Shareholder Quota Advantage
    if has_quota and parent_company:
        profit_signals.append(f"🏢 <b>Shareholder Quota Double Edge:</b> Parent company <b>{parent_company}</b> is listed on NSE/BSE. Meet can apply in both Retail + Shareholder quota for 2x allotment odds!")

    # 6. Budget & SME Check
    if is_sme:
        risk_factors.append("🚫 <b>SME IPO Violation:</b> Lot cost exceeds standard retail bounds (~₹1,00,000+ required). Violates Meet's ₹14,000 - ₹16,000 capital protocol.")

    # ==========================================
    # MEET'S STRICT 20% - 25% GMP REQUIREMENT CHECK
    # ==========================================
    # User Directive: Only tell to APPLY where GMP is up to 20% to 25%+
    # If GMP < 20%, it does NOT fulfill requirement -> AVOID / DO NOT APPLY
    gmp_meets_requirement = False
    if is_sme:
        requirement_status = "❌ VIOLATES PROTOCOL (SME ISSUE)"
        requirement_text = "SME IPOs require ₹1,00,000+ capital and carry illiquid trading. Violates Meet's ₹15,000 single mainline lot rule."
        verdict = "🔴 AVOID - SME ISSUE (VIOLATES PROTOCOL)"
        verdict_color = "🔴"
        summary_call = "Do NOT apply. MeetBot exclusively tracks mainline issues for maximum liquidity and safety."
    elif gmp_percent >= config.MIN_GMP_PERCENT:  # >= 25%
        gmp_meets_requirement = True
        requirement_status = f"✅ FULLY FULFILLED (+{gmp_percent:.1f}% ≥ 25% Target)"
        requirement_text = f"Current GMP (+{gmp_percent:.1f}%) exceeds your 25% target! Strong profit potential of +₹{est_profit:,.0f} per lot."
        verdict = "🟢 APPLY - HIGH PROFIT CONVICTION (GMP ≥ 25%)"
        verdict_color = "🟢"
        summary_call = f"✅ FULFILLS YOUR REQUIREMENT! GMP is +{gmp_percent:.1f}% (exceeds 25%). Strong listing gains mathematically favored. Apply strictly 1 Retail Lot at cut-off price."
    elif gmp_percent >= config.AVOID_GMP_PERCENT:  # 20% - 25%
        gmp_meets_requirement = True
        requirement_status = f"✅ FULFILLED (+{gmp_percent:.1f}% Meets 20% Minimum)"
        requirement_text = f"Current GMP (+{gmp_percent:.1f}%) satisfies your 20% minimum threshold. Expected profit: +₹{est_profit:,.0f} per lot."
        verdict = "🟢 APPLY - PROFITABLE (MEETS 20%-25% RULE)"
        verdict_color = "🟢"
        summary_call = f"✅ FULFILLS YOUR REQUIREMENT! GMP is +{gmp_percent:.1f}% (within 20%–25% profit range). Profitable and safe to apply 1 Retail Lot at cut-off price."
    elif gmp_percent >= 15.0:  # 15% - 20%
        gmp_meets_requirement = False
        requirement_status = f"⚠️ NOT FULFILLED (+{gmp_percent:.1f}% is Below 20%)"
        requirement_text = f"Current GMP (+{gmp_percent:.1f}%) fails your 20% minimum threshold. Margin of safety is too low."
        verdict = "🔴 AVOID - BELOW YOUR 20% GMP REQUIREMENT"
        verdict_color = "🔴"
        summary_call = f"⚠️ FAILS YOUR 20% REQUIREMENT! GMP is only +{gmp_percent:.1f}% (< 20%). Margin of safety is insufficient. AVOID to preserve capital."
    else:  # < 15%
        gmp_meets_requirement = False
        requirement_status = f"🔴 FAILED (+{gmp_percent:.1f}% is Low / Flat)"
        requirement_text = f"Current GMP (+{gmp_percent:.1f}%) indicates high risk of discount listing."
        verdict = "🔴 AVOID - HIGH RISK / UNPROFITABLE"
        verdict_color = "🔴"
        summary_call = f"❌ DOES NOT FULFILL REQUIREMENT! Subdued GMP (+{gmp_percent:.1f}%). High listing-day capital erosion risk. Strict Avoid."

    return {
        "name": name,
        "clean_term": clean_term,
        "price_band": price_band if price_band else "To be announced",
        "upper_price": upper_price,
        "lot_size": lot_size,
        "total_cost": total_cost,
        "gmp_val": gmp_val,
        "gmp_percent": gmp_percent,
        "est_profit": est_profit,
        "subscription": subscription,
        "open_date": open_date,
        "listing_date": listing_date,
        "issue_size": chittor_data.get("issue_size", ""),
        "fresh_issue": chittor_data.get("fresh_issue", ""),
        "ofs": chittor_data.get("ofs", ""),
        "pe_post": pe_post,
        "has_quota": has_quota,
        "parent_company": parent_company,
        "is_sme": is_sme,
        "profit_signals": profit_signals,
        "risk_factors": risk_factors,
        "gmp_meets_requirement": gmp_meets_requirement,
        "requirement_status": requirement_status,
        "requirement_text": requirement_text,
        "verdict": verdict,
        "verdict_color": verdict_color,
        "summary_call": summary_call,
        "headlines": news_signals.get("headlines", [])[:3],
        "chittor_url": chittor_url
    }


def format_ipo_analysis_report(data: Dict[str, Any]) -> str:
    """
    Renders the complete, beautiful Godfather Telegram HTML report for Meet Panchal.
    """
    name = data["name"]
    verdict = data["verdict"]
    gmp_pct = data["gmp_percent"]
    est_profit = data["est_profit"]
    cost = data["total_cost"]
    price_band = data["price_band"]
    lot_size = data["lot_size"]
    dates = data["open_date"]
    req_status = data.get("requirement_status", "")
    req_text = data.get("requirement_text", "")
    meets_req = data.get("gmp_meets_requirement", False)

    # Budget badge
    if cost > 0:
        budget_str = f"₹{cost:,.0f} (1 Retail Lot)"
        if config.BUDGET_MIN <= cost <= (config.BUDGET_MAX + 1500):
            budget_str += " ✅ Perfect Budget Fit"
        elif cost > 30000:
            budget_str += " ⚠️ Exceeds ₹15k Protocol"
    else:
        budget_str = "Under Final SEBI DRHP Review"

    # Profit potential banner
    if gmp_pct > 0:
        profit_banner = f"<b>+₹{est_profit:,.0f} per lot</b> ({gmp_pct:+.1f}% listing gain)"
    else:
        profit_banner = "Negligible / Unconfirmed"

    # Prominent Requirement Box
    req_box = (
        f"\n🎯 <b>MEET'S 20% – 25% PROFIT REQUIREMENT:</b>\n"
        f"• <b>Your Rule:</b> Minimum <b>+20% to +25% GMP</b> required to apply\n"
        f"• <b>Current GMP:</b> <b>+{gmp_pct:.1f}%</b> (+₹{est_profit:,.0f} est. profit/lot)\n"
        f"• <b>Requirement Check:</b> <b>{req_status}</b>\n"
        f"• <b>Verdict Call:</b> <i>{req_text}</i>\n"
    )

    # Profit signals section
    profit_section = ""
    if data["profit_signals"]:
        items = "\n".join([f"• {s}" for s in data["profit_signals"]])
        profit_section = f"\n💰 <b>WILL IT MAKE YOU PROFIT? (OPPORTUNITIES)</b>\n{items}\n"

    # Risk section
    risk_section = ""
    if data["risk_factors"]:
        items = "\n".join([f"• {r}" for r in data["risk_factors"]])
        risk_section = f"\n⚠️ <b>KEY RISKS & RED FLAGS (CAPITAL THREATS)</b>\n{items}\n"
    else:
        risk_section = "\n🛡️ <b>RISK AUDIT:</b> No major red flags detected. Risk-reward remains favorable.\n"

    # Shareholder Quota banner
    quota_banner = ""
    if data["has_quota"] and data["parent_company"]:
        quota_banner = (
            f"\n🏢 <b>SHAREHOLDER QUOTA EDGE DETECTED!</b>\n"
            f"• Parent Company: <b>{data['parent_company']}</b>\n"
            f"• <i>Action for Meet:</i> Buy 1 parent share before record date for 2x allotment odds!\n"
        )

    # Action Checklist
    if "APPLY" in verdict:
        checklist = (
            f"1. 📱 <b>Broker App:</b> Open Groww or Angel One.\n"
            f"2. 📦 <b>Category & Lot:</b> Select 'Retail', strictly <b>1 Lot</b> ({lot_size} shares).\n"
            f"3. 🎯 <b>Cut-off Price:</b> Check the box <b>'Cut-off Price'</b> (₹{int(data['upper_price']):,}).\n"
            f"4. ⏰ <b>Bid Timing:</b> Submit on Day 3 between 1:00 PM and 3:30 PM IST.\n"
            f"5. ⚡ <b>UPI Mandate:</b> Authorize & enter UPI PIN before 4:30 PM IST sharp!"
        )
    elif "WATCHLIST" in verdict:
        checklist = (
            f"1. ⏸️ <b>DO NOT APPLY EARLY:</b> Wait on sidelines during Day 1 and Day 2.\n"
            f"2. 🔍 <b>Day 3 Audit:</b> MeetBot will check institutional QIB numbers at 1:15 PM.\n"
            f"3. 🛡️ If QIB crosses 25x, Green Light alert will trigger instantly."
        )
    else:
        checklist = (
            f"1. 🚫 <b>DO NOT BID:</b> Capital preservation rule strictly active.\n"
            f"2. 💵 <b>Keep Capital Safe:</b> Protect your ₹15,000 for high-conviction issues.\n"
            f"3. ⚠️ Avoid buying into retail hype without institutional QIB conviction."
        )

    # Live News Headlines
    news_section = ""
    if data["headlines"]:
        h_lines = "\n".join([f"  📰 <i>{h}</i>" for h in data["headlines"][:2]])
        news_section = f"\n📡 <b>LATEST MARKET DISPATCHES:</b>\n{h_lines}\n"

    msg = (
        f"👑 <b>MEETBOT IPO INTELLIGENCE REPORT | {config.TARGET_USER.upper()}</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>Target Issue:</b> {name}\n"
        f"🏷️ <b>Price Band:</b> {price_band}\n"
        f"💵 <b>Investment Needed:</b> {budget_str}\n"
        f"📈 <b>Expected Profit:</b> {profit_banner}\n"
        f"📅 <b>Timeline:</b> {dates} (Listing: {data['listing_date']})\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{req_box}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⚖️ <b>FINAL VERDICT:</b>\n"
        f"<b>{verdict}</b>\n"
        f"<i>{data['summary_call']}</i>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
        f"{profit_section}"
        f"{risk_section}"
        f"{quota_banner}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📝 <b>MEET'S EXECUTION CHECKLIST:</b>\n"
        f"{checklist}\n"
        f"{news_section}"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 <i>MeetBot mathematical risk engine • Single-lot discipline</i>"
    )
    return msg
