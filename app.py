"""Interface graphique tkinter du compte à rebours PC."""

import math
import tkinter as tk
from tkinter import messagebox, ttk

import actions
from countdown import Countdown

PRESETS = {"1 min": 60, "5 min": 300, "10 min": 600, "30 min": 1800, "1 h": 3600}

# Palette du thème sombre
BG = "#14151a"
CARD = "#1f2128"
FIELD = "#2a2d35"
BORDER = "#33363f"
TEXT = "#e8eaf0"
MUTED = "#9aa0b0"
ACCENT = "#5b8cff"
ACCENT_DOWN = "#4a7ae0"
NORMA = "#67c23a"
WARN = "#e6a23c"
DANGER = "#f56c6c"


def format_time(seconds: float) -> str:
    total = int(math.ceil(max(seconds, 0)))
    h, rest = divmod(total, 3600)
    m, s = divmod(rest, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


class App:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title("Compte à rebours PC")
        self.root.resizable(False, False)
        self.root.configure(bg=BG)

        self.countdown = Countdown(600)
        self.action_var = tk.StringVar(value="shutdown")
        self._setup_styles()
        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self._set_status("Prêt. Réglez le temps et choisissez une action.")
        self._tick()

    # --- thème ---

    def _setup_styles(self) -> None:
        """Applique le thème sombre. En cas de souci, on garde le thème par défaut."""
        try:
            style = ttk.Style(self.root)
            style.theme_use("clam")
            style.configure(".", background=BG, foreground=TEXT, bordercolor=BORDER)

            style.configure("TFrame", background=BG)
            style.configure("TLabel", background=BG, foreground=TEXT)
            style.configure("Muted.TLabel", background=BG, foreground=MUTED)

            style.configure(
                "Card.TLabelframe",
                background=CARD,
                bordercolor=BORDER,
                borderwidth=1,
                relief="solid",
            )
            style.configure(
                "Card.TLabelframe.Label",
                background=CARD,
                foreground=MUTED,
                font=("Segoe UI", 9, "bold"),
            )

            style.configure(
                "TEntry",
                fieldbackground=FIELD,
                foreground=TEXT,
                insertcolor=TEXT,
                bordercolor=BORDER,
                padding=4,
                font=("Segoe UI", 11),
            )

            style.configure(
                "TButton",
                background=CARD,
                foreground=TEXT,
                bordercolor=BORDER,
                padding=(14, 6),
                font=("Segoe UI", 10, "bold"),
                relief="flat",
            )
            style.map(
                "TButton",
                background=[("active", "#2f323a"), ("pressed", "#393d47")],
                bordercolor=[("active", ACCENT)],
            )
            style.configure(
                "Accent.TButton",
                background=ACCENT,
                foreground="#ffffff",
                borderwidth=0,
            )
            style.map(
                "Accent.TButton",
                background=[("active", ACCENT_DOWN), ("pressed", ACCENT_DOWN)],
            )

            style.configure(
                "TRadiobutton",
                background=CARD,
                foreground=TEXT,
                indicatorbackground=FIELD,
                borderwidth=0,
                font=("Segoe UI", 10),
            )
            style.map(
                "TRadiobutton",
                indicatorbackground=[("selected", ACCENT), ("active", "#3a3e49")],
                foreground=[("disabled", MUTED)],
            )

            style.configure(
                "TProgressbar",
                background=ACCENT,
                troughcolor=FIELD,
                bordercolor=BG,
                borderwidth=0,
                thickness=10,
            )
        except Exception:
            pass

    # --- interface ---

    def _build_ui(self) -> None:
        pad = {"padx": 16, "pady": 8}

        header = tk.Frame(self.root, bg=BG)
        header.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        tk.Label(
            header, text="Compte à rebours PC", bg=BG, fg=TEXT,
            font=("Segoe UI", 16, "bold"),
        ).pack(side="left")
        tk.Label(
            header, text="Action automatique programmée", bg=BG, fg=MUTED,
            font=("Segoe UI", 9),
        ).pack(side="right", pady=(6, 0))

        frame_time = ttk.LabelFrame(self.root, text=" TEMPS AVANT ACTION ", style="Card.TLabelframe")
        frame_time.grid(row=1, column=0, sticky="ew", **pad)
        frame_time.columnconfigure(0, weight=1)

        row = ttk.Frame(frame_time)
        row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 6))
        self.hours = ttk.Entry(row, width=4, justify="center")
        self.minutes = ttk.Entry(row, width=4, justify="center")
        self.seconds = ttk.Entry(row, width=4, justify="center")
        self.hours.insert(0, "0")
        self.minutes.insert(0, "10")
        self.seconds.insert(0, "0")
        for label in ("heures", "minutes", "secondes"):
            ttk.Label(row, text=label, style="Muted.TLabel").pack(side="left", padx=(10, 0))
        self.hours.pack(side="left")
        self.minutes.pack(side="left")
        self.seconds.pack(side="left")

        presets = ttk.Frame(frame_time)
        presets.grid(row=1, column=0, sticky="ew", padx=10, pady=(4, 10))
        ttk.Label(presets, text="Rapide :", style="Muted.TLabel").pack(side="left")
        self.preset_buttons = []
        for name, seconds in PRESETS.items():
            btn = ttk.Button(
                presets, text=name, width=7,
                command=lambda s=seconds: self._set_time(s),
            )
            btn.pack(side="left", padx=4)
            self.preset_buttons.append(btn)

        frame_action = ttk.LabelFrame(
            self.root, text=" ACTION À LA FIN DU COMPTE À REBOURS ", style="Card.TLabelframe"
        )
        frame_action.grid(row=2, column=0, sticky="ew", **pad)
        self.radio_buttons = []
        for key, label in actions.ACTIONS.items():
            rb = ttk.Radiobutton(
                frame_action, text=label, value=key, variable=self.action_var
            )
            rb.pack(anchor="w", padx=12, pady=2)
            self.radio_buttons.append(rb)
        ttk.Label(
            frame_action, text="Le compte à rebours étant terminé, l'action est lancée après 3 secondes.",
            style="Muted.TLabel",
        ).pack(anchor="w", padx=12, pady=(8, 8))

        frame_status = ttk.Frame(self.root)
        frame_status.grid(row=3, column=0, sticky="ew", **pad)
        frame_status.columnconfigure(0, weight=1)
        self.time_label = tk.Label(
            frame_status, text=format_time(self.countdown.total),
            bg=BG, fg=ACCENT,
            font=("Segoe UI", 44, "bold"),
        )
        self.time_label.grid(row=0, column=0, pady=(0, 6))
        self.progress = ttk.Progressbar(
            frame_status, length=380, maximum=max(self.countdown.total, 1),
            value=max(self.countdown.total, 0),
        )
        self.progress.grid(row=1, column=0, sticky="ew")

        frame_buttons = ttk.Frame(self.root)
        frame_buttons.grid(row=4, column=0, pady=(14, 4))
        self.start_btn = ttk.Button(frame_buttons, text="Démarrer", command=self._start, style="Accent.TButton")
        self.pause_btn = ttk.Button(frame_buttons, text="Pause", command=self._pause, state="disabled")
        self.stop_btn = ttk.Button(frame_buttons, text="Arrêter", command=self._stop, state="disabled")
        self.start_btn.pack(side="left", padx=5)
        self.pause_btn.pack(side="left", padx=5)
        self.stop_btn.pack(side="left", padx=5)

        self.status_label = ttk.Label(self.root, text="", style="Muted.TLabel")
        self.status_label.grid(row=5, column=0, pady=(0, 12))

    # --- contrôles ---

    def _set_inputs_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"
        for entry in (self.hours, self.minutes, self.seconds):
            entry.config(state=state)
        for btn in self.preset_buttons:
            btn.config(state=state)
        for rb in self.radio_buttons:
            rb.config(state=state)

    def _set_status(self, text: str) -> None:
        self.status_label.config(text=text)

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
        self.hours.delete(0, "end")
        self.minutes.delete(0, "end")
        self.seconds.delete(0, "end")
        self.hours.insert(0, str(h))
        self.minutes.insert(0, str(m))
        self.seconds.insert(0, str(s))
        if not self.countdown.running:
            self.countdown.reset(seconds)
            self._refresh_display()
            self._set_status(f"Aperçu : action dans {format_time(seconds)}.")

    def _start(self) -> None:
        if self.countdown.running:
            return
        if self.countdown.remaining <= 0:
            total = self._read_inputs()
            if total is None:
                return
            self.countdown.reset(total)
        self.countdown.start()
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="normal")
        self.stop_btn.config(state="normal")
        self._set_inputs_enabled(False)
        action_label = actions.ACTIONS[self.action_var.get()]
        self._set_status(f"En cours — {action_label} dans {format_time(self.countdown.remaining_left())}.")

    def _pause(self) -> None:
        if not self.countdown.running:
            return
        self.countdown.pause()
        self.start_btn.config(text="Reprendre", state="normal")
        self.pause_btn.config(state="disabled")
        self._refresh_display()
        self._set_status("En pause. Utilisez « Reprendre » pour continuer.")

    def _stop(self) -> None:
        self.countdown.reset()
        self.start_btn.config(text="Démarrer", state="normal")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self._set_inputs_enabled(True)
        self._refresh_display()
        self._set_status("Arrêté. Réglez un nouveau temps si besoin.")

    # --- affichage ---

    def _refresh_display(self, remaining: float | None = None) -> None:
        if remaining is None:
            remaining = self.countdown.remaining_left()
        self.time_label.config(text=format_time(remaining))
        self.progress.config(
            maximum=max(self.countdown.total, 1), value=max(remaining, 0)
        )
        if remaining > 60:
            self.time_label.config(fg=ACCENT)
        elif remaining > 10:
            self.time_label.config(fg=WARN)
        else:
            self.time_label.config(fg=DANGER)

    def _tick(self) -> None:
        if self.countdown.running:
            remaining = self.countdown.remaining_left()
            self._refresh_display(remaining)
            if self.countdown.is_finished():
                self._finish()
        self.root.after(200, self._tick)

    def _finish(self) -> None:
        action_label = actions.ACTIONS[self.action_var.get()]
        self.countdown.reset(0)
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self._set_inputs_enabled(True)
        self.time_label.config(text=format_time(0), fg=DANGER)
        self.progress.config(value=0)
        self.root.update()
        self._set_status("Terminé — l'action a été déclenchée.")
        messagebox.showinfo(
            "Compte à rebours terminé",
            f"Le temps est écoulé. Action : {action_label}.\n"
            "Le système va exécuter l'action dans 3 secondes "
            "(fermez la fenêtre pour annuler).",
        )
        self.root.after(3000, lambda: actions.execute(self.action_var.get()))

    def _on_close(self) -> None:
        if self.countdown.running:
            if not messagebox.askyesno(
                "Fermer ?",
                "Un compte à rebours est en cours. Vraiment quitter ?",
            ):
                return
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()