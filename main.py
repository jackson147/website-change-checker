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
    possible_config_locations = ["./configs/", "/configs/", "/run/secrets/"]
    possible_config_names = ["config.json", "website-change-checker-config.json"]

    true_config_file_path = None
    for config_location in possible_config_locations:
        for config_name in possible_config_names:
            config_path = config_location + config_name
            if exists(config_path):
                true_config_file_path = config_path
                break
    
    if true_config_file_path is None:
        exit_with_failure(
            'missing config.json file, could not find in locations: ' + ', '.join(str(x) for x in possible_config_locations)
        )

    config = load_config(true_config_file_path)

    if config['CHECK_URL'] is None or config['SEARCH_TEXT'] is None or config['EMAIL_USERNAME'] is None or config['EMAIL_PASSWORD'] is None or config['EMAIL_USERNAME'] is None or config['RECIPIENT_ADDRESSES'] is None:
        exit_with_failure(
            'missing required credentials in environment variables')
    
    # Begin the loop to check if site has changed.
    while True:
        try:
            print_with_timestamp("Checking url {} for text: '{}'".format(config['CHECK_URL'], config['SEARCH_TEXT']))
            driver.get(config['CHECK_URL'])
            if(config['PAGE_LOADING_TIME'] > 0):
                print_with_timestamp("Sleeping for {}s while page loads...".format(config['PAGE_LOADING_TIME']))
                time.sleep(config['PAGE_LOADING_TIME'])
            html = driver.page_source
            soup = BeautifulSoup(html, features="html.parser")
            value = soup.find(string=config['SEARCH_TEXT'])
            
            if value is None or value == "":
                # notify
                print_with_timestamp("Search text no longer exists on site, sending alert!".format(config['SEARCH_TEXT']))
                send_changed_alert(config)
                exit(0)
                
            # Wait for check interval                
            print_with_timestamp("No change, sleeping for {} seconds".format(config['CHECK_INTERVAL_SECONDS']))
            time.sleep(config['CHECK_INTERVAL_SECONDS'])

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
    with open(path, 'r') as file:
        config = json.load(file)
        return config

def send_changed_alert(config):
    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    server.login(config['EMAIL_USERNAME'], config['EMAIL_PASSWORD'])
    check_url = config['CHECK_URL']
    message = f'\n\n{check_url} has changed'

    if message != '':
        for RECIPIENT_ADDRESS in config['RECIPIENT_ADDRESSES']:
            try:
                server.sendmail(config['EMAIL_USERNAME'], [RECIPIENT_ADDRESS], message)
                print(message)
            except:
                print('unable to send:\n' + message)
                raise

    server.quit()

if __name__ == '__main__':
    main()
