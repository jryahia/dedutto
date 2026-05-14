"""Dedutto — Entry point."""
import sys
import tkinter as tk
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging import get_logger

log = get_logger("dedutto.main")


def main():
    from core.database import Database, DB_PATH
    from ui.dialogs import PasswordDialog
    from ui.main_window import MainWindow
    from ui import theme

    root = tk.Tk()
    root.withdraw()  # Hide while setting up

    theme.apply_theme(root)

    # Determine if this is a first-run (no DB file yet)
    is_new = not DB_PATH.exists()

    # Prompt for master password
    password = PasswordDialog.ask(root, is_new=is_new, lang="it")
    if password is None:
        log.info("User cancelled password entry — exiting")
        root.destroy()
        sys.exit(0)

    # Open database
    try:
        db = Database(password=password)
    except ValueError as exc:
        import tkinter.messagebox as mb
        mb.showerror(
            "Errore",
            f"Impossibile aprire il database:\n{exc}\n\n"
            "Verifica la password o ripristina un backup.",
        )
        root.destroy()
        sys.exit(1)
    except Exception as exc:
        import tkinter.messagebox as mb
        log.exception("Fatal DB error: %s", exc)
        mb.showerror("Errore critico", f"Errore database:\n{exc}")
        root.destroy()
        sys.exit(1)

    root.deiconify()  # Show the window now
    try:
        MainWindow(root, db)
        root.mainloop()
    finally:
        db.close()
        log.info("Dedutto closed")


if __name__ == "__main__":
    main()
