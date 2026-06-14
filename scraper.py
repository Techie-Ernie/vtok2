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


if __name__ == "__main__":
    vct_scrape_stats(
        "https://www.rib.gg/series/paper-rex-vs-evil-geniuses-valorant-champions-2023/55475?match=124524&tab=rounds",
    )
