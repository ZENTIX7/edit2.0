import sys

from PySide6 import QtWidgets

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
    app.setApplicationName(APP_TITLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
