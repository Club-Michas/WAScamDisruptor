from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import json
import os

# Load config
try:
    with open("config/config.json", "r", encoding="utf-8") as config_file:
        config = json.load(config_file)
except Exception as e:
    print(f" Failed to load config.json: {e}")
    exit()

# Load messages from the specified file
messages_file = config.get("messages_file")
if not os.path.exists(messages_file):
    print(f" Message file not found: {messages_file}")
    exit()

try:
    with open(messages_file, "r", encoding="utf-8") as mf:
        messages = json.load(mf)["messages"]
except Exception as e:
    print(f" Failed to load messages from {messages_file}: {e}")
    exit()

driver_path = config["driver_path"]
group_name = config["group_name"]

# Use Edge WebDriver
service = Service(driver_path)
driver = webdriver.Edge(service=service)

# Open WhatsApp Web
driver.get("https://web.whatsapp.com")

# Wait for QR code scan
input("Scan QR code and press Enter...")

# Wait for chats to load
time.sleep(10)

# Search for the group
search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
search_box.click()
search_box.send_keys(group_name)
search_box.send_keys(Keys.ENTER)

# Wait for group to open
time.sleep(2)

# Send messages in rotation
count = 0
while True:
    try:
        message = messages[count % len(messages)]  # Rotate through messages
        message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
        message_box.click()
        message_box.send_keys(message)
        message_box.send_keys(Keys.ENTER)
        count += 1
        print(f" Message {count} sent: {message}")
        time.sleep(5)
    except Exception as e:
        print(f" Error at message {count}: {e}")
        time.sleep(10)
