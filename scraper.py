from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


# Returns highlights dict
def scrape_stats(stats_link, min_kills):
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


if __name__ == "__main__":
    link = input("Stats link: ")
    print(scrape_stats(link, min_kills=3))
