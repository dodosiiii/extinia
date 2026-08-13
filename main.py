"""Point d'entrée de l'application Compte à rebours PC."""

import sys

from app import App, log_exception


def _handle_exception(exc_type, exc_value, exc_tb) -> None:
    """Logge toute erreur fatale dans %APPDATA%\\Extinia\\error.log."""
    log_exception(exc_type, exc_value, exc_tb)


sys.excepthook = _handle_exception


if __name__ == "__main__":
    App().run()