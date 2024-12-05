from ocr import ocr 
import cv2
from selenium import webdriver 
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

def predict_map_name(video_path):
    # This just assumes the map name is in the title (e.g. videos from VALORANT DAILY (https://www.youtube.com/@valorantdaily1976/videos))
    # If no map name is found in the video title, prompt user for input instead
    map_list = ["bind", "haven", "split", "ascent", "lotus", "breeze", "icebox", "sunset", "fracture", "pearl"]    
    for map in map_list:
        if map in video_path.lower():
            return map
    
    map = input("Enter map name: ")
    if map.lower() in map_list:
        return map.lower()


# Check the last x frames of the video to read score
def check_score(video_path):
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print("Cannot open video file")
        exit()
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    checking_list = [400, 800, 1200, 1600, 2000, 2400]
    score_found = False
    for i in checking_list:
        if not score_found:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_count - i)
            ret, frame = cap.read()
            cropped_frame_1 = frame[30:70, 770:860]
            cropped_frame_2 = frame[30:70, 1100:1150]
            img_1 = cv2.resize((cropped_frame_1), None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
            img_2 = cv2.resize((cropped_frame_2), None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
            result_1 = ocr(img_1)
            result_2 = ocr(img_2)
            if result_1 and result_2: 
                score_found = True
                return f'{result_1}:{result_2}'
        
def search_score(match_map, player_id, match_score):
    
    # example player_id: SEN tarik#1337
    # edit the string 
    player_id = player_id.replace(' ', '%20')
    player_id = player_id.replace('#', '-')
    
    options = webdriver.ChromeOptions()  
    options.add_argument("--disable-blink-features=AutomationControlled") 
    options.add_experimental_option("excludeSwitches", ["enable-automation"]) 
    options.add_experimental_option("useAutomationExtension", False) 
    
    driver = webdriver.Chrome(options=options) 
    
    # changing the property of the navigator value for webdriver to undefined 
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})") 
    driver.get(f'https://valorant.op.gg/profile/{player_id}') 
    try: 
        # Waiting for divs to load as they don't load immediately 
        element_present = EC.visibility_of_all_elements_located((By.CLASS_NAME, "match-game-score"))
        WebDriverWait(driver, 10).until(element_present) 
        print("Elements ready")
    except TimeoutException:
        print("Loading took too much time, try again!")
    
    match_game_score = driver.find_elements(By.CLASS_NAME, "match-game-score")
    print(len(match_game_score))
    for match in match_game_score:
        map_name = match.find_element(By.CLASS_NAME, "map-name").text.lower()
        score = match.find_element(By.CLASS_NAME, "game-score").text.replace('\n', ':')
       
        if map_name == match_map and score == match_score:
          
            a_tag = match.find_element(By.XPATH, ".//following::div[contains(@class, 'btn-outlink')]//a")
            match_stats_link = a_tag.get_attribute('href')
            return match_stats_link
        
    print("No valid match found. valorant.op.gg may not be updated or the program failed to find the correct link. ")
    match_stats_link = input("Manually key in the link here: ")
    return match_stats_link
    

    # close the driver
    driver.close()

    
        

if __name__ == "__main__":
    score = check_score('/home/ernie/vtok2/mvp! SEN TARIK REYNA VALORANT RANKED MVP GAMEPLAY FULL MATCH VOD.mp4')
    print(score)
    map_name = predict_map_name('/home/ernie/vtok2/mvp! SEN TARIK REYNA VALORANT RANKED MVP GAMEPLAY FULL MATCH VOD.mp4')
    print(search_score(map_name, player_id='SEN tarik#1337', match_score=score))