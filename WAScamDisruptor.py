from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

# Use Edge WebDriver
service = Service("C:/Path/to/msedgedriver.exe")
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
search_box.send_keys("TYPE IN THE SCAM GROUP HERE")
search_box.send_keys(Keys.ENTER)

# Wait for group to open
time.sleep(5)

# List of rotating messages
messages = [
    " SCAM ALERT: This is a fake promo designed to steal your data. DO NOT send screenshots or codes.",
    " FAKE JOB OFFER: No 10€ reward, no remote job, just fraud. Report and leave.",
    " They use fake Instagram profiles and Telegram bots to steal your info. Stay safe.",
    " Don’t follow, don’t send anything. It’s a scam network.",
    " Watch Kitboga, Jim Browning, and Scammer Payback to learn how these scams work.",
    " This is a Pig Butchering scam, don't fall for it",
    " FAKE FAKE FAKE, they will take your money and run",
    " Don't believe those scammers, they will steal your Money",
    " Those Randi Ka Larka are Scammers",
    " They are low life Benchodes that want to steal your Money, stay safe",
    " Don't ever Trust those Fools, they are Scamming you, no reward",
    " Say no to Scams, do not send them a single Penny, you will get Scammed",
    " WARNING: This group promotes fraudulent schemes. Leave immediately.",
    " Don’t be fooled, this is a scam operation targeting innocent people.",
    " They promise rewards, but all they want is your personal data and money.",
    " No legit company asks for screenshots or verification codes. It’s a trap.",
    " Scammers use fake profiles to build trust, don’t fall for it.",
    " This is a classic social engineering scam. Stay alert.",
    " Protect your identity. Don’t share anything with these fraudsters.",
    " Think before you click. Scammers prey on urgency and greed.",
    " Report this group to WhatsApp. Help stop the spread of fraud.",
    " No job, no prize, no giveaway, just lies and theft.",
    " They’re trying to manipulate you. Don’t engage.",
    " These scammers are exploiting people for profit. Don’t let them win.",
    " If it sounds too good to be true, it’s probably a scam.",
    " Don’t risk your money or data. Leave this group now.",
    " Educate others, share scam awareness and expose these frauds."

]

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


