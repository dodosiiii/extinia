"""Icône dans la barre des tâches (zone de notification) : minutes restantes, clic pour ouvrir.

Sans pystray / Pillow, l'application fonctionne quand même (sans icône).
"""

import threading

from config import ACCENT, APP_NAME, DANGER, IDLE, MUTED, WARN

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont

    TRAY_AVAILABLE = True
except Exception:
    pystray = None
    TRAY_AVAILABLE = False


def _font(size: int, bold: bool = False) -> ImageFont.ImageFont:
    try:
        name = "segoeuib.ttf" if bold else "segoeui.ttf"
        return ImageFont.truetype(name, size)
    except Exception:
        return ImageFont.load_default()


def logo_image(size: int = 64) -> Image.Image:
    """Logo de l'application : carré arrondi bleu avec une horloge blanche."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=ACCENT)
    cx = cy = size / 2
    r = size * 0.30
    w = max(2, size // 14)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline="white", width=w)
    d.line([cx, cy, cx, cy - r * 0.62], fill="white", width=w)
    d.line([cx, cy, cx + r * 0.45, cy + r * 0.12], fill="white", width=w)
    return img


def status_image(state: str, minutes: int) -> Image.Image:
    """Image de l'icône selon l'état : temps restant en gros chiffres."""
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=IDLE)

    if state == "paused":
        bar_w = size // 8
        gap = size // 5
        rel = size // 8
        for x in (rel, rel + gap, rel + 2 * gap):
            d.rectangle([x, size // 3, x + bar_w, size - size // 3], fill="white")
        return img
    if state == "stopped":
        d.ellipse(
            [size // 2 - size // 6, size // 2 - size // 6,
             size // 2 + size // 6, size // 2 + size // 6],
            outline="white", width=size // 16,
        )
        return img

    if minutes > 10:
        bg = ACCENT
    elif minutes >= 1:
        bg = WARN
    else:
        bg = DANGER
    img2 = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d2 = ImageDraw.Draw(img2)
    d2.rounded_rectangle([0, 0, size - 1, size - 1], radius=size // 5, fill=bg)
    text = str(min(minutes, 999))
    if len(text) <= 2:
        font = _font(32, bold=True)
    else:
        font = _font(24, bold=True)
    box = d2.textbbox((0, 0), text, font=font)
    d2.text(
        ((size - (box[2] - box[0])) / 2 - box[0],
         (size - (box[3] - box[1])) / 2 - box[1]),
        text, font=font, fill="white",
    )
    return img2


class Tray:
    """Icône de la zone de notification, reliée à l'application."""

    def __init__(self, app) -> None:
        self.app = app
        self.icon = None

    @property
    def available(self) -> bool:
        return TRAY_AVAILABLE

    def start(self) -> None:
        if not TRAY_AVAILABLE:
            return
        menu = pystray.Menu(
            pystray.MenuItem(f"Ouvrir {APP_NAME}", self._open, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Pause / Reprendre", self._toggle),
            pystray.MenuItem("Arrêter le compte à rebours", self._stop),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quitter", self._quit),
        )
        self.icon = pystray.Icon(APP_NAME.lower(), logo_image(64), APP_NAME, menu)
        threading.Thread(target=self.icon.run, daemon=True).start()

    def refresh(self, state: str, tooltip: str, minutes: int = 0) -> None:
        if self.icon is None:
            return
        self.icon.title = tooltip
        try:
            self.icon.update_image(status_image(state, minutes))
        except AttributeError:
            # Versions récentes de pystray : pas de update_image(),
            # on réassigne directement la propriété .icon.
            self.icon.icon = status_image(state, minutes)

    def notify(self, message: str) -> None:
        if self.icon is None:
            return
        try:
            self.icon.notify(message, APP_NAME)
        except Exception:
            pass

    def stop(self) -> None:
        if self.icon is not None:
            try:
                self.icon.stop()
            except Exception:
                pass

    def _open(self, _icon=None, _item=None) -> None:
        self.app.root.after(0, self.app.show_window)

    def _toggle(self, _icon=None, _item=None) -> None:
        self.app.root.after(0, self.app.toggle_from_tray)

    def _stop(self, _icon=None, _item=None) -> None:
        self.app.root.after(0, self.app.stop_from_tray)

    def _quit(self, _icon=None, _item=None) -> None:
        self.app.root.after(0, self.app.quit_from_tray)