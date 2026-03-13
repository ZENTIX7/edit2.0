import os
import sys
import time
import random
import json
import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- ANSI Color Codes ---
CYAN, MAGENTA, GREEN, BLUE, YELLOW, RED, RESET = '\033[96m', '\033[95m', '\033[92m', '\033[94m', '\033[93m', '\033[91m', '\033[0m'

# --- Configuration ---
CONFIG_FILE = "config.json"
SITE_URL = "https://zefame.com/free-instagram-views"
INPUT_XPATH = "/html/body/div[4]/section[1]/div/div[1]/div[2]/div/form/div/input"
BTN_XPATH = "/html/body/div[4]/section[1]/div/div[1]/div[2]/div/form/div/button"

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {"webhook_url": "", "video_url": "", "headless": True, "boosts": 1}

def send_discord_msg(webhook_url, cycle, total_boosts, start_time):
    if not webhook_url or webhook_url.strip() == "":
        return
    elapsed_seconds = time.time() - start_time
    time_running = time.strftime('%H:%M:%S', time.gmtime(elapsed_seconds))
    total_views = cycle * 300
    cycles_left = total_boosts - cycle
    payload = {
        "username": "Zefame Booster Bot",
        "embeds": [{
            "title": "🚀 Cycle Completion Update",
            "color": 5763719, 
            "fields": [
                {"name": "Current Cycle", "value": f"{cycle} / {total_boosts}", "inline": True},
                {"name": "Total Views Added", "value": f"{total_views}", "inline": True},
                {"name": "Total Runtime", "value": f"{time_running}", "inline": False},
                {"name": "Cycles Remaining", "value": f"{cycles_left}", "inline": True}
            ],
            "footer": {"text": "Discord: 7pce"}
        }]
    }
    try:
        requests.post(webhook_url, json=payload, timeout=10)
    except:
        pass

def live_countdown(seconds, message):
    for remaining in range(seconds, 0, -1):
        mins, secs = divmod(remaining, 60)
        sys.stdout.write(f"\r{MAGENTA}[*] {message}: {YELLOW}{mins:02d}:{secs:02d}{RESET} left   ")
        sys.stdout.flush()
        time.sleep(1)
    print(f"\r{GREEN}[+] {message}: Finished!{' ' * 15}{RESET}")

def run_automation(config):
    print(f"\n{GREEN}[+] Initializing Browser (Headless: {config['headless']})...{RESET}")
    options = webdriver.ChromeOptions()
    if config['headless']:
        options.add_argument("--headless=new")
    
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
    
    driver = webdriver.Chrome(options=options)
    start_time = time.time()

    for cycle in range(1, config['boosts'] + 1):
        os.system('cls' if os.name == 'nt' else 'clear')
        print(f"{CYAN}--- ACTIVE BOOSTING: {cycle}/{config['boosts']} ---{RESET}\n")
        try:
            driver.get(SITE_URL)
            input_box = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.XPATH, INPUT_XPATH)))
            input_box.clear()
            
            for char in config['video_url']:
                input_box.send_keys(char)
                time.sleep(random.uniform(0.04, 0.09))
            
            time.sleep(1)
            btn = driver.find_element(By.XPATH, BTN_XPATH)
            driver.execute_script("arguments[0].click();", btn)
            
            live_countdown(60, "Website Processing")
            send_discord_msg(config['webhook_url'], cycle, config['boosts'], start_time)
            live_countdown(360, "Cooldown Timer")
            
        except Exception as e:
            print(f"{RED}[!] ERROR DURING CYCLE {cycle}: {e}{RESET}")
            time.sleep(10)
            
    driver.quit()
    input(f"\n{GREEN}[+] All cycles complete! Press Enter to return to menu.{RESET}")

def main():
    os.system('') # Enable colors
    config = load_config()

    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        total_seconds = config['boosts'] * 362 
        est_time = time.strftime('%H:%M:%S', time.gmtime(total_seconds))
        
        print(f"{CYAN}--- ZEFAME BOOSTER (Discord: 7pce) ---{RESET}")
        print(f"{MAGENTA}1. VIDEO URL:  {RESET}{config['video_url'] if config['video_url'] else RED + '[NOT SET]'}")
        print(f"{MAGENTA}2. WEBHOOK:    {RESET}{config['webhook_url'] if config['webhook_url'] else RED + '[NOT SET]'}")
        print(f"{MAGENTA}3. BOOSTS:     {RESET}{config['boosts']} ({config['boosts'] * 300} Views)")
        print(f"{MAGENTA}4. BROWSER:    {RESET}{'HIDDEN (Headless)' if config['headless'] else 'VISIBLE (Windowed)'}")
        print(f"{MAGENTA}EST. RUNTIME:  {RESET}{YELLOW}{est_time}{RESET}")
        print(f"{CYAN}--------------------------------------{RESET}")
        print(f"{GREEN}[S] START BOOSTING{RESET}")
        print(f"{BLUE}[C] CHANGE ALL SETTINGS{RESET}")
        print(f"{BLUE}[T] TOGGLE BROWSER VISIBILITY{RESET}")
        print(f"{RED}[E] EXIT{RESET}")

        choice = input("\n-> ").lower()

        if choice == 's':
            if not config['video_url']:
                print(f"{RED}[!] Set a video URL first!{RESET}")
                time.sleep(2)
                continue
            run_automation(config)
            
        elif choice == 'c':
            config['video_url'] = input(f"\n{BLUE}Enter Instagram URL: {RESET}").strip()
            config['webhook_url'] = input(f"{BLUE}Enter Webhook URL (Leave blank for none): {RESET}").strip()
            try:
                config['boosts'] = int(input(f"{BLUE}Enter Boost Amount: {RESET}"))
            except:
                config['boosts'] = 1
            save_config(config)
            print(f"{GREEN}[+] Settings Saved!{RESET}")
            time.sleep(1)

        elif choice == 't':
            config['headless'] = not config['headless']
            save_config(config)
            
        elif choice == 'e':
            break

if __name__ == "__main__":
    main()