"""Sauvegarde et chargement des préférences utilisateur (JSON dans %APPDATA%)."""

import json
import os

DEFAULTS = {
    "hours": 0,
    "minutes": 10,
    "seconds": 0,
    "action": "shutdown",
    "always_on_top": False,
    "mute": False,
    "confirm_delay": 3,
}


def _settings_path() -> str:
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    folder = os.path.join(base, "Extinia")
    try:
        os.makedirs(folder, exist_ok=True)
    except Exception:
        return os.path.join(os.path.expanduser("~"), ".extinia_settings.json")
    return os.path.join(folder, "settings.json")


def load() -> dict:
    """Charge les préférences sauvegardées, ou les valeurs par défaut si absentes/corrompues."""
    merged = DEFAULTS.copy()
    try:
        with open(_settings_path(), "r", encoding="utf-8") as f:
            data = json.load(f)
        for key, default in DEFAULTS.items():
            if key not in data:
                continue
            value = data[key]
            if isinstance(default, bool):
                if isinstance(value, bool):
                    merged[key] = value
            elif isinstance(default, int):
                try:
                    merged[key] = max(int(value), 0)
                except (TypeError, ValueError):
                    pass
            else:
                merged[key] = value
    except Exception:
        pass
    return merged


def save(data: dict) -> None:
    """Sauvegarde les préférences. Échoue silencieusement si le disque est inaccessible."""
    try:
        with open(_settings_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
