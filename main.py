import sys

from PySide6 import QtCore, QtWidgets

from tweaks import APP_TITLE, is_admin, is_windows
from ui import MainWindow


def main() -> None:
    if not is_windows():
        print("This tool can only run on Windows.")
        sys.exit(1)

    if not is_admin():
        print("Administrator privileges are required.")
        sys.exit(1)

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


if __name__ == "__main__":
    main()
