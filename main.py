import sys
import traceback
from pathlib import Path

from PySide6 import QtCore, QtWidgets

from tweaks import APP_TITLE, is_admin, is_windows
from ui import MainWindow


def main() -> None:
    if not is_windows():
        print("This tool can only run on Windows.")
        sys.exit(1)

    if not is_admin():
        print("Administrator privileges are required.")
        QtWidgets.QMessageBox.critical(
            None,
            APP_TITLE,
            "Administrator privileges are required.\n"
            "Please run the launcher batch file as admin.",
        )
        sys.exit(1)

    log_file = Path("launch_debug.log")
    try:
        app = QtWidgets.QApplication(sys.argv)
        screen = app.primaryScreen()
        screen_name = screen.name() if screen else "unknown"
        screen_geo = screen.availableGeometry() if screen else None
        print("GUI framework: PySide6 (Qt)")
        if screen_geo:
            print(
                f"Screen: {screen_name} {screen_geo.width()}x{screen_geo.height()} "
                f"at ({screen_geo.x()}, {screen_geo.y()})"
            )
        else:
            print(f"Screen: {screen_name}")
        app.setApplicationName(APP_TITLE)
        window = MainWindow()
        window.show()
        window.raise_()
        window.activateWindow()
        window.setWindowState(
            (window.windowState() & ~QtCore.Qt.WindowMinimized) | QtCore.Qt.WindowActive
        )
        sys.exit(app.exec())
    except Exception as exc:  # noqa: BLE001
        log_file.write_text(
            "Failed to launch application.\n"
            f"Error: {exc}\n\n"
            f"{traceback.format_exc()}",
            encoding="utf-8",
        )
        print(f"Failed to launch. See {log_file.resolve()}")
        QtWidgets.QMessageBox.critical(
            None,
            APP_TITLE,
            f"Failed to launch. See {log_file.resolve()}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
