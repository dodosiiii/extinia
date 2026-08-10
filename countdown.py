"""Logique du compte à rebours, basée sur le temps réel (indépendant des ticks UI)."""

import time


class Countdown:
    """Compte à rebours démarré / mis en pause / réinitialisé à la demande."""

    def __init__(self, total_seconds: float) -> None:
        self.total = max(float(total_seconds), 0.0)
        self.remaining = self.total
        self.running = False
        self.end_time: float | None = None

    def start(self) -> None:
        self.running = True
        self.end_time = time.monotonic() + max(self.remaining, 0.0)

    def pause(self) -> None:
        if self.running:
            self.remaining = self.remaining_left()
        self.running = False
        self.end_time = None

    def reset(self, total_seconds: float | None = None) -> None:
        if total_seconds is not None:
            self.total = max(float(total_seconds), 0.0)
        self.remaining = self.total
        self.running = False
        self.end_time = None

    def remaining_left(self) -> float:
        if not self.running:
            return self.remaining
        return max(self.end_time - time.monotonic(), 0.0)

    def restart(self) -> None:
        """Redémarre le compte à rebours avec le temps restant si encore en cours."""
        self.start()

    def extend(self, seconds: float) -> None:
        """Ajoute du temps au compte à rebours en cours (ou en pause)."""
        add = max(float(seconds), 0.0)
        if add <= 0:
            return
        self.total += add
        if self.running:
            self.remaining = self.remaining_left() + add
            self.end_time = time.monotonic() + self.remaining
        else:
            self.remaining += add

    def is_finished(self) -> bool:
        return self.running and self.remaining_left() <= 0.0