# WAScamDisruptor 🚫📱

**WAScamDisruptor** is a lightweight, open-source Python script designed to ethically disrupt scam operations on WhatsApp by flooding scam groups with automated messages. Inspired by the scambaiting community, this tool helps raise awareness and waste scammers’ time, so they have less of it to target real victims.

> ⚠️ For educational and awareness purposes only. Use responsibly.

---

## ✨ Features
- Automated message flooding via WhatsApp Web
- Customizable message sets
- Randomized delays to mimic human behavior
- Simple setup using Selenium and Edge WebDriver
- Config file for clean separation of settings

---
## 🚧 Planned Features
- [ ] GUI interface for easy control
- [ ] Language selection (German, English, etc.)
- [ ] Modular message packs (warnings, satire, etc.)
- [ ] Persona simulation (fake scammer/victim dialogues)
- [ ] **Multisession support for parallel personas**
- [ ] Message flood engine with interval control
- [ ] Stats tracker (messages sent, groups joined)
---

## 🚀 Getting Started

### 1. Download the Script
Grab the `WAScamDisruptor.py`, `config.json`, and one of the message files like `messages_en.json`.

Scam warning messages are available in multiple languages. Use the one that fits your target audience:

- `messages_en.json` – English (default)
- `messages_de.json` – German
- `messages_pl.json` – Polish
- `messages_nl.json` – Dutch

### 2. Install Dependencies
Make sure Python is installed, then run:

```bash
pip install selenium
```

### 3. Download Edge WebDriver
Visit the Microsoft Edge WebDriver download page:

```bash
https://developer.microsoft.com/en-us/microsoft-edge/tools/webdriver/?form=MA13LH#downloads
```

Download the x64 version that matches your Edge browser

Place msedgedriver.exe in the same folder as WAScamDisruptor.py

### 4. Configure the Config file:
Edit the `config.json` file with your own values:
   - `driver_path`: Path to your `msedgedriver.exe`
   - `group_name`: Name of your WhatsApp group
   - `messages_file`: Choose your language file (e.g. `messages_en.json`, `messages_de.json`)

### 5. Run the Script
Open Command Prompt as Administrator

Navigate to the script folder:

bash
cd path\to\WAScamDisruptor
Run the script:

bash
python WAScamDisruptor.py
Scan the QR code to log into WhatsApp Web

Once logged in, return to the Command Prompt and press Enter

Let the disruption begin.

### 🤝 Contributing
Pull requests welcome! You can contribute by:

Adding new message packs

Improving platform compatibility

Suggesting new features or enhancements

### 📄 License
MIT License – free to use, modify, and share.

### 🙌 Credits
Inspired by the scambaiting efforts of:

Kitboga: https://www.youtube.com/@KitbogaShow

Jim Browning: https://www.youtube.com/@JimBrowning

Pleasant Green: https://www.youtube.com/@PleasantGreen

Help spread awareness. Disrupt scams. Protect others.
