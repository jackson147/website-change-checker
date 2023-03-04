import time
import hashlib
from urllib.request import urlopen, Request
from datetime import datetime
from os.path import exists
import json
import sys
import traceback
import smtplib

CONFIGS_LOCATION = None
CONFIG_FILE_PATH = None

CHECK_URL = None
EMAIL_USERNAME = None
EMAIL_PASSWORD = None
RECIPIENT_ADDRESS = None
CHECK_INTERVAL_SECONDS = None

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

    if CHECK_URL is None or EMAIL_USERNAME is None or EMAIL_PASSWORD is None or EMAIL_USERNAME is None or RECIPIENT_ADDRESS is None:
        exit_with_failure(
            'missing required credentials in environment variables')
        
    # URL to monitor
    url = Request(CHECK_URL,
                headers={'User-Agent': 'Mozilla/5.0'})
    
    # Begin the loop to check if site has changed.
    response = urlopen(url).read()
    currentHash = hashlib.sha224(response).hexdigest()
    print("Inital hash:", currentHash)
    while True:
        try:
            # Wait for check interval
            time.sleep(CHECK_INTERVAL_SECONDS)

            print("Checking url", CHECK_URL)
            # Perform the get request
            response = urlopen(url).read()
            # Create a new hash
            newHash = hashlib.sha224(response).hexdigest()

            # Check if new hash is same as the previous hash
            if newHash == currentHash:
                print("No change, sleeping for ", CHECK_INTERVAL_SECONDS, "seconds")
                continue

            # If something changed, alert and set currentHash
            else:
                # notify
                print("Site changed, sending alert")
                send_changed_alert()

                currentHash = newHash

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
    global EMAIL_USERNAME
    global EMAIL_PASSWORD
    global RECIPIENT_ADDRESS
    global CHECK_INTERVAL_SECONDS

    with open(path, 'r') as file:
        data = json.load(file)

        CHECK_URL = data['CHECK_URL']
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
