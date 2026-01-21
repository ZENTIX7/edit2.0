import ctypes
import datetime as dt
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, ttk

APP_TITLE = "7pce Tweaks Utility"
BACKUP_ROOT = Path("backups")


def is_windows() -> bool:
    return os.name == "nt"


def is_admin() -> bool:
    if not is_windows():
        return False
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except AttributeError:
        return False


def run_command(command: list[str], description: str) -> None:
    print(f"[RUN] {description}")
    print(f"      {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, shell=False)
    if result.returncode != 0:
        stderr = result.stderr.strip() or "(no error output)"
        raise RuntimeError(f"{description} failed: {stderr}")


def create_backup_dir() -> Path:
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUP_ROOT / timestamp
    backup_dir.mkdir(parents=True, exist_ok=True)
    return backup_dir


def backup_registry_key(parent_key: str, backup_dir: Path, backed_up: set[str]) -> None:
    if parent_key in backed_up:
        return
    safe_name = parent_key.replace("\\", "_").replace("/", "_")
    backup_file = backup_dir / f"{safe_name}.reg"
    run_command(
        ["reg", "export", parent_key, str(backup_file), "/y"],
        f"Backup registry key {parent_key}",
    )
    backed_up.add(parent_key)


def restore_backup_file(path: Path) -> None:
    run_command(["reg", "import", str(path)], f"Restore registry backup {path}")


def restart_explorer() -> None:
    run_command(["taskkill", "/f", "/im", "explorer.exe"], "Stop Explorer")
    run_command(["cmd", "/c", "start", "explorer.exe"], "Start Explorer")


TWEAKS: list[dict] = [
    {
        "label": "Disable Mouse Acceleration",
        "description": "Turn off Enhance Pointer Precision.",
        "parent_keys": ["HKCU\\Control Panel\\Mouse"],
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\Control Panel\\Mouse",
                "/v",
                "MouseSpeed",
                "/t",
                "REG_SZ",
                "/d",
                "0",
                "/f",
            ],
            [
                "reg",
                "add",
                "HKCU\\Control Panel\\Mouse",
                "/v",
                "MouseThreshold1",
                "/t",
                "REG_SZ",
                "/d",
                "0",
                "/f",
            ],
            [
                "reg",
                "add",
                "HKCU\\Control Panel\\Mouse",
                "/v",
                "MouseThreshold2",
                "/t",
                "REG_SZ",
                "/d",
                "0",
                "/f",
            ],
        ],
        "explorer_notice": False,
    },
    {
        "label": "Reduce Menu Show Delay",
        "description": "Make menus appear instantly.",
        "parent_keys": ["HKCU\\Control Panel\\Desktop"],
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\Control Panel\\Desktop",
                "/v",
                "MenuShowDelay",
                "/t",
                "REG_SZ",
                "/d",
                "0",
                "/f",
            ]
        ],
        "explorer_notice": True,
    },
    {
        "label": "Disable Taskbar Animations",
        "description": "Turn off taskbar animation effects.",
        "parent_keys": [
            "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced"
        ],
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced",
                "/v",
                "TaskbarAnimations",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ]
        ],
        "explorer_notice": True,
    },
    {
        "label": "Disable Transparency Effects",
        "description": "Disable acrylic transparency in Windows.",
        "parent_keys": [
            "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
        ],
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize",
                "/v",
                "EnableTransparency",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ]
        ],
        "explorer_notice": True,
    },
    {
        "label": "Disable Aero Peek",
        "description": "Disable Windows Aero Peek behavior.",
        "parent_keys": ["HKCU\\Software\\Microsoft\\Windows\\DWM"],
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\Windows\\DWM",
                "/v",
                "EnableAeroPeek",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ]
        ],
        "explorer_notice": True,
    },
    {
        "label": "Disable Xbox Game Bar / GameDVR",
        "description": "Disable Game Bar overlays and background capture.",
        "parent_keys": [
            "HKCU\\Software\\Microsoft\\GameBar",
            "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
        ],
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\GameBar",
                "/v",
                "AllowAutoGameMode",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ],
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\GameBar",
                "/v",
                "ShowStartupPanel",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ],
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\GameBar",
                "/v",
                "UseNexusForGameBarEnabled",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ],
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\GameBar",
                "/v",
                "GameDVR_Enabled",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ],
            [
                "reg",
                "add",
                "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
                "/v",
                "AppCaptureEnabled",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ],
        ],
        "explorer_notice": False,
    },
    {
        "label": "Network Maintenance",
        "description": "Flush DNS, release/renew IP, reset Winsock (reboot required).",
        "parent_keys": [],
        "commands": [
            ["ipconfig", "/flushdns"],
            ["ipconfig", "/release"],
            ["ipconfig", "/renew"],
            ["netsh", "winsock", "reset"],
        ],
        "explorer_notice": False,
        "post_message": "Winsock reset completed. A reboot is required.",
    },
]


class TweaksApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("980x680")
        self.minsize(940, 620)
        self.configure(bg="#0f1115")
        self.accent = "#7d5cff"
        self.theme_mode = "dark"
        self._header_phase = 0
        self._pulse_direction = 1
        self._backup_dir = create_backup_dir()
        self._backed_up_keys: set[str] = set()
        self._build_style()
        self._build_layout()
        self._animate_header()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#0f1115")
        style.configure("Card.TFrame", background="#171a21")
        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 20, "bold"),
            foreground="white",
            background="#0f1115",
        )
        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 11),
            foreground="#aab3c6",
            background="#0f1115",
        )
        style.configure(
            "CardTitle.TLabel",
            font=("Segoe UI", 12, "bold"),
            foreground="white",
            background="#171a21",
        )
        style.configure(
            "CardBody.TLabel",
            font=("Segoe UI", 10),
            foreground="#c6cede",
            background="#171a21",
            wraplength=360,
        )
        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 10, "bold"),
            foreground="white",
            background=self.accent,
            borderwidth=0,
            padding=(16, 8),
        )
        style.map("Accent.TButton", background=[("active", "#6a49ff")])
        style.configure("TLabel", background="#0f1115")
        style.configure("TButton", font=("Segoe UI", 10, "bold"))

    def _build_layout(self) -> None:
        header = ttk.Frame(self)
        header.pack(fill="x", padx=24, pady=(20, 10))

        self.header_title = ttk.Label(
            header, text=APP_TITLE, style="Title.TLabel"
        )
        self.header_title.pack(anchor="w")
        ttk.Label(
            header,
            text="Modern tweak launcher with customization, animations, and one-click actions.",
            style="Subtitle.TLabel",
        ).pack(anchor="w", pady=(4, 0))

        content = ttk.Frame(self)
        content.pack(fill="both", expand=True, padx=24, pady=10)

        tweaks_frame = ttk.Frame(content)
        tweaks_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))

        customize_frame = ttk.Frame(content)
        customize_frame.grid(row=0, column=1, sticky="nsew")

        content.columnconfigure(0, weight=3)
        content.columnconfigure(1, weight=2)
        content.rowconfigure(0, weight=1)

        self._build_tweak_cards(tweaks_frame)
        self._build_customizer(customize_frame)

    def _build_tweak_cards(self, parent: ttk.Frame) -> None:
        canvas = tk.Canvas(parent, bg="#0f1115", highlightthickness=0)
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        scrollable = ttk.Frame(canvas)

        scrollable.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        canvas.create_window((0, 0), window=scrollable, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for tweak in TWEAKS:
            card = ttk.Frame(scrollable, style="Card.TFrame")
            card.pack(fill="x", pady=10, padx=2)

            title = ttk.Label(card, text=tweak["label"], style="CardTitle.TLabel")
            title.pack(anchor="w", padx=16, pady=(12, 2))

            body = ttk.Label(
                card, text=tweak["description"], style="CardBody.TLabel"
            )
            body.pack(anchor="w", padx=16, pady=(0, 10))

            action = ttk.Button(
                card,
                text="Apply",
                style="Accent.TButton",
                command=lambda t=tweak: self._apply_tweak(t),
            )
            action.pack(anchor="e", padx=16, pady=(0, 12))

    def _build_customizer(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame")
        card.pack(fill="both", expand=True)

        ttk.Label(card, text="Customize", style="CardTitle.TLabel").pack(
            anchor="w", padx=16, pady=(16, 6)
        )
        ttk.Label(
            card,
            text="Pick a theme and accent color. Changes animate across the UI.",
            style="CardBody.TLabel",
        ).pack(anchor="w", padx=16, pady=(0, 12))

        theme_row = ttk.Frame(card, style="Card.TFrame")
        theme_row.pack(fill="x", padx=16, pady=(0, 8))

        ttk.Label(theme_row, text="Theme", style="CardBody.TLabel").pack(
            side="left"
        )
        self.theme_var = tk.StringVar(value=self.theme_mode)
        theme_toggle = ttk.Checkbutton(
            theme_row,
            text="Dark Mode",
            variable=self.theme_var,
            onvalue="dark",
            offvalue="light",
            command=self._toggle_theme,
        )
        theme_toggle.pack(side="right")

        accent_row = ttk.Frame(card, style="Card.TFrame")
        accent_row.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Label(accent_row, text="Accent", style="CardBody.TLabel").pack(
            side="left"
        )
        ttk.Button(
            accent_row, text="Pick Color", command=self._pick_accent
        ).pack(side="right")

        restore_row = ttk.Frame(card, style="Card.TFrame")
        restore_row.pack(fill="x", padx=16, pady=(0, 12))
        ttk.Label(restore_row, text="Restore", style="CardBody.TLabel").pack(
            side="left"
        )
        ttk.Button(
            restore_row, text="Import Backup", command=self._restore_from_file
        ).pack(side="right")

        divider = ttk.Separator(card)
        divider.pack(fill="x", padx=16, pady=(4, 12))

        ttk.Label(card, text="Status", style="CardTitle.TLabel").pack(
            anchor="w", padx=16, pady=(0, 6)
        )
        self.status_label = ttk.Label(
            card,
            text="Ready to apply tweaks.",
            style="CardBody.TLabel",
        )
        self.status_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.progress = ttk.Progressbar(card, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=(0, 16))

        canvas = tk.Canvas(card, height=140, bg="#171a21", highlightthickness=0)
        canvas.pack(fill="x", padx=16, pady=(0, 16))
        self._animation_canvas = canvas
        self._animation_dot = canvas.create_oval(
            10, 40, 50, 80, fill=self.accent, width=0
        )
        self._animation_direction = 1
        self._animate_dot()

    def _apply_tweak(self, tweak: dict) -> None:
        self._set_status(f"Applying: {tweak['label']}...")
        self.progress.start(10)
        self.update_idletasks()

        try:
            for parent_key in tweak.get("parent_keys", []):
                backup_registry_key(parent_key, self._backup_dir, self._backed_up_keys)

            for command in tweak.get("commands", []):
                run_command(command, tweak["label"])

            self.progress.stop()
            self._set_status(f"{tweak['label']} applied successfully.")

            post_message = tweak.get("post_message")
            if post_message:
                messagebox.showinfo(APP_TITLE, post_message)

            if tweak.get("explorer_notice"):
                self._handle_explorer_notice()
            else:
                messagebox.showinfo(APP_TITLE, "Tweak applied successfully.")
        except RuntimeError as exc:
            self.progress.stop()
            self._set_status("Tweak failed. Check permissions.")
            messagebox.showerror(APP_TITLE, str(exc))

    def _handle_explorer_notice(self) -> None:
        message = (
            "Sign out/in or restart Explorer may be required.\n"
            "Restart Explorer now?"
        )
        if messagebox.askyesno(APP_TITLE, message):
            try:
                restart_explorer()
            except RuntimeError as exc:
                messagebox.showerror(APP_TITLE, str(exc))

    def _restore_from_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Select registry backup",
            initialdir=str(BACKUP_ROOT),
            filetypes=[("Registry Files", "*.reg"), ("All Files", "*")],
        )
        if not file_path:
            return
        try:
            restore_backup_file(Path(file_path))
            messagebox.showinfo(APP_TITLE, "Backup restored successfully.")
        except RuntimeError as exc:
            messagebox.showerror(APP_TITLE, str(exc))

    def _toggle_theme(self) -> None:
        self.theme_mode = self.theme_var.get()
        if self.theme_mode == "light":
            self.configure(bg="#f5f7fb")
            self._update_colors("#f5f7fb", "#ffffff", "#374151")
        else:
            self.configure(bg="#0f1115")
            self._update_colors("#0f1115", "#171a21", "#c6cede")

    def _pick_accent(self) -> None:
        _, color = colorchooser.askcolor(color=self.accent, parent=self)
        if color:
            self.accent = color
            self._refresh_accent()

    def _refresh_accent(self) -> None:
        style = ttk.Style(self)
        style.configure("Accent.TButton", background=self.accent)
        self._animation_canvas.itemconfigure(self._animation_dot, fill=self.accent)

    def _update_colors(self, background: str, card: str, body_text: str) -> None:
        style = ttk.Style(self)
        style.configure("TFrame", background=background)
        style.configure("Card.TFrame", background=card)
        style.configure("Title.TLabel", background=background)
        style.configure("Subtitle.TLabel", background=background)
        style.configure("TLabel", background=background)
        style.configure("CardTitle.TLabel", background=card)
        style.configure("CardBody.TLabel", background=card, foreground=body_text)

    def _animate_header(self) -> None:
        self._header_phase += self._pulse_direction
        if self._header_phase >= 40:
            self._pulse_direction = -1
        if self._header_phase <= 0:
            self._pulse_direction = 1
        intensity = 120 + self._header_phase
        color = f"#{intensity:02x}{intensity:02x}ff"
        self.header_title.configure(foreground=color)
        self.after(60, self._animate_header)

    def _animate_dot(self) -> None:
        canvas = self._animation_canvas
        width = canvas.winfo_width() or 400
        x1, y1, x2, y2 = canvas.coords(self._animation_dot)
        if x2 >= width - 10:
            self._animation_direction = -1
        if x1 <= 10:
            self._animation_direction = 1
        canvas.move(self._animation_dot, 4 * self._animation_direction, 0)
        self.after(30, self._animate_dot)

    def _set_status(self, message: str) -> None:
        self.status_label.config(text=message)


def run_cli() -> None:
    print(APP_TITLE)
    print("=" * len(APP_TITLE))
    if not is_admin():
        print("[ERROR] Administrator privileges are required.")
        sys.exit(1)

    backup_dir = create_backup_dir()
    backed_up_keys: set[str] = set()

    while True:
        print("\nSelect a tweak to apply:")
        for idx, tweak in enumerate(TWEAKS, start=1):
            print(f"  {idx}. {tweak['label']}")
        print("  R. Restore from backup (.reg)")
        print("  Q. Quit")

        choice = input("> ").strip().lower()
        if choice == "q":
            break
        if choice == "r":
            backup_path = input("Path to .reg backup: ").strip()
            if backup_path:
                try:
                    restore_backup_file(Path(backup_path))
                    print("Backup restored successfully.")
                except RuntimeError as exc:
                    print(f"[ERROR] {exc}")
            continue
        if not choice.isdigit():
            print("Invalid selection.")
            continue
        index = int(choice) - 1
        if index < 0 or index >= len(TWEAKS):
            print("Invalid selection.")
            continue

        tweak = TWEAKS[index]
        try:
            for parent_key in tweak.get("parent_keys", []):
                backup_registry_key(parent_key, backup_dir, backed_up_keys)
            for command in tweak.get("commands", []):
                run_command(command, tweak["label"])
            print(f"[OK] {tweak['label']} applied.")
            if tweak.get("explorer_notice"):
                print("Sign out/in or restart Explorer may be required.")
                restart = input("Restart Explorer now? (y/N): ").strip().lower()
                if restart == "y":
                    restart_explorer()
            post_message = tweak.get("post_message")
            if post_message:
                print(post_message)
        except RuntimeError as exc:
            print(f"[ERROR] {exc}")

    print("\nBackups stored in:", backup_dir)


def main() -> None:
    if not is_windows():
        print("This tool can only run on Windows.")
        sys.exit(1)

    if "--cli" in sys.argv:
        run_cli()
        return

    if not is_admin():
        print("Administrator privileges are required.")
        sys.exit(1)

    app = TweaksApp()
    app.mainloop()


if __name__ == "__main__":
    main()
