"""Interface graphique tkinter d'Extinia (compte à rebours PC)."""

import base64
import datetime
import io
import math
import tkinter as tk
from tkinter import messagebox, ttk

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
    FIELD,
    FONT,
    MUTED,
    SHADOW,
    TEXT,
    WARN,
)
from countdown import Countdown
from tray import Tray, logo_image

PRESETS = {"1 min": 60, "5 min": 300, "10 min": 600, "30 min": 1800, "1 h": 3600}

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


class RoundedCard(tk.Frame):
    """Carte à coins arrondis avec une légère ombre portée pour donner de la profondeur."""

    def __init__(self, parent, radius: int = 16, bg_color: str = CARD,
                 border: str = CARD_BORDER, page_bg: str = BG, shadow: bool = True,
                 **kwargs) -> None:
        super().__init__(parent, bg=page_bg, **kwargs)
        self.radius = radius
        self.bg_color = bg_color
        self.border = border
        self.shadow = shadow
        self.canvas = tk.Canvas(self, bg=page_bg, highlightthickness=0)
        self.canvas.pack()
        self.body = tk.Frame(self.canvas, bg=bg_color)
        self.canvas.create_window(2, 2, window=self.body, anchor="nw")
        self.body.bind("<Configure>", self._sync)

    def _sync(self, _event=None) -> None:
        w = self.body.winfo_reqwidth() + 4
        h = self.body.winfo_reqheight() + 4
        extra = 4 if self.shadow else 0
        self.canvas.config(width=w + extra, height=h + extra)
        self.canvas.delete("bg")
        if self.shadow:
            self._round_rect(1 + 3, 1 + 4, w - 1 + 3, h - 1 + 4, self.radius,
                              fill=SHADOW, outline="", tags="bg")
        self._round_rect(1, 1, w - 1, h - 1, self.radius,
                          fill=self.bg_color, outline=self.border, width=1, tags="bg")
        self.canvas.tag_lower("bg")

    def _round_rect(self, x1, y1, x2, y2, r, **kwargs):
        points = [
            x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
            x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
            x1, y2, x1, y2 - r, x1, y1 + r, x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, **kwargs)


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


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} — Compte à rebours PC")
        self.root.resizable(False, False)
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
        self._last_tray_sec = -1
        self._tray_state = "stopped"
        self._finishing = False
        self._paused = False
        self._blink_off = False
        self._blink_counter = 0
        self._alerted = set()

        self._setup_styles()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<space>", self._on_space_key)
        self.root.bind("<Escape>", self._on_escape_key)
        self.root.attributes("-topmost", self.always_on_top_var.get())

        self._apply_saved_time()
        self._set_status("Prêt. Réglez le temps, choisissez une action, cliquez sur Démarrer.", "idle")
        self.canvas.itemconfig(self.time_label, fill=ACCENT)
        self._tick()

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
            style.configure("Icon.TButton", background=BG, bordercolor=BG,
                            padding=(6, 4), font=(FONT, 11), relief="flat")
            style.map("Icon.TButton", background=[("active", CARD), ("pressed", CARD)],
                      bordercolor=[("active", CARD_BORDER)])

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
        outer = tk.Frame(self.root, bg=BG)
        outer.grid(row=0, column=0, sticky="nsew")
        outer.columnconfigure(0, weight=1)
        outer.columnconfigure(1, weight=1)

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

        reduce_btn = ttk.Button(header, text="🗕", style="Icon.TButton", width=3,
                                command=self._minimize_to_tray)
        reduce_btn.pack(side="right", padx=(4, 0))
        Tooltip(reduce_btn, "Réduire dans la barre des tâches")

        divider = tk.Frame(outer, bg=CARD_BORDER, height=1)
        divider.grid(row=1, column=0, columnspan=2, sticky="ew", padx=20, pady=(2, 10))

        # --- carte : temps avant action (colonne gauche) ---
        ttk.Label(outer, text="DURÉE", style="BoxLabel.TLabel").grid(
            row=2, column=0, sticky="w", padx=20, pady=(0, 4))

        card_time = RoundedCard(outer, radius=16)
        card_time.grid(row=3, column=0, sticky="nw", padx=(20, 10), pady=(0, 12))

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
        ttk.Label(outer, text="ACTION FINALE", style="BoxLabel.TLabel").grid(
            row=2, column=1, sticky="w", padx=(10, 20), pady=(0, 4))

        card_action = RoundedCard(outer, radius=16)
        card_action.grid(row=3, column=1, sticky="nw", padx=(10, 20), pady=(0, 12))

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
        ring.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(10, 0))
        ttk.Label(ring, text="TEMPS RESTANT", style="BoxLabel.TLabel").pack(pady=(2, 0))
        self.canvas = tk.Canvas(ring, width=200, height=200, bg=BG, highlightthickness=0)
        self.canvas.pack(pady=(4, 0))
        self._ring_halo = self.canvas.create_oval(10, 10, 190, 190, outline=CARD_BORDER, width=1)
        self._ring_bg = self.canvas.create_oval(17, 17, 183, 183, outline=CARD_BORDER, width=12)
        self._ring = self.canvas.create_arc(17, 17, 183, 183, start=90, extent=0,
                                            style="arc", outline=ACCENT, width=12)
        self.time_label = self.canvas.create_text(
            100, 92, text=format_time(self.countdown.total),
            font=(FONT, 30, "bold"), fill=ACCENT,
        )
        self.duration_label = self.canvas.create_text(
            100, 122, text="", font=(FONT, 9), fill=MUTED,
        )

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
            messagebox.showerror("Erreur", "Heures, minutes et secondes doivent être des nombres.")
            return None
        if h < 0 or m < 0 or s < 0:
            messagebox.showerror("Erreur", "Les valeurs ne peuvent pas être négatives.")
            return None
        total = h * 3600 + m * 60 + s
        if total <= 0:
            messagebox.showerror("Erreur", "Le temps doit être supérieur à 0.")
            return None
        return total

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
        if isinstance(event.widget, (tk.Entry, ttk.Entry, ttk.Button, tk.Button)):
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

    def _refresh_display(self, remaining: float | None = None) -> None:
        if remaining is None:
            remaining = self.countdown.remaining_left()
        total = max(self.countdown.total, 1)
        text = format_time(remaining)
        font_size = 21 if len(text) > 5 else 30
        self.canvas.itemconfig(self.time_label, text=text, font=(FONT, font_size, "bold"))

        base_seconds = remaining if self.countdown.running else self.countdown.total
        finish_at = datetime.datetime.now() + datetime.timedelta(seconds=max(base_seconds, 0))
        self.canvas.itemconfig(self.duration_label, text=f"fin prévue à {finish_at.strftime('%H:%M')}")

        self.canvas.itemconfig(
            self._ring, extent=-int(360 * max(remaining, 0) / total)
        )
        if remaining > 60:
            color = ACCENT
        elif remaining > 10:
            color = WARN
        else:
            color = DANGER
        self.canvas.itemconfig(self.time_label, fill=color)
        self.canvas.itemconfig(self._ring, outline=color)

    def _tick(self) -> None:
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
        self.root.after(200, self._tick)

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
        self._overlay = overlay
        card = RoundedCard(overlay, radius=16, page_bg=BG)
        card.pack(padx=18, pady=18)
        tk.Label(card.body, text="Compte à rebours terminé", bg=CARD, fg=TEXT,
                 font=(FONT, 14, "bold")).pack(padx=24, pady=(18, 3))
        tk.Label(card.body, text=f"Action : {self._action_label()}",
                 bg=CARD, fg=ACCENT, font=(FONT, 11, "bold")).pack(padx=24, pady=(0, 4))
        tk.Label(card.body, text=f"L'exécution se lance dans {self.confirm_delay_var.get()} secondes…",
                 bg=CARD, fg=MUTED, font=(FONT, 10)).pack(padx=24, pady=(0, 12))
        btns = tk.Frame(card.body, bg=CARD)
        btns.pack(pady=(0, 18))
        ttk.Button(btns, text="Exécuter maintenant", style="Accent.TButton",
                   command=self._execute_now).pack(side="left", padx=6)
        ttk.Button(btns, text="Annuler", command=self._cancel_execute).pack(side="left", padx=6)
        overlay.protocol("WM_DELETE_WINDOW", self._cancel_execute)

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
        running = self.countdown.running or self._finishing
        if running and not messagebox.askyesno(
            "Quitter ?", "Un compte à rebours est en cours. Vraiment quitter ?"
        ):
            return
        if self._execute_after_id is not None:
            self.root.after_cancel(self._execute_after_id)
        self._save_prefs()
        self.tray.stop()
        self.root.destroy()

    def _on_close(self) -> None:
        if self._finishing:
            self._cancel_execute()
            return
        self._save_prefs()
        if self.tray.available:
            self.tray.notify(
                f"{APP_NAME} reste actif ici. Cliquez sur l'icône pour rouvrir."
            )
            self.root.withdraw()
        else:
            if (self.countdown.running or self.countdown.remaining_left() < self.countdown.total) \
                    and not messagebox.askyesno(
                        "Fermer ?", "Un compte à rebours est en cours. Vraiment quitter ?"
                    ):
                return
            self.root.destroy()

    def run(self) -> None:
        self.tray.start()
        if not self.tray.available:
            self._set_status("Barre des tâches indisponible (pystray absent) : la croix ferme l'application.", "idle")
        self.root.mainloop()
