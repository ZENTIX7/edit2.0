import ctypes
import datetime as dt
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

APP_TITLE = "7pce Tweaks Utility"
BACKUP_ROOT = Path("backups")


@dataclass(frozen=True)
class Tweak:
    label: str
    description: str
    category: str
    commands: list[list[str]]
    parent_keys: list[str] = field(default_factory=list)
    explorer_notice: bool = False
    post_message: str | None = None


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


def apply_tweak(tweak: Tweak, backup_dir: Path, backed_up: set[str]) -> None:
    for parent_key in tweak.parent_keys:
        backup_registry_key(parent_key, backup_dir, backed_up)
    for command in tweak.commands:
        run_command(command, tweak.label)


def iter_categories(tweaks: Iterable[Tweak]) -> list[str]:
    categories = {tweak.category for tweak in tweaks}
    return [
        "All",
        *sorted(categories, key=str.lower),
    ]


TWEAKS: list[Tweak] = [
    Tweak(
        label="Disable Mouse Acceleration",
        description="Turn off Enhance Pointer Precision.",
        category="Mouse",
        parent_keys=["HKCU\\Control Panel\\Mouse"],
        commands=[
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
    ),
    Tweak(
        label="Reduce Menu Show Delay",
        description="Make menus appear instantly.",
        category="UI",
        parent_keys=["HKCU\\Control Panel\\Desktop"],
        commands=[
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
        explorer_notice=True,
    ),
    Tweak(
        label="Disable Taskbar Animations",
        description="Turn off taskbar animation effects.",
        category="UI",
        parent_keys=[
            "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\Advanced"
        ],
        commands=[
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
        explorer_notice=True,
    ),
    Tweak(
        label="Disable Transparency Effects",
        description="Disable acrylic transparency in Windows.",
        category="UI",
        parent_keys=[
            "HKCU\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Themes\\Personalize"
        ],
        commands=[
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
        explorer_notice=True,
    ),
    Tweak(
        label="Disable Aero Peek",
        description="Disable Windows Aero Peek behavior.",
        category="UI",
        parent_keys=["HKCU\\Software\\Microsoft\\Windows\\DWM"],
        commands=[
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
        explorer_notice=True,
    ),
    Tweak(
        label="Disable Xbox Game Bar / GameDVR",
        description="Disable Game Bar overlays and background capture.",
        category="UI",
        parent_keys=[
            "HKCU\\Software\\Microsoft\\GameBar",
            "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\GameDVR",
        ],
        commands=[
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
    ),
    Tweak(
        label="Network Maintenance",
        description="Flush DNS, release/renew IP, reset Winsock (reboot required).",
        category="Network",
        commands=[
            ["ipconfig", "/flushdns"],
            ["ipconfig", "/release"],
            ["ipconfig", "/renew"],
            ["netsh", "winsock", "reset"],
        ],
        post_message="Winsock reset completed. A reboot is required.",
    ),
]
