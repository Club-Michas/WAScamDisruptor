import tkinter as tk
from tkinter import ttk, messagebox
import threading
import json
import time
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys

# Load config
try:
    with open("config/config.json", "r", encoding="utf-8") as f:
        app_config = json.load(f)
except Exception as e:
    raise RuntimeError(f"Failed to load config.json: {e}")

# GUI Setup
root = tk.Tk()
root.geometry("500x400")

# Tkinter variables
qr_confirmed = tk.BooleanVar(value=False)
stop_event = threading.Event()
button_state = tk.StringVar(value="idle")
theme_mode = tk.StringVar(value=app_config.get("theme_mode", "light"))
gui_texts = {}

LANGUAGE_CODES = app_config["language_codes"]

def load_gui_language(lang_code):
    try:
        with open(f"config/lang/{lang_code}.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        messagebox.showerror("Language Error", f"Failed to load GUI language: {e}")
        return {}

def refresh_gui_labels():
    root.title(gui_texts.get("title", "WAScamDisruptor"))
    group_label.config(text=gui_texts.get("group_label", "Group Name"))
    lang_label.config(text=gui_texts.get("language_label", "Targeted Audience Language"))
    update_main_button()

def apply_theme():
    is_dark = theme_mode.get() == "dark"
    bg = "#2e2e2e" if is_dark else "SystemButtonFace"
    fg = "#ffffff" if is_dark else "black"
    root.configure(bg=bg)
    for widget in root.winfo_children():
        try:
            widget.configure(bg=bg, fg=fg)
        except:
            pass
    log_box.configure(bg=bg, fg=fg, insertbackground=fg)
    update_main_button()

def update_main_button():
    is_dark = theme_mode.get() == "dark"
    dark_bg = "#444444"
    dark_fg = "#ffffff"
    bg = dark_bg if is_dark else "green"
    main_button.config(bg=bg)
    state = button_state.get()

    if state == "idle":
        main_button.config(
            text=gui_texts.get("start_button", "Start Disruption"),
            bg=dark_bg if is_dark else "green",
            fg=dark_fg if is_dark else "white"
        )
    elif state == "qr":
        main_button.config(
            text=gui_texts.get("qr_button", "Confirm QR Code"),
            bg=dark_bg if is_dark else "orange",
            fg=dark_fg if is_dark else "black"
        )
    elif state == "running":
        main_button.config(
            text=gui_texts.get("stop_button", "Stop Disruption"),
            bg=dark_bg if is_dark else "red",
            fg=dark_fg if is_dark else "white"
        )

def handle_main_button():
    state = button_state.get()

    if state == "idle":
        group = group_entry.get().strip()
        language = language_var.get()
        if not group or not language:
            messagebox.showwarning("Missing Info", "Please enter group name and select language.")
            return

        button_state.set("qr")
        update_main_button()

        lang_code = LANGUAGE_CODES[language]
        config = {
            "driver_path": app_config["driver_path"],
            "group_name": group,
            "messages_file": f"{app_config['message_folder']}messages_{lang_code}.json"
        }

        threading.Thread(target=lambda: start_bot(config), daemon=True).start()

    elif state == "qr":
        qr_confirmed.set(True)
        button_state.set("running")
        update_main_button()

    elif state == "running":
        stop_event.set()
        qr_confirmed.set(False)
        button_state.set("idle")
        update_main_button()

def log_message(msg):
    log_box.insert(tk.END, msg + "\n")
    log_box.see(tk.END)

def start_bot(config):
    try:
        service = Service(config["driver_path"])
        driver = webdriver.Edge(service=service)
        driver.get("https://web.whatsapp.com")

        log_message("Browser launched. Waiting for QR confirmation...")

        while not qr_confirmed.get():
            time.sleep(1)

        log_message("QR confirmed. Starting disruption...")

        time.sleep(10)

        search_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="3"]')
        search_box.click()
        search_box.send_keys(config["group_name"])
        search_box.send_keys(Keys.ENTER)

        time.sleep(2)

        with open(config["messages_file"], "r", encoding="utf-8") as mf:
            messages = json.load(mf)["messages"]

        count = 0
        stop_event.clear()
        while not stop_event.is_set():
            try:
                message = messages[count % len(messages)]
                message_box = driver.find_element(By.XPATH, '//div[@contenteditable="true"][@data-tab="10"]')
                message_box.click()
                message_box.send_keys(message)
                message_box.send_keys(Keys.ENTER)
                count += 1
                log_message(f"Message {count} sent: {message}")
                time.sleep(5)
            except Exception as e:
                log_message(f"Error at message {count}: {e}")
                time.sleep(10)
    except Exception as e:
        messagebox.showerror("Bot Error", str(e))

def open_settings():
    settings = tk.Toplevel(root)
    settings.title("Settings")
    settings.geometry("350x200")

    is_dark = theme_mode.get() == "dark"
    bg = "#2e2e2e" if is_dark else "SystemButtonFace"
    fg = "#ffffff" if is_dark else "black"
    settings.configure(bg=bg)

    # GUI Language Section
    lang_label = tk.Label(settings, text=gui_texts.get("gui_language_label", "GUI Language"), bg=bg, fg=fg)
    lang_label.pack(pady=(10, 5))

    lang_select = ttk.Combobox(settings, values=list(LANGUAGE_CODES.values()), state="readonly")
    lang_select.set(app_config.get("default_gui_language", "en"))
    lang_select.pack()

    def apply_language():
        global gui_texts
        selected_lang = lang_select.get()
        gui_texts = load_gui_language(selected_lang)
        refresh_gui_labels()
        app_config["default_gui_language"] = selected_lang
        try:
            with open("config/config.json", "w", encoding="utf-8") as f:
                json.dump(app_config, f, indent=4)
        except Exception as e:
            print(f"Failed to save language setting: {e}")

    tk.Button(settings, text=gui_texts.get("apply_button", "Apply"), command=apply_language, bg=bg, fg=fg).pack(pady=5)

    # Load theme icons
    try:
        sun_img = tk.PhotoImage(file="config/assets/sun.png")
        moon_img = tk.PhotoImage(file="config/assets/moon.png")
    except Exception as e:
        sun_img = moon_img = None
        print(f"Failed to load theme icons: {e}")

    # Theme Toggle Frame
    theme_frame = tk.Frame(settings, bg=bg)
    theme_frame.pack(side="right", fill="y", padx=10, pady=10)

    def set_theme():
        apply_theme()
        app_config["theme_mode"] = theme_mode.get()
        try:
            with open("config/config.json", "w", encoding="utf-8") as f:
                json.dump(app_config, f, indent=4)
        except Exception as e:
            print(f"Failed to save theme setting: {e}")

    if sun_img and moon_img:
        sun_radio = tk.Radiobutton(theme_frame, image=sun_img, variable=theme_mode, value="light",
                                   command=set_theme, indicatoron=False, bg=bg, borderwidth=0, cursor="hand2")
        sun_radio.image = sun_img
        sun_radio.pack(side="top", pady=5)

        moon_radio = tk.Radiobutton(theme_frame, image=moon_img, variable=theme_mode, value="dark",
                                    command=set_theme, indicatoron=False, bg=bg, borderwidth=0, cursor="hand2")
        moon_radio.image = moon_img
        moon_radio.pack(side="top", pady=5)

    # About Text
    about_label = tk.Label(settings, text=gui_texts.get("about_text", "Created by Michael"), bg=bg, fg=fg)
    about_label.pack(pady=(20, 5))

    # GitHub Button
    try:
        github_icon = tk.PhotoImage(file="config/assets/github.png")
    except Exception as e:
        github_icon = None
        print(f"Failed to load GitHub icon: {e}")

    def open_github():
        import webbrowser
        webbrowser.open("https://github.com/Club-Michas/WAScamDisruptor")

    if github_icon:
        github_button = tk.Button(settings, image=github_icon, command=open_github, borderwidth=0, bg="white", cursor="hand2")
        github_button.image = github_icon
        github_button.pack(pady=5)
    else:
        tk.Button(settings, text="Visit GitHub", command=open_github).pack(pady=5)


# Load default GUI language
gui_texts = load_gui_language(app_config.get("default_gui_language", "en"))
root.title(gui_texts.get("title", "WAScamDisruptor"))

# GUI Elements
group_label = tk.Label(root, text=gui_texts.get("group_label", "Group Name"))
group_label.pack(pady=5)
group_entry = tk.Entry(root, width=40)
group_entry.pack()

lang_label = tk.Label(root, text=gui_texts.get("language_label", "GUI Language"))
lang_label.pack(pady=5)
language_var = tk.StringVar()
language_dropdown = ttk.Combobox(root, textvariable=language_var, values=list(LANGUAGE_CODES.keys()), state="readonly")
language_dropdown.pack()

main_button = tk.Button(root, text="", command=handle_main_button)
main_button.pack(pady=10)
update_main_button()

# Load gear icon using Tkinter's PhotoImage
try:
    gear_icon = tk.PhotoImage(file="config/assets/gear.png")
    settings_button = tk.Button(root, image=gear_icon, command=open_settings, borderwidth=0, highlightthickness=0, bg="white", cursor="hand2")
    settings_button.image = gear_icon
    settings_button.place(relx=0.97, y=5, anchor="ne")  # Slightly inset from top-right
except Exception as e:
    messagebox.showerror("Image Error", f"Failed to load gear icon: {e}")

log_box = tk.Text(root, height=10, width=60)
log_box.pack(pady=10)

apply_theme()


root.mainloop()
