import time
import hashlib
from urllib.request import urlopen, Request
from datetime import datetime
from os.path import exists
import json
import sys
import traceback
import smtplib

from selenium.webdriver.chrome.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup

# Global vars
USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 11_1_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.114 Safari/537.36'
CONFIGS_LOCATION = None
CONFIG_FILE_PATH = None
CHECK_URL = None
SEARCH_TEXT = None
PAGE_LOADING_TIME = 0
EMAIL_USERNAME = None
EMAIL_PASSWORD = None
RECIPIENT_ADDRESS = None
CHECK_INTERVAL_SECONDS = None

# Selenium webdriver setup
options = Options()
options.add_argument(
    f'user-agent={USER_AGENT}')
options.add_argument("no-sandbox")
options.add_argument("disable-dev-shm-usage")
options.add_argument("--headless")

driver = webdriver.Chrome(
    options=options)

def main():
    global CONFIGS_LOCATION
    global CONFIG_FILE_PATH

    possible_config_locations = ["./configs/", "/configs/", "/run/secrets/"]
    possible_config_names = ["config.json", "website-change-checker-config.json"]
    for config_location in possible_config_locations:
        for config_name in possible_config_names:
            config_path = config_location + config_name
            if exists(config_path):
                CONFIGS_LOCATION = config_location
                CONFIG_FILE_PATH = config_path
                break
    
    if CONFIG_FILE_PATH is None:
        exit_with_failure(
            'missing config.json file, could not find in locations: ' + ', '.join(str(x) for x in possible_config_locations)
        )

    load_config(CONFIG_FILE_PATH)

    if CHECK_URL is None or SEARCH_TEXT is None or EMAIL_USERNAME is None or EMAIL_PASSWORD is None or EMAIL_USERNAME is None or RECIPIENT_ADDRESS is None:
        exit_with_failure(
            'missing required credentials in environment variables')
    
    # Begin the loop to check if site has changed.
    while True:
        try:
            print_with_timestamp("Checking url {} for text: '{}'".format(CHECK_URL, SEARCH_TEXT))
            driver.get(CHECK_URL)
            if(PAGE_LOADING_TIME > 0):
                print_with_timestamp("Sleeping for {}s while page loads...".format(PAGE_LOADING_TIME))
                time.sleep(PAGE_LOADING_TIME)
            html = driver.page_source
            soup = BeautifulSoup(html, features="html.parser")
            value = soup.find(string=SEARCH_TEXT)
            
            if value is None or value == "":
                # notify
                print_with_timestamp("Search text no longer exists on site, sending alert!".format(SEARCH_TEXT))
                send_changed_alert()
                exit(0)
                
            # Wait for check interval                
            print_with_timestamp("No change, sleeping for {} seconds".format(CHECK_INTERVAL_SECONDS))
            time.sleep(CHECK_INTERVAL_SECONDS)

        # To handle exceptions
        except Exception as e:
            print(e)
            exit_with_failure('Failed in check loop')


def print_with_timestamp(text):
    print(f'{datetime.now().strftime("%d/%m/%Y %H:%M:%S")} - {text}')


def exit_with_failure(message):
    traceback.print_exc()
    print_with_timestamp(message)
    sys.exit(1)

def load_config(path):
    global CHECK_URL
    global SEARCH_TEXT
    global PAGE_LOADING_TIME
    global EMAIL_USERNAME
    global EMAIL_PASSWORD
    global RECIPIENT_ADDRESS
    global CHECK_INTERVAL_SECONDS

    with open(path, 'r') as file:
        data = json.load(file)

        CHECK_URL = data['CHECK_URL']
        SEARCH_TEXT = data['SEARCH_TEXT']
        PAGE_LOADING_TIME = int(data['PAGE_LOADING_TIME'])
        EMAIL_USERNAME = data['EMAIL_USERNAME']
        EMAIL_PASSWORD = data['EMAIL_PASSWORD']
        CHECK_INTERVAL_SECONDS = int(data['CHECK_INTERVAL_SECONDS'])
        RECIPIENT_ADDRESS = data['RECIPIENT_ADDRESS']

def send_changed_alert():
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(EMAIL_USERNAME, EMAIL_PASSWORD)
    message = f'\n\n{CHECK_URL} has changed'

    if message != '':
        try:
            server.sendmail(EMAIL_USERNAME, [RECIPIENT_ADDRESS], message)
            print(message)
        except:
            print('unable to send:\n' + message)
            raise

    server.quit()

if __name__ == '__main__':
    main()
