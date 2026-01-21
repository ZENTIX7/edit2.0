from __future__ import annotations

import math
from dataclasses import dataclass
from functools import partial
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets

from tweaks import (
    APP_TITLE,
    TWEAKS,
    Tweak,
    apply_tweak,
    create_backup_dir,
    iter_categories,
    restart_explorer,
)


@dataclass
class TweakResult:
    success: bool
    message: str
    tweak: Tweak | None = None


class AnimatedButton(QtWidgets.QPushButton):
    def __init__(self, text: str, accent: QtGui.QColor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(text, parent)
        self._base_color = accent
        self._hover_color = accent.lighter(120)
        self._press_color = accent.darker(115)
        self._current_color = accent
        self._animation = QtCore.QPropertyAnimation(self, b"color")
        self._animation.setDuration(180)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet(self._style_for_color(self._current_color))

    def _style_for_color(self, color: QtGui.QColor) -> str:
        return (
            "QPushButton {"
            f"background-color: {color.name()};"
            "color: #0b0f16;"
            "border: none;"
            "border-radius: 10px;"
            "font-weight: 600;"
            "padding: 6px 16px;"
            "}"
        )

    def enterEvent(self, event: QtGui.QEnterEvent) -> None:
        self._animate_to(self._hover_color)
        super().enterEvent(event)

    def leaveEvent(self, event: QtCore.QEvent) -> None:
        self._animate_to(self._base_color)
        super().leaveEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        self._animate_to(self._press_color)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        self._animate_to(self._hover_color)
        super().mouseReleaseEvent(event)

    def _animate_to(self, color: QtGui.QColor) -> None:
        self._animation.stop()
        self._animation.setStartValue(self._current_color)
        self._animation.setEndValue(color)
        self._animation.valueChanged.connect(self._on_color_update)
        self._animation.start()

    def _on_color_update(self, color: QtGui.QColor) -> None:
        self._current_color = color
        self.setStyleSheet(self._style_for_color(color))


class GlassButton(QtWidgets.QPushButton):
    def __init__(self, icon: str, tooltip: str, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setText(icon)
        self.setToolTip(tooltip)
        self.setFixedSize(36, 28)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(255, 255, 255, 0.08);"
            "color: #e3e8f4;"
            "border: none;"
            "border-radius: 8px;"
            "font-size: 14px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(125, 92, 255, 0.4);"
            "}"
        )


class Toast(QtWidgets.QFrame):
    def __init__(self, message: str, accent: QtGui.QColor, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self.setStyleSheet(
            "QFrame {"
            "background-color: rgba(20, 23, 32, 0.95);"
            "border-radius: 12px;"
            "border: 1px solid rgba(255, 255, 255, 0.08);"
            "}"
        )
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(10)

        dot = QtWidgets.QLabel()
        dot.setFixedSize(10, 10)
        dot.setStyleSheet(
            f"background-color: {accent.name()}; border-radius: 5px;"
        )
        layout.addWidget(dot)

        label = QtWidgets.QLabel(message)
        label.setStyleSheet("color: #e6ecff; font-size: 12px;")
        label.setWordWrap(True)
        layout.addWidget(label)

        self.setGraphicsEffect(self._shadow())
        self.setWindowOpacity(0.0)

    @staticmethod
    def _shadow() -> QtWidgets.QGraphicsDropShadowEffect:
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(18)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        shadow.setOffset(0, 8)
        return shadow


class ToastManager(QtCore.QObject):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self._parent = parent
        self._toasts: list[Toast] = []
        self._accent = QtGui.QColor("#7d5cff")

    def set_accent(self, color: QtGui.QColor) -> None:
        self._accent = color

    def show_toast(self, message: str) -> None:
        toast = Toast(message, self._accent, self._parent)
        toast.setFixedWidth(320)
        toast.show()
        self._toasts.insert(0, toast)
        self._reposition_toasts()
        self._animate_toast(toast)

    def _animate_toast(self, toast: Toast) -> None:
        fade_in = QtCore.QPropertyAnimation(toast, b"windowOpacity")
        fade_in.setDuration(200)
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade_in.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

        timer = QtCore.QTimer(toast)
        timer.setSingleShot(True)
        timer.timeout.connect(partial(self._fade_out, toast))
        timer.start(3200)

    def _fade_out(self, toast: Toast) -> None:
        fade_out = QtCore.QPropertyAnimation(toast, b"windowOpacity")
        fade_out.setDuration(250)
        fade_out.setStartValue(toast.windowOpacity())
        fade_out.setEndValue(0.0)
        fade_out.finished.connect(partial(self._remove_toast, toast))
        fade_out.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _remove_toast(self, toast: Toast) -> None:
        if toast in self._toasts:
            self._toasts.remove(toast)
        toast.deleteLater()
        self._reposition_toasts()

    def _reposition_toasts(self) -> None:
        margin = 18
        spacing = 12
        x = self._parent.width() - margin - 320
        y = margin + 60
        for toast in self._toasts:
            toast.move(x, y)
            y += toast.height() + spacing


class AnimatedBlob(QtWidgets.QWidget):
    def __init__(self, parent: QtWidgets.QWidget) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._phase = 0.0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def _tick(self) -> None:
        self._phase += 0.015
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w * (0.35 + 0.1 * math.sin(self._phase))
        cy = h * (0.3 + 0.12 * math.cos(self._phase))
        gradient = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), w * 0.5)
        gradient.setColorAt(0.0, QtGui.QColor(125, 92, 255, 120))
        gradient.setColorAt(1.0, QtGui.QColor(15, 17, 22, 0))
        painter.fillRect(self.rect(), gradient)


class TweakWorker(QtCore.QObject):
    finished = QtCore.Signal(TweakResult)

    def __init__(self, tweak: Tweak, backup_dir: Path, backed_up: set[str]) -> None:
        super().__init__()
        self._tweak = tweak
        self._backup_dir = backup_dir
        self._backed_up = backed_up

    def run(self) -> None:
        try:
            apply_tweak(self._tweak, self._backup_dir, self._backed_up)
            message = self._tweak.post_message or "Tweak applied successfully."
            self.finished.emit(TweakResult(True, message, self._tweak))
        except RuntimeError as exc:
            self.finished.emit(TweakResult(False, str(exc), self._tweak))


class TweakCard(QtWidgets.QFrame):
    def __init__(
        self,
        tweak: Tweak,
        accent: QtGui.QColor,
        on_apply: callable,
        on_restore: callable,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._tweak = tweak
        self.setStyleSheet(
            "QFrame {"
            "background-color: rgba(21, 24, 34, 0.9);"
            "border-radius: 18px;"
            "border: 1px solid rgba(255, 255, 255, 0.05);"
            "}"
        )
        self.setGraphicsEffect(self._shadow())

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title = QtWidgets.QLabel(tweak.label)
        title.setStyleSheet("color: #f5f7ff; font-size: 14px; font-weight: 600;")
        layout.addWidget(title)

        desc = QtWidgets.QLabel(tweak.description)
        desc.setStyleSheet("color: #9aa3b7; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        footer = QtWidgets.QHBoxLayout()
        footer.addStretch()
        restore_button = QtWidgets.QPushButton("Restore")
        restore_button.setCursor(QtCore.Qt.PointingHandCursor)
        restore_button.setFixedHeight(32)
        restore_button.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(255, 255, 255, 0.08);"
            "color: #dfe6f4;"
            "border: none;"
            "border-radius: 10px;"
            "padding: 4px 14px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(255, 255, 255, 0.16);"
            "}"
        )
        restore_button.clicked.connect(partial(on_restore, tweak))
        footer.addWidget(restore_button)

        apply_button = AnimatedButton("Apply", accent)
        apply_button.clicked.connect(partial(on_apply, tweak))
        footer.addWidget(apply_button)

        layout.addLayout(footer)

    @staticmethod
    def _shadow() -> QtWidgets.QGraphicsDropShadowEffect:
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QtGui.QColor(0, 0, 0, 160))
        shadow.setOffset(0, 10)
        return shadow


class MainWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowSystemMenuHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.resize(1100, 720)

        self._accent = QtGui.QColor("#7d5cff")
        self._backup_dir = create_backup_dir()
        self._backed_up: set[str] = set()
        self._active_category = "All"

        self._toast_manager = ToastManager(self)
        self._toast_manager.set_accent(self._accent)

        self._build_ui()
        self._start_intro_animation()

    def _build_ui(self) -> None:
        self._container = QtWidgets.QFrame(self)
        self._container.setObjectName("container")
        self._container.setStyleSheet(
            "#container {"
            "background-color: rgba(15, 17, 22, 0.96);"
            "border-radius: 22px;"
            "border: 1px solid rgba(255, 255, 255, 0.05);"
            "}"
        )
        self._container.setGraphicsEffect(self._shadow())

        layout = QtWidgets.QVBoxLayout(self._container)
        layout.setContentsMargins(20, 18, 20, 20)
        layout.setSpacing(16)

        self._blob = AnimatedBlob(self._container)
        self._blob.lower()

        self._title_bar = self._build_title_bar()
        layout.addWidget(self._title_bar)

        content = QtWidgets.QHBoxLayout()
        content.setSpacing(18)
        layout.addLayout(content)

        sidebar = self._build_sidebar()
        content.addWidget(sidebar, 0)

        main_area = QtWidgets.QVBoxLayout()
        main_area.setSpacing(16)
        content.addLayout(main_area, 1)

        main_area.addLayout(self._build_header())
        main_area.addWidget(self._build_search())
        main_area.addWidget(self._build_tweak_list(), 1)

        right_panel = self._build_status_panel()
        content.addWidget(right_panel, 0)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._container.setGeometry(10, 10, self.width() - 20, self.height() - 20)
        self._blob.setGeometry(0, 0, self._container.width(), self._container.height())
        self._toast_manager._reposition_toasts()
        super().resizeEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, QtGui.QColor(10, 12, 18))
        gradient.setColorAt(1.0, QtGui.QColor(18, 20, 28))
        painter.fillRect(rect, gradient)

        vignette = QtGui.QRadialGradient(rect.center(), rect.width() * 0.6)
        vignette.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QtGui.QColor(0, 0, 0, 180))
        painter.fillRect(rect, vignette)
        super().paintEvent(event)

    def _build_title_bar(self) -> QtWidgets.QWidget:
        bar = QtWidgets.QFrame()
        bar.setFixedHeight(48)
        bar.setStyleSheet("background: transparent;")
        layout = QtWidgets.QHBoxLayout(bar)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(10)

        logo = QtWidgets.QLabel("⬤")
        logo.setStyleSheet("color: #7d5cff; font-size: 18px;")
        layout.addWidget(logo)

        title = QtWidgets.QLabel(APP_TITLE)
        title.setStyleSheet("color: #eef2ff; font-size: 14px; font-weight: 600;")
        layout.addWidget(title)
        layout.addStretch()

        self._min_btn = GlassButton("–", "Minimize")
        self._close_btn = GlassButton("✕", "Close")
        self._min_btn.clicked.connect(self.showMinimized)
        self._close_btn.clicked.connect(self.close)
        layout.addWidget(self._min_btn)
        layout.addWidget(self._close_btn)

        bar.mousePressEvent = self._title_mouse_press
        bar.mouseMoveEvent = self._title_mouse_move
        return bar

    def _title_mouse_press(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint()

    def _title_mouse_move(self, event: QtGui.QMouseEvent) -> None:
        if event.buttons() == QtCore.Qt.LeftButton:
            delta = event.globalPosition().toPoint() - self._drag_pos
            self.move(self.pos() + delta)
            self._drag_pos = event.globalPosition().toPoint()

    def _build_sidebar(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFixedWidth(180)
        frame.setStyleSheet(
            "QFrame {"
            "background-color: rgba(18, 20, 28, 0.9);"
            "border-radius: 16px;"
            "border: 1px solid rgba(255, 255, 255, 0.05);"
            "}"
        )
        frame.setGraphicsEffect(self._shadow())

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        title = QtWidgets.QLabel("Categories")
        title.setStyleSheet("color: #d7ddf1; font-weight: 600;")
        layout.addWidget(title)

        self._category_buttons: dict[str, QtWidgets.QPushButton] = {}
        for category in iter_categories(TWEAKS) + ["Power", "Cleanup"]:
            button = QtWidgets.QPushButton(category)
            button.setCursor(QtCore.Qt.PointingHandCursor)
            button.setStyleSheet(self._category_style(category == "All"))
            button.clicked.connect(partial(self._set_category, category))
            layout.addWidget(button)
            self._category_buttons[category] = button

        layout.addStretch()
        return frame

    def _category_style(self, active: bool) -> str:
        base = "rgba(255, 255, 255, 0.08)" if active else "transparent"
        return (
            "QPushButton {"
            f"background-color: {base};"
            "color: #e1e7f7;"
            "border: none;"
            "border-radius: 10px;"
            "padding: 8px 12px;"
            "text-align: left;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(125, 92, 255, 0.3);"
            "}"
        )

    def _build_header(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        title = QtWidgets.QLabel("Tweaks Dashboard")
        title.setStyleSheet("color: #f5f7ff; font-size: 18px; font-weight: 700;")
        layout.addWidget(title)

        badge = QtWidgets.QLabel("Premium")
        badge.setStyleSheet(
            "background-color: rgba(125, 92, 255, 0.25);"
            "color: #dcd4ff;"
            "border-radius: 10px;"
            "padding: 4px 10px;"
            "font-size: 11px;"
        )
        layout.addWidget(badge)
        layout.addStretch()
        return layout

    def _build_search(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setStyleSheet(
            "QFrame {"
            "background-color: rgba(18, 21, 30, 0.9);"
            "border-radius: 14px;"
            "border: 1px solid rgba(255, 255, 255, 0.06);"
            "}"
        )
        layout = QtWidgets.QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)

        icon = QtWidgets.QLabel("🔍")
        icon.setStyleSheet("color: #9aa3b7; font-size: 14px;")
        layout.addWidget(icon)

        self._search = QtWidgets.QLineEdit()
        self._search.setPlaceholderText("Search tweaks...")
        self._search.textChanged.connect(self._filter_tweaks)
        self._search.setStyleSheet(
            "QLineEdit {"
            "background: transparent;"
            "border: none;"
            "color: #eaf0ff;"
            "font-size: 12px;"
            "}"
        )
        layout.addWidget(self._search)
        return frame

    def _build_tweak_list(self) -> QtWidgets.QScrollArea:
        self._scroll = QtWidgets.QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._scroll.setStyleSheet(
            "QScrollArea { background: transparent; }"
            "QScrollBar:vertical {"
            "background: transparent;"
            "width: 8px;"
            "}"
            "QScrollBar::handle:vertical {"
            "background: rgba(125, 92, 255, 0.5);"
            "border-radius: 4px;"
            "}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {"
            "height: 0px;"
            "}"
        )

        container = QtWidgets.QWidget()
        self._tweak_layout = QtWidgets.QVBoxLayout(container)
        self._tweak_layout.setContentsMargins(4, 4, 4, 4)
        self._tweak_layout.setSpacing(14)
        self._scroll.setWidget(container)

        self._render_tweaks()
        return self._scroll

    def _build_status_panel(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFixedWidth(260)
        frame.setStyleSheet(
            "QFrame {"
            "background-color: rgba(18, 20, 28, 0.9);"
            "border-radius: 16px;"
            "border: 1px solid rgba(255, 255, 255, 0.05);"
            "}"
        )
        frame.setGraphicsEffect(self._shadow())

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("Status")
        title.setStyleSheet("color: #d7ddf1; font-weight: 600;")
        layout.addWidget(title)

        self._status_label = QtWidgets.QLabel("Ready to apply tweaks.")
        self._status_label.setStyleSheet("color: #9aa3b7; font-size: 12px;")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._status_chip = QtWidgets.QLabel("Idle")
        self._status_chip.setStyleSheet(
            "background-color: rgba(255, 255, 255, 0.08);"
            "color: #e5ecff;"
            "border-radius: 8px;"
            "padding: 4px 10px;"
            "font-size: 11px;"
        )
        layout.addWidget(self._status_chip)

        self._progress = QtWidgets.QProgressBar()
        self._progress.setRange(0, 0)
        self._progress.setTextVisible(False)
        self._progress.hide()
        self._progress.setStyleSheet(
            "QProgressBar {"
            "background-color: rgba(255, 255, 255, 0.1);"
            "border-radius: 8px;"
            "height: 12px;"
            "}"
            "QProgressBar::chunk {"
            f"background-color: {self._accent.name()};"
            "border-radius: 8px;"
            "}"
        )
        layout.addWidget(self._progress)

        layout.addStretch()
        return frame

    def _render_tweaks(self) -> None:
        while self._tweak_layout.count():
            item = self._tweak_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        for tweak in self._filtered_tweaks():
            card = TweakCard(
                tweak,
                self._accent,
                on_apply=self._handle_apply,
                on_restore=self._handle_restore,
            )
            self._tweak_layout.addWidget(card)

        self._tweak_layout.addStretch()

    def _filtered_tweaks(self) -> list[Tweak]:
        query = self._search.text().strip().lower()
        items = TWEAKS
        if self._active_category != "All":
            items = [t for t in items if t.category == self._active_category]
        if query:
            items = [
                t
                for t in items
                if query in t.label.lower() or query in t.description.lower()
            ]
        return items

    def _filter_tweaks(self) -> None:
        self._render_tweaks()

    def _set_category(self, category: str) -> None:
        self._active_category = category
        for key, button in self._category_buttons.items():
            button.setStyleSheet(self._category_style(key == category))
        self._render_tweaks()

    def _handle_apply(self, tweak: Tweak) -> None:
        self._status_chip.setText("Working")
        self._status_label.setText(f"Applying {tweak.label}...")
        self._progress.show()
        self._backup_dir = create_backup_dir()

        worker = TweakWorker(tweak, self._backup_dir, self._backed_up)
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(self._handle_worker_result)
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _handle_worker_result(self, result: TweakResult) -> None:
        self._progress.hide()
        if result.success:
            self._status_chip.setText("Success")
            self._status_label.setText(result.message)
            self._toast_manager.show_toast(result.message)
            if result.tweak and result.tweak.explorer_notice:
                self._prompt_restart_explorer()
        else:
            self._status_chip.setText("Failed")
            self._status_label.setText(result.message)
            self._toast_manager.show_toast(result.message)

    def _handle_restore(self, tweak: Tweak) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select registry backup",
            str(Path("backups")),
            "Registry Files (*.reg);;All Files (*)",
        )
        if not file_path:
            return
        try:
            from tweaks import restore_backup_file

            restore_backup_file(Path(file_path))
            message = f"Backup restored for {tweak.label}."
            self._status_chip.setText("Restored")
            self._status_label.setText(message)
            self._toast_manager.show_toast(message)
        except RuntimeError as exc:
            self._status_chip.setText("Failed")
            self._status_label.setText(str(exc))
            self._toast_manager.show_toast(str(exc))

    def _prompt_restart_explorer(self) -> None:
        prompt = QtWidgets.QMessageBox(self)
        prompt.setWindowTitle(APP_TITLE)
        prompt.setText("Sign out/in or restart Explorer may be required.")
        prompt.setInformativeText("Restart Explorer now?")
        prompt.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        if prompt.exec() == QtWidgets.QMessageBox.Yes:
            try:
                restart_explorer()
            except RuntimeError as exc:
                self._toast_manager.show_toast(str(exc))

    def _start_intro_animation(self) -> None:
        self.setWindowOpacity(0.0)
        fade = QtCore.QPropertyAnimation(self, b"windowOpacity")
        fade.setDuration(350)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

        geo = self.geometry()
        start_pos = QtCore.QPoint(geo.x(), geo.y() + 30)
        move = QtCore.QPropertyAnimation(self, b"pos")
        move.setDuration(350)
        move.setStartValue(start_pos)
        move.setEndValue(QtCore.QPoint(geo.x(), geo.y()))
        move.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        move.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    @staticmethod
    def _shadow() -> QtWidgets.QGraphicsDropShadowEffect:
        shadow = QtWidgets.QGraphicsDropShadowEffect()
        shadow.setBlurRadius(24)
        shadow.setColor(QtGui.QColor(0, 0, 0, 200))
        shadow.setOffset(0, 12)
        return shadow
