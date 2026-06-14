from comp_ocr import ocr
import cv2
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from scraper import make_stealth_driver


def predict_map_name(video_path):
    map_list = [
        "bind", "abyss", "haven", "split", "ascent", "lotus",
        "breeze", "icebox", "sunset", "fracture", "pearl",
    ]
    for m in map_list:
        if m in video_path.lower():
            return m

    m = input("Enter map name: ")
    if m.lower() in map_list:
        return m.lower()


def check_score(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Cannot open video file")
        exit()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    for offset in [400, 800, 1200, 1600, 2000, 2400]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - offset)
        ret, frame = cap.read()
        img1 = cv2.resize(frame[30:70, 770:860], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        img2 = cv2.resize(frame[30:70, 1050:1150], None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
        result_1 = ocr(img1)
        result_2 = ocr(img2)
        if result_1 and result_2:
            return f"{result_1}:{result_2}"


def search_score(match_map, player_id, match_score):
    player_id = player_id.replace(" ", "%20").replace("#", "-")
    driver = make_stealth_driver()
    driver.get(f"https://valorant.op.gg/profile/{player_id}")
    try:
        element_present = EC.visibility_of_all_elements_located(
            (By.CLASS_NAME, "match-game-score")
        )
        WebDriverWait(driver, 10).until(element_present)
        print("Elements ready")
    except TimeoutException:
        print("Loading took too much time, try again!")

    for match in driver.find_elements(By.CLASS_NAME, "match-game-score"):
        map_name = match.find_element(By.CLASS_NAME, "map-name").text.lower()
        score = match.find_element(By.CLASS_NAME, "game-score").text.replace("\n", ":")
        if map_name == match_map and score == match_score:
            print(match_map, match_score)
            a_tag = match.find_element(
                By.XPATH, ".//following::div[contains(@class, 'btn-outlink')]//a"
            )
            match_stats_link = a_tag.get_attribute("href")
            driver.close()
            return match_stats_link

    print("No valid match found.")
    driver.close()
    return input("Manually key in the link here: ")
