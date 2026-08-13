"""Interface graphique tkinter d'Extinia (compte à rebours PC)."""

import base64
import datetime
import io
import math
import os
import time
import tkinter as tk
import traceback
from tkinter import ttk

import actions
import settings
from config import (
    ACCENT,
    ACCENT_DOWN,
    ACCENT_SOFT,
    APP_AUTHOR,
    APP_NAME,
    APP_TAGLINE,
    APP_VERSION,
    BG,
    CARD,
    CARD_BORDER,
    DANGER,
    DANGER_DIM,
    FIELD,
    FONT,
    MUTED,
    SHADOW,
    TEXT,
    WARN,
)
from countdown import Countdown
from tray import Tray, logo_image

try:
    from PIL import Image, ImageDraw, ImageTk

    PILLOW_AVAILABLE = True
except Exception:
    Image = None
    ImageDraw = None
    ImageTk = None
    PILLOW_AVAILABLE = False

PRESETS = {"1 min": 60, "5 min": 300, "10 min": 600, "30 min": 1800, "1 h": 3600}

if PILLOW_AVAILABLE:
    _RESAMPLE = getattr(Image, "Resampling", Image).LANCZOS
    GLOW_COLORS = {
        "accent": (124, 108, 255),
        "warn": (242, 169, 60),
        "danger": (255, 93, 108),
    }


def _make_glow(size: int = 128) -> dict:
    """Halos radiaux doux (dégradés violets/orange/rouge transparents)."""
    glows = {}
    for key, color in GLOW_COLORS.items():
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        px = img.load()
        c = size / 2
        max_r = size / 2 - 1
        peak = 55 if key == "warn" else 70
        for y in range(size):
            for x in range(size):
                r = ((x - c + 0.5) ** 2 + (y - c + 0.5) ** 2) ** 0.5 / max_r
                if r < 1:
                    px[x, y] = (color[0], color[1], color[2],
                                int(peak * (1 - r) ** 2.2))
        glows[key] = img
    return glows


def _to_photo(pil_img) -> "tk.PhotoImage":
    """Convertit une image Pillow en PhotoImage tkinter (rapide)."""
    if ImageTk is not None:
        return ImageTk.PhotoImage(pil_img)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())

ACTION_ICONS = {
    "shutdown": "⏻",
    "veille": "🌙",
    "restart": "⟳",
    "lock": "🔒",
    "logout": "⎋",
}


def format_time(seconds: float) -> str:
    total = int(math.ceil(max(seconds, 0)))
    h, rest = divmod(total, 3600)
    m, s = divmod(rest, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _draw_icon(painter, size: int = 20) -> "tk.PhotoImage":
    """Dessine une petite icône avec Pillow et la convertit en PhotoImage
    tkinter (fond transparent, couleur ACCENT, rendu net)."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    painter(ImageDraw.Draw(img), size)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())


def _paint_tray_icon(d, size: int) -> None:
    """Icône « réduire dans la barre des tâches » : fenêtre + flèche vers la barre."""
    w = max(1, size // 10)
    d.rectangle([size * 0.2, size * 0.1, size * 0.8, size * 0.5],
                outline=ACCENT, width=w)
    d.line([size * 0.5, size * 0.5, size * 0.5, size * 0.78],
           fill=ACCENT, width=w)
    d.line([size * 0.5, size * 0.78, size * 0.35, size * 0.63],
           fill=ACCENT, width=w)
    d.line([size * 0.5, size * 0.78, size * 0.65, size * 0.63],
           fill=ACCENT, width=w)
    d.line([size * 0.2, size * 0.88, size * 0.8, size * 0.88],
           fill=ACCENT, width=w)


def _paint_mini_icon(d, size: int) -> None:
    """Icône « mode mini » : petit anneau avec aiguilles d'horloge."""
    w = max(1, size // 10)
    r = size * 0.33
    cx = cy = size / 2
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ACCENT, width=w)
    d.line([cx, cy, cx, cy - r * 0.7], fill=ACCENT, width=w)
    d.line([cx, cy, cx + r * 0.5, cy + r * 0.15], fill=ACCENT, width=w)


def _paint_restore_icon(d, size: int) -> None:
    """Icône « revenir à la fenêtre complète » : deux carrés superposés."""
    w = max(1, size // 10)
    d.rectangle([size * 0.25, size * 0.32, size * 0.75, size * 0.72],
                outline=ACCENT, width=w)
    d.rectangle([size * 0.38, size * 0.18, size * 0.88, size * 0.58],
                outline=ACCENT, width=w)


def log_exception(exc_type, exc_value, exc_tb) -> None:
    """Journalise une exception dans %APPDATA%\\Extinia\\error.log (robustesse
    hors vacances : on peut relire le journal si l'app plante)."""
    try:
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        folder = os.path.join(base, "Extinia")
        os.makedirs(folder, exist_ok=True)
        with open(os.path.join(folder, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"\n[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] "
                    f"{exc_type.__name__}: {exc_value}\n")
            traceback.print_exception(exc_type, exc_value, exc_tb, file=f)
    except Exception:
        pass


class RoundedCard(tk.Frame):
    """Carte à coins arrondis avec une légère ombre portée pour donner de la profondeur.

    S'adapte à la taille disponible : le contenu reste centré lorsque la
    carte est étirée par la mise en page.
    """

    def __init__(self, parent, radius: int = 16, bg_color: str = CARD,
                 border: str = CARD_BORDER, page_bg: str = BG, shadow: bool = True,
                 **kwargs) -> None:
        super().__init__(parent, bg=page_bg, **kwargs)
        self.radius = radius
        self.bg_color = bg_color
        self.border = border
        self.shadow = shadow
        self.canvas = tk.Canvas(self, bg=page_bg, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.body = tk.Frame(self.canvas, bg=bg_color)
        self._body_item = self.canvas.create_window(2, 2, window=self.body, anchor="nw")
        self._card_item = None
        self._shadow_item = None
        self.body.bind("<Configure>", self._sync)
        self.canvas.bind("<Configure>", self._draw)

    def _sync(self, _event=None) -> None:
        # Taille minimale du canvas = contenu + ombre ; au-delà, il s'étire
        # avec la fenêtre et _draw() recentre le contenu.
        self.canvas.config(
            width=self.body.winfo_reqwidth() + 8,
            height=self.body.winfo_reqheight() + 8,
        )
        self._draw()

    def _draw(self, _event=None) -> None:
        # Mise à jour par coords() : aucun objet recréé, donc fluide même
        # pendant un redimensionnement continu.
        body_w = self.body.winfo_reqwidth()
        body_h = self.body.winfo_reqheight()
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        x = max(4, (cw - body_w) // 2)
        y = max(4, (ch - body_h) // 2)
        self.canvas.coords(self._body_item, x, y)
        if self.shadow:
            points = self._round_rect_points(x + 3, y + 4, x + body_w - 1 + 3,
                                             y + body_h - 1 + 4, self.radius)
            if self._shadow_item is None:
                self._shadow_item = self.canvas.create_polygon(
                    points, smooth=True, fill=SHADOW, outline="", tags="bg")
            else:
                self.canvas.coords(self._shadow_item, *points)
        points = self._round_rect_points(x, y, x + body_w - 1, y + body_h - 1, self.radius)
        if self._card_item is None:
            self._card_item = self.canvas.create_polygon(
                points, smooth=True, fill=self.bg_color,
                outline=self.border, width=1, tags="bg")
        else:
            self.canvas.coords(self._card_item, *points)
        self.canvas.tag_lower("bg")
        # Liseré lumineux sur l'arête supérieure (effet de profondeur).
        self.canvas.delete("hl")
        self.canvas.create_line(x + 3, y + 2, x + body_w - 4, y + 2,
                                fill="#23293a", tags="hl")
        self.canvas.tag_raise("hl")

    @staticmethod
    def _round_rect_points(x1, y1, x2, y2, r) -> list:
        return [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]


class Tooltip:
    """Petite bulle d'aide affichée au survol d'un widget."""

    def __init__(self, widget: tk.Widget, text: str) -> None:
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self._show, add="+")
        widget.bind("<Leave>", self._hide, add="+")

    def _show(self, _event=None) -> None:
        if self.tip is not None or not self.text:
            return
        try:
            x = self.widget.winfo_rootx() + 6
            y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
            self.tip = tk.Toplevel(self.widget)
            self.tip.wm_overrideredirect(True)
            self.tip.wm_geometry(f"+{x}+{y}")
            tk.Label(self.tip, text=self.text, bg=CARD, fg=TEXT, font=(FONT, 8),
                     padx=8, pady=4, relief="solid", bd=1,
                     highlightbackground=CARD_BORDER).pack()
        except Exception:
            self.tip = None

    def _hide(self, _event=None) -> None:
        if self.tip is not None:
            try:
                self.tip.destroy()
            except Exception:
                pass
            self.tip = None


class ThemedDialog(tk.Toplevel):
    """Boîte de dialogue assortie au thème sombre (remplace messagebox).

    Entrée valide l'action par défaut, Échap ou la croix annule.
    """

    def __init__(self, parent: tk.Misc, title: str, message: str,
                 buttons: tuple = ("OK",), default: int = 0,
                 icon: str = "?", icon_color: str = ACCENT) -> None:
        super().__init__(parent)
        self.configure(bg=BG)
        self.title(title)
        self.resizable(False, False)
        self.transient(parent)
        self._result = None
        self.protocol("WM_DELETE_WINDOW", self._dismiss)

        card = RoundedCard(self, radius=14, page_bg=BG)
        card.pack(padx=16, pady=16)
        head = tk.Frame(card.body, bg=CARD)
        head.pack(fill="x", padx=18, pady=(16, 2))
        tk.Label(head, text=icon, bg=CARD, fg=icon_color,
                 font=(FONT, 20, "bold")).pack(side="left", padx=(0, 10))
        tk.Label(head, text=title, bg=CARD, fg=TEXT,
                 font=(FONT, 12, "bold")).pack(anchor="w")
        tk.Label(card.body, text=message, bg=CARD, fg=MUTED, font=(FONT, 10),
                 justify="left", wraplength=340).pack(padx=24, pady=(4, 14))
        btns = tk.Frame(card.body, bg=CARD)
        btns.pack(pady=(0, 16))
        for index, label in enumerate(buttons):
            style = "Accent.TButton" if index == 0 else "TButton"
            btn = ttk.Button(btns, text=label, style=style, width=10,
                             command=lambda i=index: self._choose(i))
            btn.pack(side="left", padx=4)
            if index == default:
                btn.focus_set()
        self.bind("<Return>", lambda _e: self._choose(default))
        self.bind("<Escape>", lambda _e: self._dismiss())
        self._center(parent)
        self.grab_set()
        self.wait_window(self)

    def _center(self, parent: tk.Misc) -> None:
        self.update_idletasks()
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        try:
            if str(parent.state()) == "withdrawn":
                x = (self.winfo_screenwidth() - w) // 2
                y = (self.winfo_screenheight() - h) // 2
            else:
                x = parent.winfo_rootx() + (parent.winfo_width() - w) // 2
                y = parent.winfo_rooty() + (parent.winfo_height() - h) // 2
        except Exception:
            x = (self.winfo_screenwidth() - w) // 2
            y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")

    def _choose(self, index: int) -> None:
        if self._result is not None:
            return
        self._result = index
        self.destroy()

    def _dismiss(self) -> None:
        if self._result is not None:
            return
        self._result = None
        self.destroy()

    def confirmed(self) -> bool:
        """True si le premier bouton (Oui / OK) a été choisi."""
        return self._result == 0


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Compte à rebours PC")
        self.root.resizable(True, True)
        self.root.configure(bg=BG)
        self._set_window_icon()

        self.prefs = settings.load()

        self.countdown = Countdown(600)
        self.action_var = tk.StringVar(value=self.prefs.get("action", "shutdown"))
        self.always_on_top_var = tk.BooleanVar(value=self.prefs.get("always_on_top", False))
        self.mute_var = tk.BooleanVar(value=self.prefs.get("mute", False))
        self.confirm_delay_var = tk.IntVar(value=self.prefs.get("confirm_delay", 3))
        self.tray = Tray(self)
        self._execute_after_id = None
        self._overlay = None
        self._overlay_label = None
        self._overlay_deadline = 0.0
        self._last_tray_sec = -1
        self._tray_state = "stopped"
        self._finishing = False
        self._paused = False
        self._blink_off = False
        self._blink_counter = 0
        self._alerted = set()
        self._ring_scale = 1.0
        self._ring_pending = False
        self._tick_id = None
        self._mini = None
        self._mini_mode = False
        self._mini_drag_dx = 0
        self._mini_drag_dy = 0

        # Icônes des boutons (vraies icônes dessinées, ou texte si Pillow absent).
        self._icon_tray = None
        self._icon_mini = None
        self._icon_restore = None
        if PILLOW_AVAILABLE:
            self._icon_tray = _draw_icon(_paint_tray_icon)
            self._icon_mini = _draw_icon(_paint_mini_icon)
            self._icon_restore = _draw_icon(_paint_restore_icon)

        # Halos lumineux pour l'anneau de temps restant.
        self._glow_base = _make_glow() if PILLOW_AVAILABLE else {}
        self._glow_photo = None

        self._setup_styles()
        self._build_ui()
        self._center_window()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<space>", self._on_space_key)
        self.root.bind("<Escape>", self._on_escape_key)
        self.root.attributes("-topmost", self.always_on_top_var.get())
        self.root.report_callback_exception = self._report_callback_exception

        self._apply_saved_time()
        self._set_status("Prêt. Réglez le temps, choisissez une action, cliquez sur Démarrer.", "idle")
        self.canvas.itemconfig(self.time_label, fill=ACCENT)
        self._tick()

    # --- divers ---

    def _center_window(self) -> None:
        """Centre la fenêtre sur l'écran et fixe sa taille minimale
        (le contenu ne peut pas être coupé en réduisant)."""
        self.root.update_idletasks()
        w = self.root.winfo_reqwidth()
        h = self.root.winfo_reqheight()
        self.root.minsize(w, h)
        x = max((self.root.winfo_screenwidth() - w) // 2, 0)
        y = max((self.root.winfo_screenheight() - h) // 2, 0)
        self.root.geometry(f"{w}x{h}+{x}+{y}")

    def _report_callback_exception(self, exc_type, exc_value, exc_tb) -> None:
        log_exception(exc_type, exc_value, exc_tb)

    # --- thème et logo ---

    def _set_window_icon(self) -> None:
        try:
            buf = io.BytesIO()
            logo_image(48).save(buf, format="PNG")
            photo = tk.PhotoImage(data=base64.b64encode(buf.getvalue()).decode())
            self.root.iconphoto(True, photo)
            self._logo_photo = photo
        except Exception:
            pass

    def _setup_styles(self) -> None:
        try:
            style = ttk.Style(self.root)
            style.theme_use("clam")
            style.configure(".", background=BG, foreground=TEXT, bordercolor=CARD_BORDER)

            style.configure("TFrame", background=BG)
            style.configure("Card.TFrame", background=CARD)

            style.configure("TLabel", background=BG, foreground=TEXT)
            style.configure("Muted.TLabel", background=BG, foreground=MUTED)
            style.configure("BoxLabel.TLabel", background=BG, foreground=MUTED,
                            font=(FONT, 8, "bold"))
            style.configure("Small.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))

            style.configure("CardTitle.TLabel", background=CARD, foreground=TEXT,
                            font=(FONT, 10, "bold"))
            style.configure("CardBoxLabel.TLabel", background=CARD, foreground=MUTED,
                            font=(FONT, 8, "bold"))

            style.configure("TEntry", fieldbackground=FIELD, foreground=TEXT,
                            insertcolor=TEXT, bordercolor=CARD_BORDER, padding=4,
                            font=(FONT, 11))
            style.configure("Big.TEntry", fieldbackground=FIELD, foreground=TEXT,
                            insertcolor=TEXT, bordercolor=CARD_BORDER, padding=6,
                            font=(FONT, 19, "bold"))
            style.map("Big.TEntry", bordercolor=[("focus", ACCENT)])

            style.configure("TButton", background=CARD, foreground=TEXT,
                            bordercolor=CARD_BORDER, padding=(16, 9), font=(FONT, 10, "bold"),
                            relief="flat")
            style.map("TButton", background=[("active", "#20242f"), ("pressed", "#282d3a"),
                                              ("disabled", BG)],
                      bordercolor=[("active", ACCENT)],
                      foreground=[("disabled", MUTED)])
            style.configure("Accent.TButton", background=ACCENT, foreground="#ffffff",
                            borderwidth=0, padding=(18, 10))
            style.map("Accent.TButton",
                      background=[("active", ACCENT_DOWN), ("pressed", ACCENT_DOWN),
                                  ("disabled", "#2a2740")],
                      foreground=[("disabled", MUTED)])
            style.configure("Chip.TButton", background=FIELD, bordercolor=CARD_BORDER,
                            padding=(11, 6), font=(FONT, 9, "bold"), relief="flat")
            style.map("Chip.TButton", background=[("active", ACCENT_SOFT), ("pressed", ACCENT_SOFT)],
                      bordercolor=[("active", ACCENT)],
                      foreground=[("active", ACCENT)])
            style.configure("ChipActive.TButton", background=ACCENT, bordercolor=ACCENT,
                            padding=(11, 6), font=(FONT, 9, "bold"), relief="flat")
            style.map("ChipActive.TButton",
                      background=[("active", ACCENT_DOWN), ("pressed", ACCENT_DOWN)],
                      bordercolor=[("active", ACCENT)],
                      foreground=[("active", "#ffffff")])
            style.configure("Icon.TButton", background=BG, bordercolor=BG,
                            padding=(6, 4), font=(FONT, 11), relief="flat")
            style.map("Icon.TButton", background=[("active", ACCENT_SOFT), ("pressed", ACCENT_SOFT)],
                      bordercolor=[("active", ACCENT)])

            style.configure("TRadiobutton", background=CARD, foreground=TEXT,
                            indicatorbackground=FIELD, indicatorforeground=CARD,
                            borderwidth=0, font=(FONT, 10), padding=(2, 5))
            style.map("TRadiobutton",
                      indicatorbackground=[("selected", ACCENT), ("active", "#343a49")],
                      foreground=[("disabled", MUTED), ("active", TEXT)])

            style.configure("TCheckbutton", background=BG, foreground=MUTED,
                            indicatorbackground=FIELD, indicatorforeground=BG,
                            borderwidth=0, font=(FONT, 9), padding=(2, 3))
            style.map("TCheckbutton",
                      indicatorbackground=[("selected", ACCENT), ("active", "#343a49")],
                      foreground=[("selected", TEXT), ("active", TEXT)])

            style.configure("OptionRadio.TRadiobutton", background=BG, foreground=MUTED,
                            indicatorbackground=FIELD, indicatorforeground=BG,
                            borderwidth=0, font=(FONT, 9), padding=(2, 3))
            style.map("OptionRadio.TRadiobutton",
                      indicatorbackground=[("selected", ACCENT), ("active", "#343a49")],
                      foreground=[("selected", TEXT), ("active", TEXT)])

            style.configure("Extend.TButton", background=FIELD, bordercolor=CARD_BORDER,
                            padding=(10, 6), font=(FONT, 9, "bold"), relief="flat")
            style.map("Extend.TButton", background=[("active", ACCENT_SOFT), ("pressed", ACCENT_SOFT),
                                                     ("disabled", BG)],
                      bordercolor=[("active", ACCENT)],
                      foreground=[("active", ACCENT), ("disabled", MUTED)])
        except Exception:
            pass

    # --- interface ---

    def _build_ui(self) -> None:
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        outer = tk.Frame(self.root, bg=BG)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)
        outer.rowconfigure(3, weight=1)  # cartes : s'étirent en hauteur
        outer.rowconfigure(5, weight=1)  # anneau : s'étire en hauteur

        # --- en-tête ---
        header = tk.Frame(outer, bg=BG)
        header.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=(18, 4))
        if getattr(self, "_logo_photo", None) is not None:
            tk.Label(header, image=self._logo_photo, bg=BG).pack(side="left", padx=(0, 10))
        title_box = tk.Frame(header, bg=BG)
        title_box.pack(side="left")
        tk.Label(title_box, text=APP_NAME, bg=BG, fg=TEXT,
                 font=(FONT, 18, "bold")).pack(anchor="w")
        tk.Label(title_box, text=APP_TAGLINE, bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(anchor="w")

        if self._icon_tray is not None:
            reduce_btn = ttk.Button(header, image=self._icon_tray,
                                    style="Icon.TButton", command=self._minimize_to_tray)
        else:
            reduce_btn = ttk.Button(header, text="🗕", style="Icon.TButton", width=3,
                                    command=self._minimize_to_tray)
        reduce_btn.pack(side="right", padx=(4, 0))
        Tooltip(reduce_btn, "Réduire dans la barre des tâches")

        if self._icon_mini is not None:
            mini_btn = ttk.Button(header, image=self._icon_mini,
                                  style="Icon.TButton", command=self._enter_mini)
        else:
            mini_btn = ttk.Button(header, text="▁", style="Icon.TButton", width=3,
                                  command=self._enter_mini)
        mini_btn.pack(side="right", padx=(4, 0))
        Tooltip(mini_btn, "Mode mini : petit anneau déplaçable partout")

        divider = tk.Frame(outer, bg=CARD_BORDER, height=1)
        divider.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(2, 10))

        # --- carte : temps avant action (colonne gauche) ---
        self._section_label(outer, "DURÉE").grid(
            row=2, column=0, sticky="w", padx=20, pady=(0, 4))

        card_time = RoundedCard(outer, radius=16)
        card_time.grid(row=3, column=0, sticky="nsew", padx=(20, 10), pady=(0, 12))

        boxes = tk.Frame(card_time.body, bg=CARD)
        boxes.pack(padx=14, pady=(14, 8))
        self.hours = self._time_box(boxes, "H", "0", max_value=99)
        self._sep(boxes)
        self.minutes = self._time_box(boxes, "MIN", "10", max_value=59)
        self._sep(boxes)
        self.seconds = self._time_box(boxes, "SEC", "0", max_value=59)

        presets = tk.Frame(card_time.body, bg=CARD)
        presets.pack(fill="x", padx=14, pady=(4, 14))
        ttk.Label(presets, text="RAPIDE", style="CardBoxLabel.TLabel").pack(anchor="w", pady=(0, 5))
        presets_row = tk.Frame(presets, bg=CARD)
        presets_row.pack(fill="x")
        self.preset_buttons = []
        for name, seconds in PRESETS.items():
            btn = ttk.Button(presets_row, text=name, style="Chip.TButton", width=5,
                             command=lambda s=seconds: self._set_time(s))
            btn.pack(side="left", padx=2, fill="x", expand=True)
            self.preset_buttons.append(btn)

        # --- carte : action à la fin (colonne droite) ---
        self._section_label(outer, "ACTION FINALE").grid(
            row=2, column=1, sticky="w", padx=(10, 20), pady=(0, 4))

        card_action = RoundedCard(outer, radius=16)
        card_action.grid(row=3, column=1, sticky="nsew", padx=(10, 20), pady=(0, 12))

        action_body = tk.Frame(card_action.body, bg=CARD)
        action_body.pack(fill="x", padx=12, pady=10)
        self.radio_buttons = []
        for key, label in actions.ACTIONS.items():
            icon = ACTION_ICONS.get(key, "•")
            rb = ttk.Radiobutton(action_body, text=f"{icon}  {label}", value=key,
                                 variable=self.action_var, command=self._save_prefs)
            rb.pack(anchor="w", padx=8, pady=2)
            self.radio_buttons.append(rb)

        # --- options ---
        options_row = tk.Frame(outer, bg=BG)
        options_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(0, 2))

        options = tk.Frame(options_row, bg=BG)
        options.pack(side="left")
        top_chk = ttk.Checkbutton(options, text="Toujours au premier plan",
                                  variable=self.always_on_top_var,
                                  command=self._on_toggle_always_on_top)
        top_chk.pack(side="left")
        mute_chk = ttk.Checkbutton(options, text="Son désactivé",
                                   variable=self.mute_var, command=self._save_prefs)
        mute_chk.pack(side="left", padx=(16, 0))

        delay_row = tk.Frame(options_row, bg=BG)
        delay_row.pack(side="right")
        tk.Label(delay_row, text="Délai :", bg=BG, fg=MUTED,
                 font=(FONT, 9)).pack(side="left", padx=(0, 6))
        for value in (3, 5, 10):
            ttk.Radiobutton(delay_row, text=f"{value}s", value=value,
                            variable=self.confirm_delay_var, style="OptionRadio.TRadiobutton",
                            command=self._save_prefs).pack(side="left")

        # --- anneau de temps restant ---
        ring = tk.Frame(outer, bg=BG)
        ring.grid(row=5, column=0, columnspan=2, sticky="nsew", pady=(10, 0))
        self._section_label(ring, "TEMPS RESTANT").pack(pady=(2, 0))
        self.canvas = tk.Canvas(ring, width=200, height=200, bg=BG, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, pady=(4, 0))
        self.canvas.bind("<Configure>", self._redraw_ring)
        self._redraw_ring_now()

        # --- boutons de contrôle ---
        frame_buttons = tk.Frame(outer, bg=BG)
        frame_buttons.grid(row=6, column=0, columnspan=2, pady=(12, 6))
        self.start_btn = ttk.Button(frame_buttons, text="▶  Démarrer", style="Accent.TButton",
                                    width=14, command=self._start)
        self.pause_btn = ttk.Button(frame_buttons, text="⏸  Pause", width=11,
                                    command=self._pause, state="disabled")
        self.stop_btn = ttk.Button(frame_buttons, text="■  Arrêter", width=11,
                                   command=self._stop, state="disabled")
        self.start_btn.pack(side="left", padx=4)
        self.pause_btn.pack(side="left", padx=4)
        self.stop_btn.pack(side="left", padx=4)
        Tooltip(self.start_btn, "Espace")
        Tooltip(self.pause_btn, "Espace")
        Tooltip(self.stop_btn, "Échap")

        extend_row = tk.Frame(outer, bg=BG)
        extend_row.grid(row=7, column=0, columnspan=2, pady=(0, 8))
        self.extend1_btn = ttk.Button(extend_row, text="+1 min", style="Extend.TButton",
                                      command=lambda: self._extend(60), state="disabled")
        self.extend5_btn = ttk.Button(extend_row, text="+5 min", style="Extend.TButton",
                                      command=lambda: self._extend(300), state="disabled")
        self.extend1_btn.pack(side="left", padx=3)
        self.extend5_btn.pack(side="left", padx=3)

        # --- pied de page ---
        footer = tk.Frame(outer, bg=BG)
        footer.grid(row=8, column=0, columnspan=2, sticky="ew", padx=20, pady=(6, 16))
        footer.columnconfigure(0, weight=1)

        status_box = tk.Frame(footer, bg=BG)
        status_box.grid(row=0, column=0, sticky="w")
        self.status_dot = tk.Label(status_box, text="●", bg=BG, fg=MUTED, font=(FONT, 9))
        self.status_dot.pack(side="left", padx=(0, 6))
        self.status_label = tk.Label(status_box, text="", bg=BG, fg=MUTED, font=(FONT, 9))
        self.status_label.pack(side="left")

        version_pill = tk.Frame(footer, bg=ACCENT_SOFT)
        version_pill.grid(row=0, column=1, sticky="e")
        tk.Label(version_pill, text=APP_VERSION, bg=ACCENT_SOFT, fg=ACCENT,
                 font=(FONT, 8, "bold"), padx=8, pady=2).pack(side="left")
        tk.Label(footer, text=f"par {APP_AUTHOR}", bg=BG, fg=MUTED,
                 font=(FONT, 9)).grid(row=0, column=2, sticky="e", padx=(8, 0))

    def _sep(self, parent: tk.Frame) -> None:
        tk.Label(parent, text=":", bg=CARD, fg=MUTED,
                 font=(FONT, 18, "bold")).pack(side="left", padx=2, pady=(0, 16))

    def _section_label(self, parent: tk.Misc, text: str) -> tk.Frame:
        """Titre de section avec une puce violette pour l'harmonie visuelle."""
        box = tk.Frame(parent, bg=BG)
        tk.Label(box, text="●", bg=BG, fg=ACCENT,
                 font=(FONT, 7)).pack(side="left", padx=(0, 5), pady=(0, 2))
        ttk.Label(box, text=text, style="BoxLabel.TLabel").pack(side="left")
        return box

    def _update_preset_highlight(self) -> None:
        """Met en évidence la présélection correspondant au temps réglé."""
        try:
            h = int(self.hours.get() or 0)
            m = int(self.minutes.get() or 0)
            s = int(self.seconds.get() or 0)
        except ValueError:
            return
        total = h * 3600 + m * 60 + s
        for btn, (_, seconds) in zip(self.preset_buttons, PRESETS.items()):
            btn.config(style="ChipActive.TButton" if seconds == total
                       else "Chip.TButton")

    def _time_box(self, parent: tk.Frame, label: str, value: str, max_value: int = 59) -> ttk.Entry:
        f = tk.Frame(parent, bg=CARD)
        f.pack(side="left", padx=6)
        e = ttk.Entry(f, width=3, justify="center", style="Big.TEntry")
        e.insert(0, value)
        e.bind("<KeyRelease>", lambda _ev: self._preview_typed_time())
        # Sélectionne tout le contenu au focus : taper remplace directement la valeur.
        e.bind("<FocusIn>", lambda _ev, ent=e: ent.after(1, lambda: ent.select_range(0, "end")))
        e.bind("<Button-1>", lambda _ev, ent=e: ent.after(1, lambda: ent.select_range(0, "end")))
        # Molette de la souris pour ajuster rapidement la valeur.
        e.bind("<MouseWheel>", lambda ev, ent=e, mx=max_value: self._wheel_adjust(ent, ev, mx))
        e.bind("<Button-4>", lambda ev, ent=e, mx=max_value: self._wheel_adjust(ent, ev, mx, force_up=True))
        e.bind("<Button-5>", lambda ev, ent=e, mx=max_value: self._wheel_adjust(ent, ev, mx, force_down=True))
        e.pack()
        ttk.Label(f, text=label, style="CardBoxLabel.TLabel").pack(pady=(4, 0))
        return e

    def _wheel_adjust(self, entry: ttk.Entry, event, max_value: int,
                       force_up: bool = False, force_down: bool = False) -> None:
        if str(entry.cget("state")) == "disabled":
            return
        try:
            current = int(entry.get() or 0)
        except ValueError:
            current = 0
        up = force_up or (not force_down and getattr(event, "delta", 0) > 0)
        current = current + 1 if up else current - 1
        current = max(0, min(current, max_value))
        entry.delete(0, "end")
        entry.insert(0, str(current))
        self._preview_typed_time()
        self._save_prefs()

    # --- préférences ---

    def _apply_saved_time(self) -> None:
        for entry, key in ((self.hours, "hours"), (self.minutes, "minutes"), (self.seconds, "seconds")):
            entry.delete(0, "end")
            entry.insert(0, str(self.prefs.get(key, 0)))
        self._preview_typed_time()

    def _current_prefs(self) -> dict:
        try:
            h = int(self.hours.get() or 0)
            m = int(self.minutes.get() or 0)
            s = int(self.seconds.get() or 0)
        except ValueError:
            h, m, s = self.prefs.get("hours", 0), self.prefs.get("minutes", 10), self.prefs.get("seconds", 0)
        return {
            "hours": h, "minutes": m, "seconds": s,
            "action": self.action_var.get(),
            "always_on_top": self.always_on_top_var.get(),
            "mute": self.mute_var.get(),
            "confirm_delay": self.confirm_delay_var.get(),
        }

    def _save_prefs(self) -> None:
        self.prefs = self._current_prefs()
        settings.save(self.prefs)

    def _preview_typed_time(self) -> None:
        if self.countdown.running or self._paused:
            return
        try:
            h = int(self.hours.get() or 0)
            m = int(self.minutes.get() or 0)
            s = int(self.seconds.get() or 0)
        except ValueError:
            return
        total = max(h * 3600 + m * 60 + s, 0)
        self.countdown.reset(total)
        self._refresh_display()
        self._update_preset_highlight()

    def _on_toggle_always_on_top(self) -> None:
        self.root.attributes("-topmost", self.always_on_top_var.get())
        self._save_prefs()

    # --- contrôle du compte à rebours ---

    def _set_inputs_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for entry in (self.hours, self.minutes, self.seconds):
            entry.config(state=state)
        for btn in self.preset_buttons:
            btn.config(state=state)
        for rb in self.radio_buttons:
            rb.config(state=state)

    def _set_status(self, text: str, state: str = "idle") -> None:
        if not self.root.winfo_exists():
            return
        self.status_label.config(text=text)
        dot_color = {"idle": MUTED, "running": ACCENT, "paused": WARN,
                     "error": DANGER, "done": ACCENT}.get(state, MUTED)
        self.status_dot.config(fg=dot_color)

    def _read_inputs(self) -> int | None:
        try:
            h = int(self.hours.get() or 0)
            m = int(self.minutes.get() or 0)
            s = int(self.seconds.get() or 0)
        except ValueError:
            self._show_error("Heures, minutes et secondes doivent être des nombres.")
            return None
        if h < 0 or m < 0 or s < 0:
            self._show_error("Les valeurs ne peuvent pas être négatives.")
            return None
        total = h * 3600 + m * 60 + s
        if total <= 0:
            self._show_error("Le temps doit être supérieur à 0.")
            return None
        return total

    def _show_error(self, message: str) -> None:
        ThemedDialog(self.root, "Erreur", message, buttons=("OK",),
                     icon="!", icon_color=DANGER)

    def _set_time(self, seconds: int) -> None:
        h, rest = divmod(seconds, 3600)
        m, s = divmod(rest, 60)
        for entry, value in ((self.hours, h), (self.minutes, m), (self.seconds, s)):
            entry.config(state="normal")
            entry.delete(0, "end")
            entry.insert(0, str(value))
        if not self.countdown.running:
            self.countdown.reset(seconds)
            self._refresh_display()
            self._set_status(f"Aperçu : action dans {format_time(seconds)}.", "idle")
        self._update_preset_highlight()
        self._save_prefs()

    def _start(self) -> None:
        if self.countdown.running or self._finishing:
            return
        if not self._paused:
            total = self._read_inputs()
            if total is None:
                return
            self.countdown.reset(total)
            self._save_prefs()
        self._paused = False
        self._alerted = set()
        self.countdown.start()
        self._arm_tick(200)
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        self.extend1_btn.config(state="normal")
        self.extend5_btn.config(state="normal")
        self._set_inputs_enabled(False)
        self._last_tray_sec = -1
        self._refresh_display()
        self._update_tray("running")
        self._set_status(f"En cours — {self._action_label()} dans {format_time(self.countdown.remaining_left())}.", "running")

    def _extend(self, seconds: int) -> None:
        if not (self.countdown.running or self._paused):
            return
        self.countdown.extend(seconds)
        remaining_now = self.countdown.remaining_left() if self.countdown.running else self.countdown.remaining
        # Si on rallonge le temps au-delà d'un seuil déjà notifié, on le réarme
        # pour qu'il puisse à nouveau prévenir quand le compte y repassera.
        self._alerted = {t for t in self._alerted if remaining_now <= t}
        self._refresh_display()
        state = "running" if self.countdown.running else "paused"
        self._update_tray(state)
        minutes_added = seconds // 60
        self._set_status(f"+{minutes_added} min ajoutée(s). Fin dans {format_time(remaining_now)}.", state)

    def _pause(self) -> None:
        if not self.countdown.running:
            return
        self.countdown.pause()
        self._paused = True
        self.start_btn.config(text="▶  Reprendre", state="normal")
        self.pause_btn.config(state="disabled")
        self._refresh_display()
        self._update_tray("paused")
        self._set_status("En pause. Utilisez « Reprendre » pour continuer.", "paused")

    def _stop(self) -> None:
        self.countdown.reset()
        self._paused = False
        self.start_btn.config(text="▶  Démarrer", state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.extend1_btn.config(state="disabled")
        self.extend5_btn.config(state="disabled")
        self._set_inputs_enabled(True)
        self._refresh_display()
        self._update_tray("stopped")
        self._set_status("Arrêté. Réglez un nouveau temps si besoin.", "idle")

    def _action_label(self) -> str:
        return actions.ACTIONS[self.action_var.get()]

    # --- raccourcis clavier ---

    def _on_space_key(self, event) -> None:
        if isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Button, tk.Button,
                                     tk.Checkbutton, ttk.Checkbutton,
                                     tk.Radiobutton, ttk.Radiobutton)):
            return
        if self._finishing:
            return
        if self.countdown.running:
            self._pause()
        elif self.start_btn["state"] != "disabled":
            self._start()

    def _on_escape_key(self, event) -> None:
        if isinstance(event.widget, (tk.Entry, ttk.Entry)):
            return
        if self._finishing:
            self._cancel_execute()
        elif self.stop_btn["state"] != "disabled":
            self._stop()

    # --- affichage ---

    def _redraw_ring(self, _event=None) -> None:
        """Redessine l'anneau de temps restant à l'échelle du canvas,
        pour qu'il s'adapte à la taille de la fenêtre.

        Debounce : pendant un redimensionnement continu, le redessin n'est
        fait qu'une fois toutes les ~30 ms, ce qui garde le mouvement fluide.
        """
        if self._ring_pending:
            return
        self._ring_pending = True
        self.root.after(30, self._redraw_ring_now)

    def _redraw_ring_now(self) -> None:
        self._ring_pending = False
        cw = self.canvas.winfo_width()
        ch = self.canvas.winfo_height()
        if cw <= 1:
            cw = int(self.canvas.cget("width"))
        if ch <= 1:
            ch = int(self.canvas.cget("height"))
        self._ring_scale = min(max(min(cw, ch) / 200.0, 0.5), 2.0)
        s = self._ring_scale
        cx, cy = cw / 2, ch / 2
        self.canvas.delete("all")
        self._ring_halo = self.canvas.create_oval(
            cx - 90 * s, cy - 90 * s, cx + 90 * s, cy + 90 * s,
            outline=CARD_BORDER, width=max(1, s))
        self._ring_bg = self.canvas.create_oval(
            cx - 83 * s, cy - 83 * s, cx + 83 * s, cy + 83 * s,
            outline=CARD_BORDER, width=max(2, 12 * s))
        self._ring = self.canvas.create_arc(
            cx - 83 * s, cy - 83 * s, cx + 83 * s, cy + 83 * s,
            start=90, extent=0, style="arc", outline=ACCENT, width=max(2, 12 * s))
        self.time_label = self.canvas.create_text(
            cx, cy - 8 * s, text=format_time(self.countdown.total),
            font=(FONT, max(14, int(30 * s)), "bold"), fill=ACCENT)
        self.duration_label = self.canvas.create_text(
            cx, cy + 22 * s, text="", font=(FONT, max(7, int(9 * s))), fill=MUTED)
        # Halo lumineux doux derrière l'anneau (couleur selon l'état).
        self._glow_cx, self._glow_cy = cx, cy
        self._glow_scale = s
        self._glow_key = self._current_glow_key()
        self._paint_glow()

    def _current_glow_key(self) -> str | None:
        """Couleur du halo selon l'état du compte à rebours."""
        if self._glow_base:
            remaining = self.countdown.remaining_left()
            if self.countdown.running:
                return "danger" if remaining <= 10 else "accent"
            if self._paused:
                return "warn"
        return None

    def _paint_glow(self) -> None:
        """(Re)dessine le halo à la position de l'anneau (appelé à la demande)."""
        self.canvas.delete("glow")
        key = self._glow_key
        if not key or not self._glow_base:
            return
        r = max(30, int(105 * self._glow_scale) + 24)
        glow = self._glow_base[key].resize((r * 2, r * 2), _RESAMPLE)
        self._glow_photo = _to_photo(glow)
        self.canvas.create_image(self._glow_cx, self._glow_cy,
                                 image=self._glow_photo, tags="glow")
        self.canvas.tag_lower("glow")

    def _refresh_display(self, remaining: float | None = None) -> None:
        if remaining is None:
            remaining = self.countdown.remaining_left()
        total = max(self.countdown.total, 1)
        text = format_time(remaining)
        font_size = max(14, int((21 if len(text) > 5 else 30) * self._ring_scale))
        self.canvas.itemconfig(self.time_label, text=text, font=(FONT, font_size, "bold"))
        self.canvas.itemconfig(
            self.duration_label, font=(FONT, max(7, int(9 * self._ring_scale))))

        base_seconds = remaining
        finish_at = datetime.datetime.now() + datetime.timedelta(seconds=max(base_seconds, 0))
        self.canvas.itemconfig(self.duration_label, text=f"fin prévue à {finish_at.strftime('%H:%M')}")

        self.canvas.itemconfig(
            self._ring, extent=-int(360 * max(remaining, 0) / total)
        )
        if remaining > 60:
            color = ACCENT
        elif remaining > 10:
            color = WARN
        elif self.countdown.running and self._blink_off:
            color = DANGER_DIM  # clignotement des 10 dernières secondes
        else:
            color = DANGER
        self.canvas.itemconfig(self.time_label, fill=color)
        self.canvas.itemconfig(self._ring, outline=color)
        # Si l'état change (démarrage, pause, alerte), le halo suit immédiatement.
        key = self._current_glow_key()
        if key != self._glow_key:
            self._glow_key = key
            self._paint_glow()

        # Le titre de la fenêtre affiche le temps restant (utile quand la
        # fenêtre est réduite dans la barre des tâches de Windows).
        title = f"{APP_NAME} — {text}"
        if self._paused:
            title = f"{APP_NAME} — En pause"
        elif not self.countdown.running:
            title = f"{APP_NAME} — Compte à rebours PC"
        if self.root.title() != title:
            self.root.title(title)

    def _arm_tick(self, delay: int) -> None:
        """Planifie le prochain _tick en évitant les doublons."""
        if self._tick_id is not None:
            self.root.after_cancel(self._tick_id)
        self._tick_id = self.root.after(delay, self._tick)

    def _tick(self) -> None:
        self._tick_id = None
        if self.countdown.running:
            remaining = self.countdown.remaining_left()
            self._refresh_display(remaining)
            self._check_alerts(remaining)
            if remaining <= 10:
                self._blink_counter += 1
                if self._blink_counter >= 3:
                    self._blink_counter = 0
                    self._blink_off = not self._blink_off
            else:
                self._blink_counter = 0
                self._blink_off = False
            if int(remaining) != self._last_tray_sec or remaining <= 10:
                self._last_tray_sec = int(remaining)
                self._update_tray("running")
            if self.countdown.is_finished() and not self._finishing:
                self._finish()
            self._update_mini()
            # Pendant le compte à rebours : rafraîchissement rapide.
            self._arm_tick(200)
        elif self._paused:
            self._update_mini()
            # En pause : rafraîchissement lent (économie de CPU).
            self._arm_tick(500)
        # Au repos : la boucle s'arrête, consommation quasi nulle.
        # _start() relancera le cycle.

    def _check_alerts(self, remaining: float) -> None:
        for threshold, label in ((300, "5 minutes"), (60, "1 minute")):
            if (remaining <= threshold and threshold not in self._alerted
                    and self.countdown.total > threshold):
                self._alerted.add(threshold)
                self.tray.notify(f"Encore {label} avant : {self._action_label()}.")

    # --- fin du compte à rebours ---

    def _finish(self) -> None:
        self._finishing = True
        self._last_tray_sec = -1
        self._blink_off = False
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.extend1_btn.config(state="disabled")
        self.extend5_btn.config(state="disabled")
        self._update_tray("running")
        if not self.mute_var.get():
            try:
                import winsound
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
            except Exception:
                pass
        self.show_window()
        delay_ms = max(int(self.confirm_delay_var.get()), 1) * 1000
        self._execute_after_id = self.root.after(delay_ms, self._do_execute)
        self._show_overlay()

    def _show_overlay(self) -> None:
        overlay = tk.Toplevel(self.root)
        overlay.title(APP_NAME)
        overlay.configure(bg=BG)
        overlay.resizable(False, False)
        overlay.transient(self.root)
        overlay.attributes("-topmost", True)
        self._overlay = overlay
        card = RoundedCard(overlay, radius=16, page_bg=BG)
        card.pack(padx=18, pady=18)
        tk.Label(card.body, text="Compte à rebours terminé", bg=CARD, fg=TEXT,
                 font=(FONT, 14, "bold")).pack(padx=24, pady=(18, 3))
        tk.Label(card.body, text=f"Action : {self._action_label()}",
                 bg=CARD, fg=ACCENT, font=(FONT, 11, "bold")).pack(padx=24, pady=(0, 4))
        countdown_label = tk.Label(card.body, bg=CARD, fg=MUTED, font=(FONT, 10))
        countdown_label.pack(padx=24, pady=(0, 12))
        self._overlay_label = countdown_label
        self._overlay_deadline = time.monotonic() + max(int(self.confirm_delay_var.get()), 1)
        self._overlay_tick()
        btns = tk.Frame(card.body, bg=CARD)
        btns.pack(pady=(0, 18))
        ttk.Button(btns, text="Exécuter maintenant", style="Accent.TButton",
                   command=self._execute_now).pack(side="left", padx=6)
        ttk.Button(btns, text="Annuler", command=self._cancel_execute).pack(side="left", padx=6)
        overlay.protocol("WM_DELETE_WINDOW", self._cancel_execute)
        overlay.bind("<Return>", lambda _e: self._execute_now())
        overlay.bind("<Escape>", lambda _e: self._cancel_execute())
        # Centrage au-dessus de la fenêtre principale.
        overlay.update_idletasks()
        w = overlay.winfo_reqwidth()
        h = overlay.winfo_reqheight()
        x = self.root.winfo_rootx() + (self.root.winfo_width() - w) // 2
        y = self.root.winfo_rooty() + (self.root.winfo_height() - h) // 2
        overlay.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        overlay.grab_set()
        overlay.focus_force()

    def _overlay_tick(self) -> None:
        """Met à jour le compte à rebours affiché sur la fenêtre de fin."""
        if self._overlay is None or not self._overlay.winfo_exists():
            return
        left = max(self._overlay_deadline - time.monotonic(), 0)
        secs = int(math.ceil(left))
        self._overlay_label.config(
            text=f"L'exécution se lance dans {secs} seconde{'s' if secs != 1 else ''}…"
        )
        self._overlay.after(200, self._overlay_tick)

    def _execute_now(self) -> None:
        if self._execute_after_id is not None:
            self.root.after_cancel(self._execute_after_id)
            self._execute_after_id = None
        self._do_execute()

    def _cancel_execute(self) -> None:
        if self._execute_after_id is not None:
            self.root.after_cancel(self._execute_after_id)
            self._execute_after_id = None
        self._close_overlay()
        self._finishing = False
        self._paused = False
        self.countdown.reset(self.countdown.total)
        self.start_btn.config(text="▶  Démarrer", state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.extend1_btn.config(state="disabled")
        self.extend5_btn.config(state="disabled")
        self._set_inputs_enabled(True)
        self._refresh_display()
        self._update_tray("stopped")
        self._set_status("Action annulée. Le compte à rebours repartira de zéro.", "idle")

    def _close_overlay(self) -> None:
        if self._overlay is not None and self._overlay.winfo_exists():
            self._overlay.destroy()
        self._overlay = None
        self._overlay_label = None

    def _do_execute(self) -> None:
        if not self._finishing:
            return
        self._execute_after_id = None
        self._close_overlay()
        try:
            actions.execute(self.action_var.get())
        except Exception as exc:
            self._set_status(f"Erreur lors de l'action : {exc}", "error")
        self._finishing = False
        self._paused = False
        self.countdown.reset(0)
        self.start_btn.config(text="▶  Démarrer", state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.extend1_btn.config(state="disabled")
        self.extend5_btn.config(state="disabled")
        self._set_inputs_enabled(True)
        self._refresh_display()
        self._update_tray("stopped")
        self._set_status(f"Terminé : {self._action_label()} exécutée. Réglez un nouveau temps si besoin.", "done")

    # --- mode mini ---

    def _build_mini(self) -> None:
        """Petite fenêtre sans bordure : anneau + temps restant, déplaçable."""
        mini = tk.Toplevel(self.root)
        mini.overrideredirect(True)
        mini.configure(bg=BG)
        mini.attributes("-topmost", True)
        self._mini = mini
        card = tk.Frame(mini, bg=CARD, highlightbackground=CARD_BORDER,
                        highlightthickness=1)
        card.pack(padx=2, pady=2)
        top = tk.Frame(card, bg=CARD)
        top.pack(fill="x", padx=4, pady=(4, 0))
        tk.Label(top, text=APP_NAME, bg=CARD, fg=MUTED,
                 font=(FONT, 7, "bold")).pack(side="left")
        if self._icon_restore is not None:
            restore_btn = tk.Button(top, image=self._icon_restore,
                                    command=self._restore_from_mini, bg=CARD,
                                    activebackground=ACCENT_SOFT, relief="flat",
                                    bd=0, cursor="hand2")
        else:
            restore_btn = tk.Button(top, text="↗", command=self._restore_from_mini,
                                    bg=CARD, fg=ACCENT, activebackground=ACCENT_SOFT,
                                    activeforeground=ACCENT, relief="flat", bd=0,
                                    font=(FONT, 10, "bold"), padx=4, cursor="hand2")
        restore_btn.pack(side="right")
        Tooltip(restore_btn, "Revenir à la fenêtre complète (Échap)")

        canvas = tk.Canvas(card, width=130, height=130, bg=CARD, highlightthickness=0)
        canvas.pack(padx=6, pady=(2, 6))
        s = 0.65
        cx = cy = 65
        canvas.create_oval(cx - 90 * s, cy - 90 * s, cx + 90 * s, cy + 90 * s,
                           outline=CARD_BORDER, width=max(1, s))
        canvas.create_oval(cx - 83 * s, cy - 83 * s, cx + 83 * s, cy + 83 * s,
                           outline=CARD_BORDER, width=max(2, 12 * s))
        self._mini_ring = canvas.create_arc(
            cx - 83 * s, cy - 83 * s, cx + 83 * s, cy + 83 * s,
            start=90, extent=0, style="arc", outline=ACCENT, width=max(2, 12 * s))
        self._mini_time = canvas.create_text(
            cx, cy - 8 * s, text=format_time(self.countdown.total),
            font=(FONT, max(14, int(30 * s)), "bold"), fill=ACCENT)
        self._mini_dur = canvas.create_text(
            cx, cy + 22 * s, text="", font=(FONT, max(7, int(9 * s))), fill=MUTED)
        self._mini_canvas = canvas

        # Position initiale : centre de l'écran.
        mini.update_idletasks()
        w = mini.winfo_reqwidth()
        h = mini.winfo_reqheight()
        x = max((mini.winfo_screenwidth() - w) // 2, 0)
        y = max((mini.winfo_screenheight() - h) // 3, 0)
        mini.geometry(f"+{x}+{y}")

        # Déplacement par glisser-déposer (toute la surface sauf le bouton).
        for widget in (mini, card, top, canvas):
            widget.bind("<Button-1>", self._mini_drag_start)
            widget.bind("<B1-Motion>", self._mini_drag_move)
        mini.bind("<Escape>", lambda _e: self._restore_from_mini())

    def _enter_mini(self) -> None:
        """Passe en mode mini : seule la petite fenêtre reste visible."""
        if self._mini is None:
            self._build_mini()
        self._mini_mode = True
        self._mini.deiconify()
        self._mini.lift()
        self._mini.focus_force()
        self._update_mini()
        self.root.withdraw()

    def _restore_from_mini(self) -> None:
        """Restaure la fenêtre complète (bouton ↗, Échap ou icône tray)."""
        self._mini_mode = False
        if self._mini is not None and self._mini.winfo_exists():
            self._mini.withdraw()
        self.show_window()

    def _mini_drag_start(self, event) -> None:
        self._mini_drag_dx = event.x_root - self._mini.winfo_x()
        self._mini_drag_dy = event.y_root - self._mini.winfo_y()

    def _mini_drag_move(self, event) -> None:
        self._mini.geometry(
            f"+{event.x_root - self._mini_drag_dx}+{event.y_root - self._mini_drag_dy}"
        )

    def _update_mini(self) -> None:
        """Met à jour l'affichage du mini anneau (temps, arc, couleur)."""
        if self._mini is None or not self._mini_mode:
            return
        if self._paused:
            remaining = self.countdown.remaining
            duration = "En pause"
        else:
            remaining = self.countdown.remaining_left()
            finish_at = datetime.datetime.now() + datetime.timedelta(
                seconds=max(remaining, 0))
            duration = (""
                        if not self.countdown.running
                        else f"fin {finish_at.strftime('%H:%M')}")
        total = max(self.countdown.total, 1)
        if remaining > 60:
            color = ACCENT
        elif remaining > 10:
            color = WARN
        else:
            color = DANGER
        self._mini_canvas.itemconfig(self._mini_time, text=format_time(remaining),
                                     fill=color)
        self._mini_canvas.itemconfig(
            self._mini_ring, extent=-int(360 * max(remaining, 0) / total),
            outline=color)
        self._mini_canvas.itemconfig(self._mini_dur, text=duration)

    # --- barre des tâches ---

    def _update_tray(self, state: str) -> None:
        self._tray_state = state
        if state == "running":
            remaining = self.countdown.remaining_left()
            minutes = int(remaining // 60)
            tooltip = (f"{self._action_label()} dans {format_time(remaining)}")
        elif state == "paused":
            minutes = int(self.countdown.remaining // 60)
            tooltip = f"En pause — il reste {format_time(self.countdown.remaining)}"
        else:
            minutes = 0
            tooltip = f"{APP_NAME} — prêt, réglez un temps"
        self.tray.refresh(state, tooltip, minutes, self._blink_off)

    def show_window(self) -> None:
        if self._mini_mode:
            self._mini_mode = False
            if self._mini is not None:
                self._mini.withdraw()
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _minimize_to_tray(self) -> None:
        if self.tray.available:
            self.tray.notify(f"{APP_NAME} reste actif ici. Cliquez sur l'icône pour rouvrir.")
            self.root.withdraw()
        else:
            self.root.iconify()

    def toggle_from_tray(self) -> None:
        if self._finishing:
            self.show_window()
        elif self.countdown.running:
            self._pause()
        elif self.countdown.remaining > 0:
            self.show_window()
            self._start()
        else:
            self.show_window()

    def stop_from_tray(self) -> None:
        if self._finishing:
            self._cancel_execute()
        else:
            self._stop()
            self.tray.notify("Compte à rebours arrêté.")

    def quit_from_tray(self) -> None:
        running = self.countdown.running or self._finishing or self._paused
        if running:
            dialog = ThemedDialog(self.root, "Quitter Extinia ?",
                                  "Un compte à rebours est en cours. Vraiment quitter ?",
                                  buttons=("Oui", "Non"), default=1, icon="?")
            if not dialog.confirmed():
                return
        self._quit_app()

    def _quit_app(self) -> None:
        """Ferme tout : enregistre les préférences, retire l'icône de la
        barre des tâches puis ferme la fenêtre."""
        if self._execute_after_id is not None:
            self.root.after_cancel(self._execute_after_id)
            self._execute_after_id = None
        self._close_overlay()
        if self._mini is not None:
            try:
                self._mini.destroy()
            except Exception:
                pass
        self._mini = None
        self._save_prefs()
        self.tray.stop()
        self.root.destroy()

    def _on_close(self) -> None:
        if self._finishing:
            self._cancel_execute()
            return
        message = f"Voulez-vous vraiment fermer {APP_NAME} ?"
        if self.countdown.running or self._paused:
            message += "\nUn compte à rebours est en cours et sera arrêté."
        dialog = ThemedDialog(self.root, f"Fermer {APP_NAME} ?", message,
                              buttons=("Oui", "Non"), default=1, icon="?")
        if dialog.confirmed():
            self._quit_app()

    def run(self) -> None:
        self.tray.start()
        if not self.tray.available:
            self._set_status("Barre des tâches indisponible (pystray absent) : la croix ferme l'application.", "idle")
        self.root.mainloop()
