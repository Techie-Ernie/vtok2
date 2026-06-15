import json
import re
import subprocess
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver


def make_stealth_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def comp_scrape_stats(stats_link, min_kills):
    driver = make_stealth_driver()
    driver.get(f"{stats_link}?tab=Performance")
    try:
        element_present = EC.presence_of_element_located((By.CLASS_NAME, "kills"))
        WebDriverWait(driver, 5).until(element_present)
        print("Elements ready")
    except TimeoutException:
        print("Loading took too much time, try again!")

    kills_div = driver.find_elements(By.CLASS_NAME, "kills")
    number_of_rounds = len(driver.find_elements(By.CLASS_NAME, "round"))
    kills_dict = {}
    for i in range(number_of_rounds):
        kill_spans = kills_div[i + 2].find_elements(By.TAG_NAME, "span")
        kills_dict[i + 1] = len(kill_spans)

    driver.close()

    return {rnd: kills for rnd, kills in kills_dict.items() if kills >= min_kills}


def vct_scrape_stats(stats_link, map_index=1):
    """
    Scrape rib.gg for highlight rounds (4K/5K) by parsing the __NEXT_DATA__ JSON
    embedded in the page — one load instead of one per round.
    """
    driver = Driver(uc=True, headless=False)
    driver.uc_open_with_reconnect(stats_link, reconnect_time=7)

    # Dismiss Cookiebot dialog if it appears
    try:
        deny_btn = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Deny']"))
        )
        deny_btn.click()
        print("Cookie dialog dismissed")
    except TimeoutException:
        pass

    try:
        WebDriverWait(driver, 12).until(
            EC.presence_of_element_located((By.CLASS_NAME, "MuiBox-root"))
        )
    except TimeoutException:
        print("Loading took too much time, try again!")

    src = driver.page_source
    driver.close()

    # Pull all round/event data from Next.js server-side props
    m = re.search(
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        src, re.DOTALL
    )
    if not m:
        print("Could not find __NEXT_DATA__ on rib.gg page")
        return {}

    data = json.loads(m.group(1))
    pp = data["props"]["pageProps"]

    # pageProps.matchId is the match shown (from ?match= URL param)
    match_id = pp.get("matchId")
    matches = pp.get("series", {}).get("matches", [])
    if match_id:
        # URL has ?match=NNN — use that specific match
        target = next((x for x in matches if x["id"] == match_id), None)
    else:
        # No match param — use map_index (1-indexed) to select within the series
        target = matches[min(map_index - 1, len(matches) - 1)] if matches else None
    if not target:
        print("No match data found in rib.gg response")
        return {}

    num_rounds = len(target.get("rounds", []))
    print(f"Total rounds: {num_rounds}")

    # Count kills per player per round from the events array
    events = pp.get("matchDetails", {}).get("events", [])
    round_kills: dict[int, dict[int, int]] = {}
    for event in events:
        if event.get("eventType") == "kill" and event.get("playerId") is not None:
            rnum = event["roundNumber"]
            pid = event["playerId"]
            round_kills.setdefault(rnum, {})
            round_kills[rnum][pid] = round_kills[rnum].get(pid, 0) + 1

    highlight_rounds = {}
    for rnum, player_kills in round_kills.items():
        max_kills = max(player_kills.values())
        if max_kills >= 4:
            highlight_rounds[rnum] = "5K" if max_kills >= 5 else "4K"

    # Collect team names + player IGNs to pass as Whisper vocabulary hints
    vocabulary = []
    series = pp.get("series", {})
    for team_key in ("team1", "team2"):
        team = series.get(team_key) or {}
        for field in ("name", "abbreviation", "shortName"):
            val = team.get(field, "")
            if val and val not in vocabulary:
                vocabulary.append(val)
    for team in series.get("teams", []):
        for field in ("name", "abbreviation", "shortName"):
            val = team.get(field, "")
            if val and val not in vocabulary:
                vocabulary.append(val)
    md = pp.get("matchDetails", {})
    for player in md.get("players", []):
        ign = player.get("ign") or player.get("name") or player.get("username") or ""
        if ign and ign not in vocabulary:
            vocabulary.append(ign)

    print(f"Vocabulary hints: {vocabulary}")
    print(highlight_rounds)
    return highlight_rounds, vocabulary


def vlr_scrape_stats(stats_link, game_num=1):
    """
    Scrape a vlr.gg match page for highlight rounds using plain HTTP (no Selenium).

    vlr.gg does not expose per-round kill counts in its HTML — multi-kill data
    (4K/5K) is only available as per-player aggregates on the performance tab.
    As a best approximation, this returns all elimination-type rounds from maps
    where any player recorded a 4K or 5K. If no multi-kills are found it still
    returns all elimination rounds so clips are never empty.

    Args:
        stats_link: vlr.gg match URL, e.g. https://www.vlr.gg/670464/g2-vs-xlg-...
        game_num:   which map to clip (1 = first map, 2 = second, ...)
    """
    base_url = stats_link.split("?")[0].rstrip("/")
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

    resp = requests.get(base_url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # Ordered list of game IDs from the map nav (excludes the "all" tab)
    game_ids = [
        item.get("data-game-id")
        for item in soup.find_all(class_="vm-stats-gamesnav-item")
        if item.get("data-game-id") and item.get("data-game-id") != "all"
    ]
    if not game_ids:
        print("No maps found on this vlr.gg page.")
        return {}
    if not (1 <= game_num <= len(game_ids)):
        print(f"Game {game_num} not found — match has {len(game_ids)} map(s).")
        return {}

    game_id = game_ids[game_num - 1]

    # --- Rounds from base page (server-side rendered) ---
    game_div = soup.find("div", attrs={"class": "vm-stats-game", "data-game-id": game_id})
    rounds_div = game_div.find(class_="vlr-rounds") if game_div else None

    elim_rounds = {}
    total_rounds = 0
    if rounds_div:
        for row in rounds_div.find_all(class_="vlr-rounds-row"):
            for col in row.find_all(class_="vlr-rounds-row-col"):
                if "mod-spacing" in (col.get("class") or []):
                    continue
                rnd_el = col.find(class_="rnd-num")
                if not rnd_el or not rnd_el.get_text(strip=True).isdigit():
                    continue
                total_rounds += 1
                win_sq = next(
                    (sq for sq in col.find_all(class_="rnd-sq") if "mod-win" in sq.get("class", [])),
                    None,
                )
                if win_sq:
                    img = win_sq.find("img")
                    win_type = img["src"].split("/")[-1].replace(".webp", "") if img else ""
                    if win_type == "elim":
                        elim_rounds[total_rounds] = "4K"

    # --- Advanced stats from performance tab ---
    perf_url = f"{base_url}/?game={game_id}&tab=performance"
    perf_resp = requests.get(perf_url, headers=headers, timeout=15)
    perf_soup = BeautifulSoup(perf_resp.text, "lxml")

    has_multikill = False
    for adv_table in perf_soup.find_all("table", class_="mod-adv-stats"):
        col_headers = [th.get_text(strip=True) for th in adv_table.find_all("th")]
        for col_name in ("4K", "5K"):
            if col_name not in col_headers:
                continue
            idx = col_headers.index(col_name)
            for row in adv_table.find_all("tr"):
                cells = row.find_all("td")
                if idx < len(cells) and cells[idx].get_text(strip=True).isdigit():
                    if int(cells[idx].get_text(strip=True)) > 0:
                        has_multikill = True
                        break
            if has_multikill:
                break
        if has_multikill:
            break

    if not has_multikill:
        print("No 4K/5K found in advanced stats; returning all elimination rounds.")

    # Collect team names + player IGNs from the performance page
    vocabulary = []
    for tag in soup.select(".match-header-link-name .wf-title-med"):
        name = tag.get_text(strip=True)
        if name and name not in vocabulary:
            vocabulary.append(name)
    for tag in perf_soup.select(".mod-player .text-of"):
        ign = tag.get_text(strip=True)
        if ign and ign not in vocabulary:
            vocabulary.append(ign)

    print(f"Vocabulary hints: {vocabulary}")
    print(f"Highlight rounds: {len(elim_rounds)} elimination rounds out of {total_rounds} total")
    print(elim_rounds)
    return elim_rounds, vocabulary


def _rib_url_from_search(team1, team2):
    """
    Search DuckDuckGo for a rib.gg series page containing both team names.
    DuckDuckGo's plain HTML endpoint is scraper-friendly and covers all
    indexed rib.gg pages, including old matches not on rib.gg/matches.
    DDG wraps result URLs in //duckduckgo.com/l/?uddg=ENCODED_URL redirects,
    so we decode the uddg parameter to get the real URL.
    """
    query = f'site:rib.gg "{team1}" "{team2}"'
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "duckduckgo.com/l/" in href:
            parsed = urlparse("https:" + href)
            real_url = parse_qs(parsed.query).get("uddg", [None])[0]
            if real_url:
                href = unquote(real_url)
        if "rib.gg/series/" in href:
            if "?" not in href:
                href += "?tab=rounds"
            return href
    return None


def vlr_to_rib(vlr_url):
    """
    Given a vlr.gg match URL, find and return the corresponding rib.gg URL.

    Strategy:
    1. Fetch the vlr.gg page (plain HTTP) to extract both team names.
    2. Open rib.gg/matches with Selenium and look for a matching series link
       (fast path — works for recent matches).
    3. If not found, fall back to a DuckDuckGo site-search which covers all
       historical rib.gg pages.

    Returns the rib.gg series URL string, or None if not found on either path.
    """
    base_url = vlr_url.split("?")[0].rstrip("/")
    headers = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36"}

    resp = requests.get(base_url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    teams = []
    for mod in ("mod-1", "mod-2"):
        el = soup.select_one(f".match-header-link-name.{mod}")
        if el:
            lines = [ln.strip() for ln in el.get_text().splitlines() if ln.strip()]
            if lines:
                teams.append(lines[0])

    if len(teams) < 2:
        print("Could not extract team names from vlr.gg page.")
        return None

    print(f"Searching rib.gg for: {teams[0]} vs {teams[1]}")
    tokens = [t.lower().split()[0] for t in teams]

    # --- Step 1: rib.gg/matches via Selenium (recent matches) ---
    result = None
    driver = Driver(uc=True, headless=False)
    try:
        driver.uc_open_with_reconnect("https://www.rib.gg/matches", reconnect_time=7)
        try:
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/series/')]"))
            )
            for link in driver.find_elements(By.XPATH, "//a[contains(@href, '/series/')]"):
                href = link.get_attribute("href") or ""
                if all(tok in link.text.lower() for tok in tokens):
                    result = href
                    break
        except TimeoutException:
            print("rib.gg/matches did not load in time.")
    finally:
        driver.close()

    if result:
        print(f"Found on rib.gg/matches: {result}")
        return result

    # --- Step 2: DuckDuckGo site-search (historical matches) ---
    print("Not on recent matches page — trying DuckDuckGo site search...")
    result = _rib_url_from_search(teams[0], teams[1])

    if result:
        print(f"Found via search: {result}")
    else:
        print(
            f"No rib.gg page found for '{teams[0]}' vs '{teams[1]}'. "
            "The match may not be tracked on rib.gg."
        )
    return result


def _search_vlr_match_url(team1, team2, event_hint=""):
    """
    Search DuckDuckGo for a vlr.gg MATCH page (not a news article).
    Match pages have '-vs-' in their URL slug; news articles do not.
    """
    query = f'site:vlr.gg "{team1}" "{team2}"'
    if event_hint:
        query += f' "{event_hint}"'
    resp = requests.get(
        "https://html.duckduckgo.com/html/",
        params={"q": query},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=15,
    )
    soup = BeautifulSoup(resp.text, "lxml")
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "duckduckgo.com/l/" in href:
            parsed = urlparse("https:" + href)
            real_url = parse_qs(parsed.query).get("uddg", [None])[0]
            if real_url:
                href = unquote(real_url)
        # Match pages have team1-vs-team2 in the slug; articles don't
        if re.search(r'vlr\.gg/\d+/[^/?]+-vs-[^/?]+', href):
            return href.split("?")[0].rstrip("/")
    return None


def auto_detect_stats_links(youtube_url, num_maps, log=print):
    """
    Fetch the YouTube video title via yt-dlp, extract the 'X vs Y' team names,
    search vlr.gg for the match, and return a list of {stats_link, stats_map_num}
    pre-populated for every map (same URL, incrementing map number).
    Falls back to empty entries if detection fails at any step.
    """
    empty = [{"stats_link": "", "stats_map_num": i + 1} for i in range(num_maps)]

    log("Fetching video metadata...")
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-download", "--no-playlist", youtube_url],
            capture_output=True, text=True, timeout=30,
        )
    except Exception as e:
        log(f"yt-dlp failed: {e}")
        return empty

    if result.returncode != 0 or not result.stdout.strip():
        log("Could not fetch video metadata.")
        return empty

    meta = json.loads(result.stdout)
    title = meta.get("title", "")
    log(f"Title: {title}")

    # Parse "Team A vs Team B" — stop at common delimiters (|, -, ,, or end of string)
    m = re.search(
        r'([A-Za-z0-9][\w\s\.]+?)\s+[Vv][Ss]\.?\s+([\w\s\.]+?)(?:\s*[|\-,]|$)',
        title,
    )
    if not m:
        log("No 'X vs Y' pattern found in title — cannot auto-detect.")
        return empty

    team1, team2 = m.group(1).strip(), m.group(2).strip()
    log(f"Detected teams: {team1} vs {team2}")

    # Use everything after the first delimiter as event hint for more precise search
    event_hint = ""
    after = re.search(r'[|\-,]\s*(.+)', title)
    if after:
        event_hint = after.group(1).strip()

    # Step 1: find the vlr.gg match page (vlr.gg indexes abbreviations like EDG/FUT,
    # and match page slugs always contain '-vs-' which filters out news articles)
    log("Searching vlr.gg for match page...")
    vlr_url = _search_vlr_match_url(team1, team2, event_hint)
    if not vlr_url:
        # Retry without event hint in case it was too specific
        vlr_url = _search_vlr_match_url(team1, team2)
    if not vlr_url:
        log(f"No vlr.gg match page found for '{team1}' vs '{team2}'.")
        return empty
    log(f"Found vlr.gg match: {vlr_url}")

    # Step 2: vlr_to_rib fetches full team names from the vlr page and searches
    # rib.gg for the corresponding series (handles abbreviation → full name mapping)
    log("Looking up rib.gg series...")
    rib_url = vlr_to_rib(vlr_url)
    if not rib_url:
        log("No rib.gg series found — try pasting the stats link manually.")
        return empty

    # Strip match param so vct_scrape_stats selects the map via map_index
    rib_url = rib_url.split("?")[0] + "?tab=rounds"
    log(f"Found rib.gg series: {rib_url}")
    return [{"stats_link": rib_url, "stats_map_num": i + 1} for i in range(num_maps)]


if __name__ == "__main__":
    vlr_scrape_stats("https://www.vlr.gg/670464/g2-esports-vs-xi-lai-gaming-valorant-masters-london-2026-ubqf/", game_num=1)
