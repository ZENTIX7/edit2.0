import os
import subprocess
import sys
import tkinter as tk
from tkinter import colorchooser, messagebox, ttk

APP_TITLE = "7pce Tweaks Utility"

TWEAKS = [
    {
        "label": "Enable ANSI Colors",
        "description": "Turns on ANSI escape sequences for the Windows console.",
        "commands": [
            [
                "reg",
                "add",
                "HKCU\\CONSOLE",
                "/v",
                "VirtualTerminalLevel",
                "/t",
                "REG_DWORD",
                "/d",
                "1",
                "/f",
            ]
        ],
    },
    {
        "label": "Disable UAC",
        "description": "Disables User Account Control (requires reboot).",
        "commands": [
            [
                "reg",
                "add",
                "HKLM\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System",
                "/v",
                "EnableLUA",
                "/t",
                "REG_DWORD",
                "/d",
                "0",
                "/f",
            ]
        ],
    },
    {
        "label": "Create Restore Point",
        "description": "Creates a system restore point before applying other tweaks.",
        "commands": [
            [
                "powershell",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                "Checkpoint-Computer -Description '7pce Tweaks Restore Point' -RestorePointType 'MODIFY_SETTINGS'",
            ]
        ],
    },
    {
        "label": "Open System Restore",
        "description": "Launches the Windows restore UI.",
        "commands": [["rstrui.exe"]],
    },
]


class TweaksApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("940x620")
        self.minsize(900, 580)
        self.configure(bg="#0f1115")
        self.accent = "#7d5cff"
        self.theme_mode = "dark"
        self._header_phase = 0
        self._pulse_direction = 1
        self._build_style()
        self._build_layout()
        self._animate_header()

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TFrame",
            background="#0f1115",
        )
        style.configure(
            "Card.TFrame",
            background="#171a21",
        )
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
        style.map(
            "Accent.TButton",
            background=[("active", "#6a49ff")],
        )
        style.configure(
            "TLabel",
            background="#0f1115",
        )
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
        self._animation_dot = canvas.create_oval(10, 40, 50, 80, fill=self.accent, width=0)
        self._animation_direction = 1
        self._animate_dot()

    def _apply_tweak(self, tweak: dict) -> None:
        self._set_status(f"Applying: {tweak['label']}...")
        self.progress.start(10)
        self.update_idletasks()

        if os.name != "nt":
            self.progress.stop()
            self._set_status("This tweak requires Windows.")
            messagebox.showinfo(
                APP_TITLE,
                "Tweaks can only be applied on Windows systems.",
            )
            return

        for command in tweak.get("commands", []):
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                shell=False,
            )
            if result.returncode != 0:
                self.progress.stop()
                self._set_status("Tweak failed. Check permissions.")
                messagebox.showerror(
                    APP_TITLE,
                    f"Failed to apply {tweak['label']}:\n{result.stderr.strip()}",
                )
                return

        self.progress.stop()
        self._set_status(f"{tweak['label']} applied successfully.")
        messagebox.showinfo(APP_TITLE, "Tweak applied successfully.")

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


def main() -> None:
    app = TweaksApp()
    app.mainloop()


if __name__ == "__main__":
    main()
