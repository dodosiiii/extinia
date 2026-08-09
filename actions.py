"""Actions exécutées par le système à la fin du compte à rebours (Windows)."""

import ctypes
import subprocess

ACTIONS = {
    "shutdown": "Éteindre le PC",
    "veille": "Mettre en veille",
    "restart": "Redémarrer",
    "lock": "Verrouiller la session",
    "logout": "Déconnexion",
}


def eteindre() -> None:
    subprocess.run(["shutdown", "/s", "/t", "0"], check=False)


def redemarrer() -> None:
    subprocess.run(["shutdown", "/r", "/t", "0"], check=False)


def deconnexion() -> None:
    subprocess.run(["shutdown", "/l"], check=False)


def veille() -> None:
    try:
        ctypes.windll.powrprof.SetSuspendState(0, 1, 0)
    except Exception:
        subprocess.run(
            ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"], check=False
        )


def verrouiller() -> None:
    ctypes.windll.user32.LockWorkStation()


def execute(action_key: str) -> None:
    FUNCTIONS = {
        "shutdown": eteindre,
        "veille": veille,
        "restart": redemarrer,
        "lock": verrouiller,
        "logout": deconnexion,
    }
    FUNCTIONS[action_key]()