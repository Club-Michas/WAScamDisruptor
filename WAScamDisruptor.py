"""
WAScamDisruptor — WhatsApp scam-awareness broadcaster.

Modern Tkinter UI using sv_ttk (light/dark theme), ttk widgets only,
thread-safe updates via a queue, and Selenium Manager for driver handling.
"""

import json
import os
import queue
import threading
import time
import tkinter as tk
import webbrowser
from dataclasses import dataclass
from datetime import datetime
from tkinter import ttk, messagebox
from typing import Optional

import sv_ttk
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.edge.options import Options as EdgeOptions


CONFIG_PATH = "config/config.json"


# --------------------------------------------------------------------------- #
# JSON helpers
# --------------------------------------------------------------------------- #
def load_json(path: str) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json_atomic(path: str, data: dict) -> None:
    tmp = f"{path}.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)
    os.replace(tmp, path)


# --------------------------------------------------------------------------- #
# Bot runner (unchanged logic, Selenium Manager for driver)
# --------------------------------------------------------------------------- #
@dataclass
class BotConfig:
    group_name: str
    messages_file: str


class BotRunner:
    SEARCH_BOX_XPATHS = [
        '//div[@contenteditable="true"][@data-tab="3"]',
        '//div[@contenteditable="true"][@role="textbox"][@aria-label]',
    ]
    MESSAGE_BOX_XPATHS = [
        '//div[@contenteditable="true"][@data-tab="10"]',
        '//footer//div[@contenteditable="true"][@role="textbox"]',
    ]

    def __init__(self, config: BotConfig, log, on_error):
        self.config = config
        self.log = log
        self.on_error = on_error
        self.stop_event = threading.Event()
        self.qr_confirmed = threading.Event()
        self.driver: Optional[webdriver.Edge] = None

    def start(self) -> None:
        threading.Thread(target=self._run, daemon=True).start()

    def confirm_qr(self) -> None:
        self.qr_confirmed.set()

    def stop(self) -> None:
        self.stop_event.set()
        self.qr_confirmed.set()

    def _find_first(self, xpaths, timeout=30):
        deadline = time.time() + timeout
        while time.time() < deadline:
            for xp in xpaths:
                els = self.driver.find_elements(By.XPATH, xp)
                if els:
                    return els[0]
            time.sleep(0.5)
        raise WebDriverException(f"No element matched any of: {xpaths}")

    def _run(self) -> None:
        try:
            options = EdgeOptions()
            # Selenium Manager auto-resolves msedgedriver for installed Edge.
            self.driver = webdriver.Edge(options=options)
            self.driver.get("https://web.whatsapp.com")
            self.log("Browser launched. Scan the QR code, then confirm in the app.")

            if not self.qr_confirmed.wait(timeout=300):
                self.on_error("Timed out waiting for QR confirmation.")
                return
            if self.stop_event.is_set():
                return

            self.log("QR confirmed. Waiting for WhatsApp Web to be ready...")
            search_box = self._find_first(self.SEARCH_BOX_XPATHS, timeout=60)
            search_box.click()
            search_box.send_keys(self.config.group_name)
            time.sleep(1.5)
            search_box.send_keys(Keys.ENTER)
            time.sleep(1.5)

            messages = load_json(self.config.messages_file).get("messages", [])
            if not messages:
                self.on_error("Messages file is empty.")
                return

            self.log(f"Group '{self.config.group_name}' opened. Sending messages...")

            count = 0
            while not self.stop_event.is_set():
                message = messages[count % len(messages)]
                try:
                    box = self._find_first(self.MESSAGE_BOX_XPATHS, timeout=15)
                    box.click()
                    box.send_keys(message)
                    box.send_keys(Keys.ENTER)
                    count += 1
                    preview = message[:60] + ("…" if len(message) > 60 else "")
                    self.log(f"[{count}] Sent: {preview}")
                    if self.stop_event.wait(timeout=5):
                        break
                except WebDriverException as e:
                    self.log(f"Send error at #{count + 1}: {e}")
                    if self.stop_event.wait(timeout=10):
                        break

            self.log(f"Stopped after {count} messages.")

        except Exception as e:  # noqa: BLE001
            self.on_error(str(e))
        finally:
            self._cleanup()

    def _cleanup(self) -> None:
        if self.driver is not None:
            try:
                self.driver.quit()
            except Exception:
                pass
            self.driver = None


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def make_card(parent) -> ttk.Frame:
    """A padded content frame; sv_ttk handles bg/fg automatically."""
    return ttk.Frame(parent, padding=(20, 16))


def section_title(parent, text: str) -> ttk.Label:
    lbl = ttk.Label(parent, text=text, style="Section.TLabel")
    return lbl


# --------------------------------------------------------------------------- #
# Main application
# --------------------------------------------------------------------------- #
class App:
    POLL_MS = 100

    def __init__(self, root: tk.Tk):
        self.root = root
        self.app_config = load_json(CONFIG_PATH)
        self._migrate_legacy_settings()

        self.language_codes: dict = self.app_config["language_codes"]
        self.gui_texts: dict = {}
        self.theme_mode = tk.StringVar(value=self.app_config.get("theme_mode", "dark"))
        self.language_var = tk.StringVar()
        self.button_state = tk.StringVar(value="idle")
        self.qr_confirmed = tk.BooleanVar(value=False)

        self.bot: Optional[BotRunner] = None
        self.ui_queue: "queue.Queue[callable]" = queue.Queue()

        # Apply theme BEFORE creating widgets so sv_ttk styles are present.
        sv_ttk.set_theme(self.theme_mode.get())
        self._define_styles()

        self._build_ui()
        self._load_gui_language(self.app_config.get("default_gui_language", "en"))

        self._pump_queue()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # -- migration --------------------------------------------------------- #
    def _migrate_legacy_settings(self) -> None:
        legacy = "settings.json"
        if not os.path.exists(legacy):
            return
        try:
            data = load_json(legacy)
        except Exception:
            return
        changed = False
        if "default_gui_language" not in self.app_config and "language" in data:
            self.app_config["default_gui_language"] = data["language"]
            changed = True
        if "theme_mode" not in self.app_config and "dark_mode" in data:
            self.app_config["theme_mode"] = "dark" if data["dark_mode"] else "light"
            changed = True
        if changed:
            save_json_atomic(CONFIG_PATH, self.app_config)
        try:
            os.remove(legacy)
        except OSError:
            pass

    # -- styles ------------------------------------------------------------ #
    def _define_styles(self) -> None:
        """Custom ttk styles for the app."""
        style = ttk.Style()

        # Base font
        default_font = ("Segoe UI", 10)
        self.root.option_add("*Font", default_font)

        # Section header inside cards
        style.configure("Section.TLabel", font=("Segoe UI Semibold", 10))
        # Title in the header bar
        style.configure("Title.TLabel", font=("Segoe UI Semibold", 14))
        # Subtitle in the header bar
        style.configure("Subtitle.TLabel", font=("Segoe UI", 9))
        # Big primary action button
        style.configure("Accent.TButton", font=("Segoe UI Semibold", 11), padding=10)

    # -- UI ---------------------------------------------------------------- #
    def _build_ui(self) -> None:
        self.root.title("WAScamDisruptor")
        self.root.minsize(560, 620)

        # ---------- Header bar ---------- #
        header = ttk.Frame(self.root, padding=(20, 14, 20, 10))
        header.pack(fill="x")

        title_block = ttk.Frame(header)
        title_block.pack(side="left", fill="x", expand=True)

        self.title_label = ttk.Label(title_block, text="WAScamDisruptor",
                                     style="Title.TLabel")
        self.title_label.pack(anchor="w")

        self.subtitle_label = ttk.Label(
            title_block,
            text="Automated scam-awareness messaging for WhatsApp groups",
            style="Subtitle.TLabel",
        )
        self.subtitle_label.pack(anchor="w", pady=(2, 0))

        # Settings (gear) button
        try:
            self.gear_icon = tk.PhotoImage(file="config/assets/gear.png")
            self.settings_button = ttk.Button(
                header, image=self.gear_icon, style="Icon.TButton",
                command=self._open_settings, width=4,
            )
            self.settings_button.image = self.gear_icon
        except Exception:
            self.settings_button = ttk.Button(
                header, text="⚙", width=3, command=self._open_settings,
            )
        self.settings_button.pack(side="right")

        ttk.Separator(self.root).pack(fill="x")

        # ---------- Configuration card ---------- #
        cfg = make_card(self.root)
        cfg.pack(fill="x", padx=16, pady=(16, 8))

        self.group_label = section_title(cfg, "Group Name")
        self.group_label.pack(anchor="w")

        self.group_entry = ttk.Entry(cfg)
        self.group_entry.pack(fill="x", pady=(6, 14))

        self.lang_label = section_title(cfg, "Targeted Audience Language")
        self.lang_label.pack(anchor="w")

        self.language_dropdown = ttk.Combobox(
            cfg,
            textvariable=self.language_var,
            values=list(self.language_codes.keys()),
            state="readonly",
        )
        self.language_dropdown.pack(fill="x", pady=(6, 0))
        if self.language_codes:
            self.language_var.set(next(iter(self.language_codes)))

        # ---------- Action button ---------- #
        action_wrap = ttk.Frame(self.root, padding=(16, 8))
        action_wrap.pack(fill="x")

        self.main_button = ttk.Button(
            action_wrap,
            text="Start Disruption",
            style="Accent.TButton",
            command=self._on_main_button,
        )
        self.main_button.pack(fill="x", ipady=6)

        # ---------- Status / log card ---------- #
        log_card = make_card(self.root)
        log_card.pack(fill="both", expand=True, padx=16, pady=(8, 16))

        self.log_label = section_title(log_card, "Activity Log")
        self.log_label.pack(anchor="w", pady=(0, 8))

        log_frame = ttk.Frame(log_card)
        log_frame.pack(fill="both", expand=True)

        self.log_box = tk.Text(
            log_frame,
            height=12,
            wrap="word",
            relief="flat",
            borderwidth=0,
            padx=10,
            pady=8,
            font=("Cascadia Mono", 9) if self._font_exists("Cascadia Mono")
                 else ("Consolas", 9),
        )
        self.log_box.pack(side="left", fill="both", expand=True)

        scroll = ttk.Scrollbar(log_frame, command=self.log_box.yview)
        scroll.pack(side="right", fill="y")
        self.log_box.config(yscrollcommand=scroll.set, state="disabled")

        # Log tags for colored messages
        self.log_box.tag_configure("info", foreground="#9aa0a6")
        self.log_box.tag_configure("sent", foreground="#4caf50")
        self.log_box.tag_configure("error", foreground="#e53935")

        self._restyle_log()

    @staticmethod
    def _font_exists(name: str) -> bool:
        try:
            import tkinter.font as tkfont
            return name in tkfont.families()
        except Exception:
            return False

    def _restyle_log(self) -> None:
        """Make the log Text widget match the current theme."""
        is_dark = sv_ttk.get_theme() == "dark"
        bg = "#1e1e1e" if is_dark else "#fafafa"
        fg = "#e8e8e8" if is_dark else "#1a1a1a"
        self.log_box.configure(
            bg=bg, fg=fg, insertbackground=fg,
            highlightthickness=0, selectbackground="#3a6ea5",
        )

    # -- i18n -------------------------------------------------------------- #
    def _load_gui_language(self, lang_code: str) -> None:
        try:
            self.gui_texts = load_json(f"config/lang/{lang_code}.json")
        except Exception as e:
            messagebox.showerror("Language Error", f"Failed to load GUI language: {e}")
            self.gui_texts = {}
        self._refresh_labels()

    def _refresh_labels(self) -> None:
        t = self.gui_texts
        self.root.title(t.get("title", "WAScamDisruptor"))
        self.group_label.config(text=t.get("group_label", "Group Name"))
        self.lang_label.config(text=t.get("language_label", "Targeted Audience Language"))
        self._update_main_button()

    # -- button state machine --------------------------------------------- #
    def _update_main_button(self) -> None:
        t = self.gui_texts
        state = self.button_state.get()
        if state == "idle":
            self.main_button.config(
                text=t.get("start_button", "Start Disruption"),
                state="normal",
            )
        elif state == "qr":
            self.main_button.config(
                text=t.get("qr_button", "Confirm QR Code"),
                state="normal",
            )
        elif state == "running":
            self.main_button.config(
                text=t.get("stop_button", "Stop Disruption"),
                state="normal",
            )

    def _on_main_button(self) -> None:
        state = self.button_state.get()

        if state == "idle":
            group = self.group_entry.get().strip()
            language = self.language_var.get()
            if not group or not language:
                messagebox.showwarning(
                    "Missing Info",
                    "Please enter a group name and select a language.",
                )
                return

            lang_code = self.language_codes[language]
            bot_cfg = BotConfig(
                group_name=group,
                messages_file=f"{self.app_config['message_folder']}messages_{lang_code}.json",
            )
            if not os.path.exists(bot_cfg.messages_file):
                messagebox.showerror(
                    "Missing Messages",
                    f"Messages file not found:\n{bot_cfg.messages_file}",
                )
                return

            self.bot = BotRunner(bot_cfg, self._log_async, self._error_async)
            self.bot.start()
            self.button_state.set("qr")
            self._update_main_button()

        elif state == "qr":
            if self.bot is not None:
                self.bot.confirm_qr()
            self.button_state.set("running")
            self._update_main_button()

        elif state == "running":
            if self.bot is not None:
                self.bot.stop()
                self.bot = None
            self.button_state.set("idle")
            self._update_main_button()

    # -- thread-safe UI bridge -------------------------------------------- #
    def _pump_queue(self) -> None:
        try:
            while True:
                fn = self.ui_queue.get_nowait()
                fn()
        except queue.Empty:
            pass
        self.root.after(self.POLL_MS, self._pump_queue)

    def _log_async(self, msg: str) -> None:
        self.ui_queue.put(lambda m=msg: self._log(m))

    def _error_async(self, msg: str) -> None:
        self.ui_queue.put(lambda m=msg: self._on_bot_error(m))

    def _log(self, msg: str, tag: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_box.configure(state="normal")
        self.log_box.insert(tk.END, f"[{ts}] ", ("info",))
        self.log_box.insert(tk.END, f"{msg}\n", (tag,))
        self.log_box.see(tk.END)
        self.log_box.configure(state="disabled")

    def _on_bot_error(self, msg: str) -> None:
        self._log(f"ERROR: {msg}", tag="error")
        messagebox.showerror("Bot Error", msg)
        self.bot = None
        self.button_state.set("idle")
        self._update_main_button()

    # -- settings ---------------------------------------------------------- #
    def _open_settings(self) -> None:
        SettingsWindow(self.root, self)

    # -- shutdown ---------------------------------------------------------- #
    def _on_close(self) -> None:
        if self.bot is not None:
            self.bot.stop()
        self.root.after(150, self.root.destroy)


# --------------------------------------------------------------------------- #
# Settings window
# --------------------------------------------------------------------------- #
class SettingsWindow(tk.Toplevel):
    def __init__(self, parent: tk.Misc, app: App):
        super().__init__(parent)
        self.app = app
        self.title("Settings")
        self.geometry("420x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        t = app.gui_texts

        # ---------- Appearance section ---------- #
        appearance = make_card(self)
        appearance.pack(fill="x", padx=12, pady=(12, 6))

        ttk.Label(appearance, text="Appearance", style="Section.TLabel").pack(anchor="w")

        theme_row = ttk.Frame(appearance)
        theme_row.pack(fill="x", pady=(8, 0))

        ttk.Label(theme_row, text="Theme").pack(side="left")

        toggle = ttk.Checkbutton(
            theme_row,
            text="Dark Mode",
            style="Switch.TCheckbutton",
            command=self._toggle_theme,
        )
        # sv_ttk exposes Switch.TCheckbutton for iOS-like toggles
        if sv_ttk.get_theme() == "dark":
            toggle.state(["selected"])
        toggle.pack(side="right")
        self.theme_toggle = toggle

        # ---------- Language section ---------- #
        lang = make_card(self)
        lang.pack(fill="x", padx=12, pady=6)

        ttk.Label(lang, text=t.get("gui_language_label", "GUI Language"),
                  style="Section.TLabel").pack(anchor="w")

        self.lang_select = ttk.Combobox(
            lang,
            values=list(app.language_codes.values()),
            state="readonly",
        )
        self.lang_select.set(app.app_config.get("default_gui_language", "en"))
        self.lang_select.pack(fill="x", pady=(8, 8))

        ttk.Button(
            lang,
            text=t.get("apply_button", "Apply"),
            command=self._apply_language,
        ).pack(anchor="e")

        # ---------- Footer ---------- #
        footer = ttk.Frame(self, padding=(16, 8, 16, 14))
        footer.pack(fill="x", side="bottom")

        ttk.Label(
            footer,
            text=t.get("about_text", "Developed by Michael Rozwadowski"),
            style="Subtitle.TLabel",
        ).pack(side="left")

        try:
            self.github_icon = tk.PhotoImage(file="config/assets/github.png")
            gh = ttk.Button(
                footer, image=self.github_icon,
                style="Icon.TButton",
                command=self._open_github,
            )
            gh.image = self.github_icon
        except Exception:
            gh = ttk.Button(footer, text="GitHub", command=self._open_github)
        gh.pack(side="right")

    # -- callbacks -------------------------------------------------------- #
    def _toggle_theme(self) -> None:
        new_theme = "light" if sv_ttk.get_theme() == "dark" else "dark"
        sv_ttk.set_theme(new_theme)
        self.app.theme_mode.set(new_theme)
        self.app._restyle_log()
        self.app.app_config["theme_mode"] = new_theme
        try:
            save_json_atomic(CONFIG_PATH, self.app.app_config)
        except Exception as e:
            print(f"Failed to save theme: {e}")

    def _apply_language(self) -> None:
        selected = self.lang_select.get()
        self.app._load_gui_language(selected)
        self.app.app_config["default_gui_language"] = selected
        try:
            save_json_atomic(CONFIG_PATH, self.app.app_config)
        except Exception as e:
            print(f"Failed to save language: {e}")

    @staticmethod
    def _open_github() -> None:
        webbrowser.open("https://github.com/Club-Michas/WAScamDisruptor")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
def main() -> None:
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
