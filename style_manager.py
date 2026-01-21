from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ThemePreset:
    name: str
    main_color: str
    glow_color: str
    animation_speed: float


def presets_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        base = Path(appdata)
    else:
        base = Path.home() / "AppData" / "Roaming"
    return base / "7pce" / "presets.json"


def load_presets() -> list[ThemePreset]:
    path = presets_path()
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    presets = []
    for item in payload:
        try:
            presets.append(
                ThemePreset(
                    name=item["name"],
                    main_color=item["main_color"],
                    glow_color=item["glow_color"],
                    animation_speed=float(item.get("animation_speed", 1.0)),
                )
            )
        except KeyError:
            continue
    return presets


def save_presets(presets: list[ThemePreset]) -> None:
    path = presets_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asdict(preset) for preset in presets]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
