import requests
from bs4 import BeautifulSoup
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


def vct_scrape_stats(stats_link):
    highlight_rounds = {}
    highlights = ["4K"]
    driver = Driver(uc=True, headless=False)
    driver.uc_open_with_reconnect(f"{stats_link}&roundNumber=1", reconnect_time=7)
    try:
        element_present = EC.presence_of_element_located((By.CLASS_NAME, "MuiBox-root"))
        WebDriverWait(driver, 12).until(element_present)
        print("Elements ready")
    except TimeoutException:
        print("Loading took too much time, try again!")

    number_of_rounds = (
        len(
            driver.find_elements(
                By.XPATH,
                "/html/body/div[1]/div/div[3]/div[1]/div/div/div[5]/div/div/div/div[2]/div",
            )
        )
        - 2
    )
    print(number_of_rounds)
    for rnd in range(number_of_rounds):
        if rnd > 0:
            driver.uc_open_with_reconnect(
                f"{stats_link}&roundNumber={rnd + 1}", reconnect_time=7
            )
        chips = driver.find_elements(By.CLASS_NAME, "MuiChip-label")
        for chip in chips:
            if chip.text in highlights:
                highlight_rounds[rnd + 1] = chip.text

    driver.close()
    print(highlight_rounds)
    return highlight_rounds


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

    print(f"Highlight rounds: {len(elim_rounds)} elimination rounds out of {total_rounds} total")
    print(elim_rounds)
    return elim_rounds


if __name__ == "__main__":
    vlr_scrape_stats("https://www.vlr.gg/670464/g2-esports-vs-xi-lai-gaming-valorant-masters-london-2026-ubqf/", game_num=1)
