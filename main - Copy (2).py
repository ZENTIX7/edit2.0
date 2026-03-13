import json
import os
import random
import threading
import time
import tkinter as tk
from tkinter import messagebox

import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

CONFIG_FILE = "config.json"
SITE_URL = "https://zefame.com/free-instagram-views"
INPUT_XPATH = "/html/body/div[4]/section[1]/div/div[1]/div[2]/div/form/div/input"
BTN_XPATH = "/html/body/div[4]/section[1]/div/div[1]/div[2]/div/form/div/button"


class BoostWorker:
    def __init__(self, config_getter, status_callback):
        self.config_getter = config_getter
        self.status_callback = status_callback
        self.stop_event = threading.Event()
        self.thread = None
        self.driver = None

    def start(self):
        if self.thread and self.thread.is_alive():
            return False
        self.stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        return True

    def stop(self):
        self.stop_event.set()
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                pass

    def _sleep_countdown(self, seconds, label):
        for remaining in range(seconds, 0, -1):
            if self.stop_event.is_set():
                return False
            mins, secs = divmod(remaining, 60)
            self.status_callback(f"{label}: {mins:02d}:{secs:02d}")
            time.sleep(1)
        return True

    def _send_discord_msg(self, webhook_url, cycle, total_boosts, start_time):
        if not webhook_url.strip():
            return
        elapsed_seconds = int(time.time() - start_time)
        payload = {
            "username": "7pce Booster Bot",
            "embeds": [{
                "title": "🚀 Cycle Completion Update",
                "color": 5763719,
                "fields": [
                    {"name": "Current Cycle", "value": f"{cycle} / {total_boosts}", "inline": True},
                    {"name": "Total Views Added", "value": f"{cycle * 300}", "inline": True},
                    {"name": "Total Runtime", "value": time.strftime('%H:%M:%S', time.gmtime(elapsed_seconds)), "inline": False},
                    {"name": "Cycles Remaining", "value": f"{total_boosts - cycle}", "inline": True},
                ],
                "footer": {"text": "Discord: 7pce"},
            }],
        }
        try:
            requests.post(webhook_url, json=payload, timeout=10)
        except Exception:
            pass

    def _run(self):
        config = self.config_getter()
        if not config["video_url"].strip():
            self.status_callback("Set an Instagram reel URL first.")
            return

        options = webdriver.ChromeOptions()
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
        if config.get("headless", False):
            options.add_argument("--headless=new")

        try:
            self.driver = webdriver.Chrome(options=options)
            self.status_callback("Browser opened. Starting cycles...")
        except Exception as exc:
            self.status_callback(f"Failed to open browser: {exc}")
            return

        start_time = time.time()
        try:
            for cycle in range(1, config["boosts"] + 1):
                if self.stop_event.is_set():
                    self.status_callback("Stopped by user.")
                    return

                self.status_callback(f"Cycle {cycle}/{config['boosts']}: loading site...")
                self.driver.get(SITE_URL)
                input_box = WebDriverWait(self.driver, 20).until(
                    EC.presence_of_element_located((By.XPATH, INPUT_XPATH))
                )
                input_box.clear()

                for char in config["video_url"]:
                    if self.stop_event.is_set():
                        self.status_callback("Stopped by user.")
                        return
                    input_box.send_keys(char)
                    time.sleep(random.uniform(0.03, 0.08))

                btn = self.driver.find_element(By.XPATH, BTN_XPATH)
                self.driver.execute_script("arguments[0].click();", btn)

                if not self._sleep_countdown(60, "Website processing"):
                    self.status_callback("Stopped by user.")
                    return

                self._send_discord_msg(config["webhook_url"], cycle, config["boosts"], start_time)

                if cycle < config["boosts"]:
                    if not self._sleep_countdown(360, "Cooldown"):
                        self.status_callback("Stopped by user.")
                        return

            self.status_callback("All boost cycles completed.")
        except Exception as exc:
            self.status_callback(f"Automation error: {exc}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
                self.driver = None


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("7pce Services")
        self.geometry("760x470")
        self.configure(bg="#0f1115")
        self.resizable(False, False)

        self.config_data = self.load_config()
        self.worker = BoostWorker(self.get_boost_config, self.set_status_threadsafe)

        self.current_frame = None
        self.status_var = tk.StringVar(value="Ready.")

        self._build_loading_screen()
        self.after(1300, self.show_choice_screen)

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"webhook_url": "", "video_url": "", "headless": False, "boosts": 1}

    def save_config(self):
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(self.config_data, f, indent=4)

    def get_boost_config(self):
        return {
            "video_url": self.url_var.get().strip(),
            "webhook_url": self.webhook_var.get().strip() if self.use_webhook_var.get() else "",
            "boosts": max(1, int(self.boost_var.get() or 1)),
            "headless": self.headless_var.get(),
        }

    def set_status_threadsafe(self, text):
        self.after(0, lambda: self.status_var.set(text))

    def _build_loading_screen(self):
        frame = tk.Frame(self, bg="#0f1115")
        tk.Label(frame, text="7pce", font=("Segoe UI", 32, "bold"), fg="#ffffff", bg="#0f1115").pack(pady=(150, 5))
        tk.Label(
            frame,
            text="Loading services...",
            font=("Segoe UI", 12),
            fg="#8f9bb3",
            bg="#0f1115",
        ).pack()
        self.switch_frame(frame, smooth=False)

    def show_choice_screen(self):
        frame = tk.Frame(self, bg="#0f1115")

        card = tk.Frame(frame, bg="#171a21", bd=0, highlightthickness=0)
        card.place(relx=0.5, rely=0.5, anchor="center", width=470, height=260)

        tk.Label(card, text="Choose Service", font=("Segoe UI", 24, "bold"), fg="#ffffff", bg="#171a21").pack(pady=(25, 5))
        tk.Label(card, text="Pick Tweaking GUI or Boost Service", font=("Segoe UI", 11), fg="#93a0b8", bg="#171a21").pack(pady=(0, 18))

        tk.Button(
            card,
            text="Tweaking GUI",
            font=("Segoe UI", 12, "bold"),
            bg="#4e7cff",
            fg="white",
            activebackground="#4368d8",
            relief="flat",
            command=self.show_tweaking_gui,
            cursor="hand2",
            width=18,
            pady=8,
        ).pack(pady=8)

        tk.Button(
            card,
            text="Boost Service",
            font=("Segoe UI", 12, "bold"),
            bg="#00a884",
            fg="white",
            activebackground="#009173",
            relief="flat",
            command=self.show_boost_gui,
            cursor="hand2",
            width=18,
            pady=8,
        ).pack(pady=8)

        self.switch_frame(frame, smooth=True)

    def show_tweaking_gui(self):
        frame = tk.Frame(self, bg="#0f1115")
        card = tk.Frame(frame, bg="#171a21")
        card.place(relx=0.5, rely=0.5, anchor="center", width=560, height=300)

        tk.Label(card, text="Tweaking GUI", font=("Segoe UI", 24, "bold"), fg="#ffffff", bg="#171a21").pack(pady=(30, 8))
        tk.Label(
            card,
            text="Tweaking service opens the normal tweaking logic.",
            font=("Segoe UI", 11),
            fg="#9da8bc",
            bg="#171a21",
        ).pack(pady=4)

        tk.Button(
            card,
            text="Open Tweaking Logic",
            font=("Segoe UI", 11, "bold"),
            bg="#4e7cff",
            fg="white",
            relief="flat",
            cursor="hand2",
            command=self._launch_tweak_logic,
            width=22,
            pady=8,
        ).pack(pady=18)

        tk.Button(card, text="Back", command=self.show_choice_screen, bg="#2c313d", fg="white", relief="flat", width=10).pack()

        self.switch_frame(frame, smooth=True)

    def _launch_tweak_logic(self):
        batch_file = "EXM Premium.bat"
        if os.path.exists(batch_file):
            os.startfile(batch_file) if os.name == "nt" else os.system(f"bash '{batch_file}'")
            messagebox.showinfo("Started", "Tweaking logic launched.")
        else:
            messagebox.showwarning("Missing", "Tweaking file not found in this repo.")

    def show_boost_gui(self):
        frame = tk.Frame(self, bg="#0f1115")

        card = tk.Frame(frame, bg="#171a21")
        card.place(relx=0.5, rely=0.5, anchor="center", width=620, height=380)

        tk.Label(card, text="Boost Service", font=("Segoe UI", 24, "bold"), fg="#ffffff", bg="#171a21").pack(pady=(18, 4))
        tk.Label(card, text="Discord: 7pce", font=("Segoe UI", 10), fg="#9da8bc", bg="#171a21").pack(pady=(0, 10))

        self.boost_var = tk.StringVar(value=str(self.config_data.get("boosts", 1)))
        self.url_var = tk.StringVar(value=self.config_data.get("video_url", ""))
        self.webhook_var = tk.StringVar(value=self.config_data.get("webhook_url", ""))
        self.use_webhook_var = tk.BooleanVar(value=bool(self.config_data.get("webhook_url", "")))
        self.headless_var = tk.BooleanVar(value=self.config_data.get("headless", False))

        self._entry_row(card, "Boost amount", self.boost_var)
        self._entry_row(card, "Instagram reel link", self.url_var)

        check = tk.Checkbutton(
            card,
            text="Add Webhook",
            variable=self.use_webhook_var,
            bg="#171a21",
            fg="#dbe3f1",
            selectcolor="#171a21",
            activebackground="#171a21",
            activeforeground="#dbe3f1",
            command=self._toggle_webhook_entry,
        )
        check.pack(anchor="w", padx=40, pady=(8, 2))

        self.webhook_entry = self._entry_row(card, "Webhook URL", self.webhook_var)
        if not self.use_webhook_var.get():
            self.webhook_entry.pack_forget()

        tk.Checkbutton(
            card,
            text="Run browser headless",
            variable=self.headless_var,
            bg="#171a21",
            fg="#dbe3f1",
            selectcolor="#171a21",
            activebackground="#171a21",
            activeforeground="#dbe3f1",
        ).pack(anchor="w", padx=40, pady=5)

        controls = tk.Frame(card, bg="#171a21")
        controls.pack(pady=8)

        tk.Button(controls, text="Start", bg="#00a884", fg="white", relief="flat", width=10, command=self.start_boost).pack(side="left", padx=6)
        tk.Button(controls, text="Stop", bg="#f04b4b", fg="white", relief="flat", width=10, command=self.stop_boost).pack(side="left", padx=6)
        tk.Button(controls, text="Back", bg="#2c313d", fg="white", relief="flat", width=10, command=self.show_choice_screen).pack(side="left", padx=6)

        tk.Label(card, textvariable=self.status_var, font=("Segoe UI", 10), fg="#8f9bb3", bg="#171a21", wraplength=540).pack(pady=(8, 6))

        self.switch_frame(frame, smooth=True)

    def _entry_row(self, parent, label, variable):
        wrapper = tk.Frame(parent, bg="#171a21")
        wrapper.pack(fill="x", padx=40, pady=6)

        tk.Label(wrapper, text=label, font=("Segoe UI", 10), fg="#cfd6e6", bg="#171a21").pack(anchor="w")
        tk.Entry(
            wrapper,
            textvariable=variable,
            font=("Segoe UI", 11),
            bg="#0f1115",
            fg="#ffffff",
            insertbackground="#ffffff",
            relief="flat",
            highlightthickness=1,
            highlightbackground="#2f3747",
            highlightcolor="#4e7cff",
        ).pack(fill="x", pady=(5, 0), ipady=7)
        return wrapper

    def _toggle_webhook_entry(self):
        if self.use_webhook_var.get():
            self.webhook_entry.pack(fill="x", padx=40, pady=6)
        else:
            self.webhook_entry.pack_forget()

    def start_boost(self):
        try:
            cfg = self.get_boost_config()
        except ValueError:
            messagebox.showerror("Invalid", "Boost amount must be a number.")
            return

        self.config_data.update(cfg)
        self.save_config()
        started = self.worker.start()
        if started:
            self.status_var.set("Boost service started.")
        else:
            self.status_var.set("Boost service is already running.")

    def stop_boost(self):
        self.worker.stop()
        self.status_var.set("Stop requested. Closing browser...")

    def switch_frame(self, new_frame, smooth=True):
        if not smooth or self.current_frame is None:
            if self.current_frame:
                self.current_frame.destroy()
            self.current_frame = new_frame
            self.current_frame.place(x=0, y=0, relwidth=1, relheight=1)
            return

        old_frame = self.current_frame
        width = self.winfo_width() or 760
        new_frame.place(x=width, y=0, relwidth=1, relheight=1)

        def animate(step=0):
            x = int(width - (width * (step / 18)))
            new_frame.place(x=x, y=0, relwidth=1, relheight=1)
            old_frame.place(x=x - width, y=0, relwidth=1, relheight=1)
            if step < 18:
                self.after(12, lambda: animate(step + 1))
            else:
                old_frame.destroy()
                new_frame.place(x=0, y=0, relwidth=1, relheight=1)
                self.current_frame = new_frame

        animate()


if __name__ == "__main__":
    App().mainloop()
