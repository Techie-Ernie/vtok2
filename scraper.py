from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from seleniumbase import Driver


# Returns highlights dict
def comp_scrape_stats(stats_link, min_kills):
    options = webdriver.ChromeOptions()
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=options)

    # changing the property of the navigator value for webdriver to undefined
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    driver.get(f"{stats_link}?tab=Performance")  # Add error checking
    try:
        # Waiting for divs to load as they don't load immediately
        element_present = EC.presence_of_element_located((By.CLASS_NAME, "kills"))
        WebDriverWait(driver, 5).until(element_present)
        print("Elements ready")
    except TimeoutException:
        print("Loading took too much time, try again!")
    kills_div = driver.find_elements(By.CLASS_NAME, "kills")
    number_of_rounds = len(driver.find_elements(By.CLASS_NAME, "round"))
    kills_dict = {}
    for i in range(number_of_rounds):
        kill_spans = kills_div[i + 2].find_elements(
            By.TAG_NAME, "span"
        )  # first 2 'kill' divs do not correspond to the rounds, so skip those
        number_of_kills = len(kill_spans)
        kills_dict[i + 1] = number_of_kills  # Adding to kills dict

    # close the driver
    driver.close()

    highlight_rounds = {}
    for round, kills in kills_dict.items():
        if kills >= min_kills:
            highlight_rounds[round] = kills
    return highlight_rounds


def vct_scrape_stats(stats_link):
    highlight_rounds = {}
    highlights = [
        "3K",
        "4K",
        "5K" "1v2",
        "1v3",
        "1v4",
        "1v5",
    ]

    driver = Driver(uc=True, headless=False)
    driver.uc_open_with_reconnect(f"{stats_link}&roundNumber=1", reconnect_time=7)
    try:
        # Waiting for divs to load as they don't load immediately
        element_present = EC.presence_of_element_located((By.CLASS_NAME, "MuiBox-root"))
        WebDriverWait(driver, 12).until(element_present)
        print("Elements ready")
    except TimeoutException:
        print("Loading took too much time, try again!")
    # kills_div = driver.find_elements(By.CLASS_NAME, "kills")

    # get number of rounds by counting the no. of elements containing the round numbers
    number_of_rounds = (
        len(
            driver.find_elements(
                By.XPATH,
                "/html/body/div[1]/div/div[3]/div[1]/div/div/div[5]/div/div/div/div[2]/div",
            )
        )
        - 2
    )  # One element is halftime and one element is the final score
    print(number_of_rounds)
    for round in range(number_of_rounds):
        if round == 0:  # First round: we don't want to refresh the page again
            pass
        else:
            driver.uc_open_with_reconnect(
                f"{stats_link}&roundNumber={round+1}", reconnect_time=7
            )
        chips = driver.find_elements(By.CLASS_NAME, "MuiChip-label")
        print(f"Round {round+1}: ")
        for chip in chips:
            if chip.text in highlights:
                highlight_rounds[round] = chip.text

    # close the driver
    driver.close()
    print(highlight_rounds)
    return highlight_rounds


if __name__ == "__main__":
    vct_scrape_stats(
        "https://www.rib.gg/series/paper-rex-vs-evil-geniuses-valorant-champions-2023/55475?match=124524&tab=rounds",
    )
