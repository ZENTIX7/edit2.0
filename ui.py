from __future__ import annotations

import math
from dataclasses import dataclass
from functools import partial
from pathlib import Path
from typing import Callable

from PySide6 import QtCore, QtGui, QtWidgets

from style_manager import ThemePreset, load_presets, save_presets
from tweaks import (
    APP_TITLE,
    TWEAKS,
    Tweak,
    apply_tweak,
    clean_temp_files,
    cleanup_roblox,
    create_backup_dir,
    iter_categories,
    restart_explorer,
)


@dataclass
class TweakResult:
    success: bool
    message: str
    tweak: Tweak | None = None


@dataclass
class TaskResult:
    success: bool
    message: str


class AnimationSettings:
    def __init__(self, speed: float = 1.0) -> None:
        self.speed = speed

    def scale(self, ms: int) -> int:
        return max(1, int(ms * self.speed))


class AnimatedButton(QtWidgets.QPushButton):
    def __init__(
        self,
        text: str,
        accent: QtGui.QColor,
        animation: AnimationSettings,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self._animation_settings = animation
        self._base_color = accent
        self._hover_color = accent.lighter(120)
        self._press_color = accent.darker(115)
        self._current_color = accent
        self._animation = QtCore.QVariantAnimation(self)
        self._animation.valueChanged.connect(self._on_color_update)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self.setFixedHeight(36)
        self.setStyleSheet(self._style_for_color(self._current_color))

    def set_accent(self, accent: QtGui.QColor) -> None:
        self._base_color = accent
        self._hover_color = accent.lighter(120)
        self._press_color = accent.darker(115)
        self._animate_to(self._base_color)

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
        self._animation.setDuration(self._animation_settings.scale(180))
        self._animation.setStartValue(self._current_color)
        self._animation.setEndValue(color)
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


class ColorButton(QtWidgets.QPushButton):
    def __init__(self, color: QtGui.QColor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._color = color
        self.setFixedSize(44, 26)
        self.setCursor(QtCore.Qt.PointingHandCursor)
        self._apply_style()

    def color(self) -> QtGui.QColor:
        return self._color

    def set_color(self, color: QtGui.QColor) -> None:
        self._color = color
        self._apply_style()

    def _apply_style(self) -> None:
        self.setStyleSheet(
            "QPushButton {"
            f"background-color: {self._color.name()};"
            "border-radius: 8px;"
            "border: 1px solid rgba(255, 255, 255, 0.2);"
            "}"
        )


class Toast(QtWidgets.QFrame):
    def __init__(self, message: str, color: QtGui.QColor, parent: QtWidgets.QWidget) -> None:
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
            f"background-color: {color.name()}; border-radius: 5px;"
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
    def __init__(self, parent: QtWidgets.QWidget, animation: AnimationSettings) -> None:
        super().__init__(parent)
        self._parent = parent
        self._toasts: list[Toast] = []
        self._accent = QtGui.QColor("#7d5cff")
        self._animation = animation

    def set_accent(self, color: QtGui.QColor) -> None:
        self._accent = color

    def show_toast(self, message: str, tone: str = "neutral") -> None:
        color = self._accent
        if tone == "success":
            color = QtGui.QColor("#32d583")
        elif tone == "error":
            color = QtGui.QColor("#f97066")
        elif tone == "neutral":
            color = QtGui.QColor("#94a3b8")

        toast = Toast(message, color, self._parent)
        toast.setFixedWidth(320)
        toast.show()
        self._toasts.insert(0, toast)
        self._reposition_toasts()
        self._animate_toast(toast)

    def _animate_toast(self, toast: Toast) -> None:
        fade_in = QtCore.QPropertyAnimation(toast, b"windowOpacity")
        fade_in.setDuration(self._animation.scale(200))
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.OutCubic)
        fade_in.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

        timer = QtCore.QTimer(toast)
        timer.setSingleShot(True)
        timer.timeout.connect(partial(self._fade_out, toast))
        timer.start(self._animation.scale(3200))

    def _fade_out(self, toast: Toast) -> None:
        fade_out = QtCore.QPropertyAnimation(toast, b"windowOpacity")
        fade_out.setDuration(self._animation.scale(250))
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
    def __init__(self, parent: QtWidgets.QWidget, color: QtGui.QColor) -> None:
        super().__init__(parent)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
        self._phase = 0.0
        self._color = color
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)

    def set_color(self, color: QtGui.QColor) -> None:
        self._color = color
        self.update()

    def _tick(self) -> None:
        self._phase += 0.015
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        w, h = self.width(), self.height()
        cx = w * (0.35 + 0.1 * math.sin(self._phase))
        cy = h * (0.3 + 0.12 * math.cos(self._phase))
        gradient = QtGui.QRadialGradient(QtCore.QPointF(cx, cy), w * 0.55)
        gradient.setColorAt(0.0, QtGui.QColor(self._color.red(), self._color.green(), self._color.blue(), 120))
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
            self.finished.emit(TweakResult(True, "Applied tweak successfully!", self._tweak))
        except RuntimeError as exc:
            self.finished.emit(TweakResult(False, str(exc), self._tweak))


class TaskWorker(QtCore.QObject):
    finished = QtCore.Signal(TaskResult)

    def __init__(self, task: Callable[[], str]) -> None:
        super().__init__()
        self._task = task

    def run(self) -> None:
        try:
            message = self._task()
            self.finished.emit(TaskResult(True, message))
        except RuntimeError as exc:
            self.finished.emit(TaskResult(False, str(exc)))


class TweakCard(QtWidgets.QFrame):
    def __init__(
        self,
        tweak: Tweak,
        accent: QtGui.QColor,
        animation: AnimationSettings,
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
            "border: 1px solid rgba(255, 255, 255, 0.06);"
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

        apply_button = AnimatedButton("Apply", accent, animation)
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


class ColorPickerDialog(QtWidgets.QDialog):
    def __init__(self, title: str, color: QtGui.QColor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setWindowFlags(QtCore.Qt.Dialog | QtCore.Qt.FramelessWindowHint)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._color = QtGui.QColor(color)

        self.setStyleSheet(
            "QDialog {"
            "background-color: rgba(18, 20, 30, 0.98);"
            "border: 1px solid rgba(255, 255, 255, 0.08);"
            "border-radius: 16px;"
            "}"
        )

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(12)

        header = QtWidgets.QLabel(title)
        header.setStyleSheet("color: #e9efff; font-size: 13px; font-weight: 600;")
        layout.addWidget(header)

        self._preview = QtWidgets.QFrame()
        self._preview.setFixedHeight(46)
        self._preview.setStyleSheet(
            f"background-color: {self._color.name()}; border-radius: 12px;"
        )
        layout.addWidget(self._preview)

        palette = QtWidgets.QGridLayout()
        palette.setHorizontalSpacing(8)
        palette.setVerticalSpacing(8)
        colors = [
            "#7d5cff",
            "#29d3ff",
            "#22c55e",
            "#f97316",
            "#f43f5e",
            "#eab308",
            "#a855f7",
            "#94a3b8",
        ]
        row = 0
        col = 0
        for item in colors:
            swatch = QtWidgets.QPushButton()
            swatch.setFixedSize(28, 28)
            swatch.setStyleSheet(
                "QPushButton {"
                f"background-color: {item};"
                "border-radius: 8px;"
                "border: 1px solid rgba(255, 255, 255, 0.15);"
                "}"
                "QPushButton:hover {"
                "border: 1px solid rgba(255, 255, 255, 0.4);"
                "}"
            )
            swatch.clicked.connect(partial(self._set_hex, item))
            palette.addWidget(swatch, row, col)
            col += 1
            if col == 4:
                col = 0
                row += 1
        layout.addLayout(palette)

        self._hex = QtWidgets.QLineEdit(self._color.name())
        self._hex.setPlaceholderText("#RRGGBB")
        self._hex.setStyleSheet(
            "QLineEdit {"
            "background-color: rgba(255, 255, 255, 0.08);"
            "border-radius: 8px;"
            "border: 1px solid rgba(255, 255, 255, 0.1);"
            "color: #e6ecff;"
            "padding: 6px 8px;"
            "}"
        )
        self._hex.textChanged.connect(self._hex_changed)
        layout.addWidget(self._hex)

        self._sliders: dict[str, QtWidgets.QSlider] = {}
        for label, value in (("R", self._color.red()), ("G", self._color.green()), ("B", self._color.blue())):
            row_layout = QtWidgets.QHBoxLayout()
            row_label = QtWidgets.QLabel(label)
            row_label.setStyleSheet("color: #cfd6e6; font-size: 12px;")
            slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
            slider.setRange(0, 255)
            slider.setValue(value)
            slider.setStyleSheet(
                "QSlider::groove:horizontal {"
                "height: 6px;"
                "background: rgba(255, 255, 255, 0.15);"
                "border-radius: 3px;"
                "}"
                "QSlider::handle:horizontal {"
                "width: 14px;"
                "background: #eef2ff;"
                "border-radius: 7px;"
                "margin-top: -4px;"
                "margin-bottom: -4px;"
                "}"
            )
            slider.valueChanged.connect(self._slider_changed)
            row_layout.addWidget(row_label)
            row_layout.addWidget(slider)
            layout.addLayout(row_layout)
            self._sliders[label] = slider

        actions = QtWidgets.QHBoxLayout()
        actions.addStretch()
        cancel = QtWidgets.QPushButton("Cancel")
        cancel.setCursor(QtCore.Qt.PointingHandCursor)
        cancel.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(255, 255, 255, 0.08);"
            "border-radius: 10px;"
            "color: #e2e8f0;"
            "padding: 6px 14px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(255, 255, 255, 0.15);"
            "}"
        )
        cancel.clicked.connect(self.reject)
        apply = QtWidgets.QPushButton("Apply")
        apply.setCursor(QtCore.Qt.PointingHandCursor)
        apply.setStyleSheet(
            "QPushButton {"
            "background-color: #7d5cff;"
            "border-radius: 10px;"
            "color: #0b0f16;"
            "font-weight: 600;"
            "padding: 6px 14px;"
            "}"
            "QPushButton:hover {"
            "background-color: #6a49ff;"
            "}"
        )
        apply.clicked.connect(self.accept)
        actions.addWidget(cancel)
        actions.addWidget(apply)
        layout.addLayout(actions)

    def color(self) -> QtGui.QColor:
        return self._color

    def _set_hex(self, value: str) -> None:
        self._hex.setText(value)

    def _hex_changed(self, value: str) -> None:
        if not value.startswith("#"):
            value = f"#{value}"
        if len(value) != 7:
            return
        color = QtGui.QColor(value)
        if not color.isValid():
            return
        self._update_color(color)
        self._sync_sliders(color)

    def _slider_changed(self) -> None:
        color = QtGui.QColor(
            self._sliders["R"].value(),
            self._sliders["G"].value(),
            self._sliders["B"].value(),
        )
        self._update_color(color)
        self._hex.blockSignals(True)
        self._hex.setText(color.name())
        self._hex.blockSignals(False)

    def _sync_sliders(self, color: QtGui.QColor) -> None:
        for channel, value in zip(("R", "G", "B"), (color.red(), color.green(), color.blue())):
            slider = self._sliders[channel]
            slider.blockSignals(True)
            slider.setValue(value)
            slider.blockSignals(False)

    def _update_color(self, color: QtGui.QColor) -> None:
        self._color = color
        self._preview.setStyleSheet(
            f"background-color: {self._color.name()}; border-radius: 12px;"
        )


class PresetRow(QtWidgets.QFrame):
    def __init__(
        self,
        preset: ThemePreset,
        on_apply: Callable[[ThemePreset], None],
        on_delete: Callable[[ThemePreset], None],
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setStyleSheet(
            "QFrame {"
            "background-color: rgba(255, 255, 255, 0.04);"
            "border-radius: 12px;"
            "border: 1px solid rgba(255, 255, 255, 0.05);"
            "}"
        )
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)

        button = QtWidgets.QPushButton(preset.name)
        button.setCursor(QtCore.Qt.PointingHandCursor)
        button.setStyleSheet(
            "QPushButton {"
            "text-align: left;"
            "color: #e6ecff;"
            "background: transparent;"
            "border: none;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "color: #ffffff;"
            "}"
        )
        button.clicked.connect(partial(on_apply, preset))
        layout.addWidget(button, 1)

        delete = QtWidgets.QPushButton("✕")
        delete.setCursor(QtCore.Qt.PointingHandCursor)
        delete.setFixedSize(26, 26)
        delete.setStyleSheet(
            "QPushButton {"
            "background-color: rgba(255, 255, 255, 0.08);"
            "border-radius: 8px;"
            "color: #e6ecff;"
            "border: none;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(239, 68, 68, 0.5);"
            "}"
        )
        delete.clicked.connect(partial(on_delete, preset))
        layout.addWidget(delete)


class MainWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowFlags(
            QtCore.Qt.Window
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowSystemMenuHint
            | QtCore.Qt.WindowMinimizeButtonHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, False)
        self.setWindowOpacity(1.0)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self.resize(1120, 720)

        self._main_color = QtGui.QColor("#101623")
        self._accent = QtGui.QColor("#7d5cff")
        self._animation = AnimationSettings(1.0)
        self._backup_dir = create_backup_dir()
        self._backed_up: set[str] = set()
        self._active_category = "All"
        self._presets = load_presets()

        self._toast_manager = ToastManager(self, self._animation)
        self._toast_manager.set_accent(self._accent)

        self._build_ui()
        self._start_intro_animation()
        self._drag_pos = QtCore.QPoint()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(16)

        self._blob = AnimatedBlob(self, self._accent)
        self._blob.lower()

        self._title_bar = self._build_title_bar()
        self._title_bar.installEventFilter(self)
        layout.addWidget(self._title_bar)

        body = QtWidgets.QHBoxLayout()
        body.setSpacing(18)
        layout.addLayout(body)

        sidebar = self._build_sidebar()
        body.addWidget(sidebar, 0)

        self._page_stack = QtWidgets.QStackedWidget()
        self._page_stack.setStyleSheet("background: transparent;")
        body.addWidget(self._page_stack, 1)

        self._tweaks_page = self._build_tweaks_page()
        self._power_page = self._build_power_page()
        self._cleanup_page = self._build_cleanup_page()
        self._style_page = self._build_style_page()

        self._page_stack.addWidget(self._tweaks_page)
        self._page_stack.addWidget(self._power_page)
        self._page_stack.addWidget(self._cleanup_page)
        self._page_stack.addWidget(self._style_page)
        self._page_stack.setCurrentWidget(self._tweaks_page)

    def showEvent(self, event: QtGui.QShowEvent) -> None:
        screen = QtWidgets.QApplication.primaryScreen()
        if screen:
            available = screen.availableGeometry()
            size = self.size()
            x = available.x() + (available.width() - size.width()) // 2
            y = available.y() + (available.height() - size.height()) // 2
            x = max(available.x(), min(x, available.x() + available.width() - size.width()))
            y = max(available.y(), min(y, available.y() + available.height() - size.height()))
            self.move(x, y)
        QtCore.QTimer.singleShot(150, self._force_activate)
        self._blob.setGeometry(0, 0, self.width(), self.height())
        super().showEvent(event)

    def resizeEvent(self, event: QtGui.QResizeEvent) -> None:
        self._blob.setGeometry(0, 0, self.width(), self.height())
        self._toast_manager._reposition_toasts()
        super().resizeEvent(event)

    def _force_activate(self) -> None:
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect()

        base = QtGui.QColor(self._main_color)
        darker = base.darker(130)
        lighter = base.lighter(130)

        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, darker)
        gradient.setColorAt(1.0, lighter)
        painter.fillRect(rect, gradient)

        vignette = QtGui.QRadialGradient(rect.center(), rect.width() * 0.6)
        vignette.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QtGui.QColor(0, 0, 0, 190))
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
        logo.setStyleSheet(f"color: {self._accent.name()}; font-size: 18px;")
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

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:
        if isinstance(obj, QtWidgets.QPushButton):
            return super().eventFilter(obj, event)
        if obj is self._title_bar or self._title_bar.isAncestorOf(obj):
            if event.type() == QtCore.QEvent.MouseButtonPress:
                mouse_event = event  # type: ignore[assignment]
                if mouse_event.button() == QtCore.Qt.LeftButton:
                    self._drag_pos = mouse_event.globalPosition().toPoint()
                    return True
            if event.type() == QtCore.QEvent.MouseMove:
                mouse_event = event  # type: ignore[assignment]
                if mouse_event.buttons() == QtCore.Qt.LeftButton:
                    delta = mouse_event.globalPosition().toPoint() - self._drag_pos
                    self.move(self.pos() + delta)
                    self._drag_pos = mouse_event.globalPosition().toPoint()
                    return True
        return super().eventFilter(obj, event)

    def _build_sidebar(self) -> QtWidgets.QFrame:
        frame = QtWidgets.QFrame()
        frame.setFixedWidth(190)
        frame.setStyleSheet(
            "QFrame {"
            "background-color: rgba(18, 20, 30, 0.8);"
            "border-radius: 18px;"
            "border: 1px solid rgba(255, 255, 255, 0.06);"
            "}"
        )
        frame.setGraphicsEffect(self._shadow())

        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(14, 16, 14, 16)
        layout.setSpacing(10)

        title = QtWidgets.QLabel("Categories")
        title.setStyleSheet("color: #d7ddf1; font-weight: 600;")
        layout.addWidget(title)

        self._category_buttons: dict[str, QtWidgets.QPushButton] = {}
        categories = iter_categories(TWEAKS)
        for name in ["Style", "Power", "Cleanup"]:
            if name not in categories:
                categories.append(name)
        for category in categories:
            button = QtWidgets.QPushButton(category)
            button.setCursor(QtCore.Qt.PointingHandCursor)
            button.setStyleSheet(self._category_style(category == "All"))
            button.clicked.connect(partial(self._set_category, category))
            layout.addWidget(button)
            self._category_buttons[category] = button

        layout.addStretch()
        return frame

    def _category_style(self, active: bool) -> str:
        base = "rgba(125, 92, 255, 0.35)" if active else "transparent"
        return (
            "QPushButton {"
            f"background-color: {base};"
            "color: #e1e7f7;"
            "border: none;"
            "border-radius: 12px;"
            "padding: 8px 12px;"
            "text-align: left;"
            "font-weight: 600;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(125, 92, 255, 0.25);"
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
            "background-color: rgba(18, 21, 30, 0.8);"
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

    def _build_tweaks_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(self._build_header())
        layout.addWidget(self._build_search())
        layout.addWidget(self._build_tweak_list(), 1)
        return page

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

    def _build_power_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addStretch()
        label = QtWidgets.QLabel("Coming soon")
        label.setAlignment(QtCore.Qt.AlignCenter)
        label.setStyleSheet("color: #e6ecff; font-size: 18px; font-weight: 600;")
        layout.addWidget(label)
        layout.addStretch()
        return page

    def _build_cleanup_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QtWidgets.QLabel("Cleanup Tools")
        header.setStyleSheet("color: #f5f7ff; font-size: 18px; font-weight: 700;")
        layout.addWidget(header)

        layout.addWidget(
            self._action_card(
                title="Clean Temp Files",
                description="Delete cached files in your user temp directory.",
                action=self._handle_clean_temp,
            )
        )
        layout.addWidget(
            self._action_card(
                title="Roblox Clean Up",
                description="Remove Roblox cache folders and temp files.",
                action=self._handle_clean_roblox,
            )
        )
        layout.addStretch()
        return page

    def _action_card(self, title: str, description: str, action: Callable[[], None]) -> QtWidgets.QFrame:
        card = QtWidgets.QFrame()
        card.setStyleSheet(
            "QFrame {"
            "background-color: rgba(21, 24, 34, 0.9);"
            "border-radius: 18px;"
            "border: 1px solid rgba(255, 255, 255, 0.06);"
            "}"
        )
        card.setGraphicsEffect(self._shadow())
        layout = QtWidgets.QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(10)

        title_label = QtWidgets.QLabel(title)
        title_label.setStyleSheet("color: #f5f7ff; font-size: 14px; font-weight: 600;")
        layout.addWidget(title_label)

        desc = QtWidgets.QLabel(description)
        desc.setStyleSheet("color: #9aa3b7; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        action_button = AnimatedButton("Run", self._accent, self._animation)
        action_button.clicked.connect(action)
        layout.addWidget(action_button, alignment=QtCore.Qt.AlignRight)
        return card

    def _build_style_page(self) -> QtWidgets.QWidget:
        page = QtWidgets.QWidget()
        page.setStyleSheet("background: transparent;")
        layout = QtWidgets.QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(16)

        header = QtWidgets.QLabel("Style")
        header.setStyleSheet("color: #f5f7ff; font-size: 18px; font-weight: 700;")
        layout.addWidget(header)

        theme_card = QtWidgets.QFrame()
        theme_card.setStyleSheet(
            "QFrame {"
            "background-color: rgba(18, 20, 30, 0.8);"
            "border-radius: 16px;"
            "border: 1px solid rgba(255, 255, 255, 0.06);"
            "}"
        )
        theme_layout = QtWidgets.QVBoxLayout(theme_card)
        theme_layout.setContentsMargins(16, 14, 16, 14)
        theme_layout.setSpacing(12)

        main_row = QtWidgets.QHBoxLayout()
        main_label = QtWidgets.QLabel("Main color")
        main_label.setStyleSheet("color: #cfd6e6; font-size: 12px;")
        self._main_color_button = ColorButton(self._main_color)
        self._main_color_button.clicked.connect(self._pick_main_color)
        main_row.addWidget(main_label)
        main_row.addStretch()
        main_row.addWidget(self._main_color_button)
        theme_layout.addLayout(main_row)

        glow_row = QtWidgets.QHBoxLayout()
        glow_label = QtWidgets.QLabel("Secondary/Glow color")
        glow_label.setStyleSheet("color: #cfd6e6; font-size: 12px;")
        self._glow_color_button = ColorButton(self._accent)
        self._glow_color_button.clicked.connect(self._pick_glow_color)
        glow_row.addWidget(glow_label)
        glow_row.addStretch()
        glow_row.addWidget(self._glow_color_button)
        theme_layout.addLayout(glow_row)

        speed_row = QtWidgets.QHBoxLayout()
        speed_label = QtWidgets.QLabel("Animation speed")
        speed_label.setStyleSheet("color: #cfd6e6; font-size: 12px;")
        self._speed_value = QtWidgets.QLabel(f"{self._animation.speed:.1f}x")
        self._speed_value.setStyleSheet("color: #e6ecff; font-weight: 600;")
        speed_row.addWidget(speed_label)
        speed_row.addStretch()
        speed_row.addWidget(self._speed_value)
        theme_layout.addLayout(speed_row)

        self._speed_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self._speed_slider.setRange(50, 200)
        self._speed_slider.setValue(int(self._animation.speed * 100))
        self._speed_slider.setStyleSheet(
            "QSlider::groove:horizontal {"
            "height: 6px;"
            "background: rgba(255, 255, 255, 0.15);"
            "border-radius: 3px;"
            "}"
            "QSlider::handle:horizontal {"
            "width: 16px;"
            "background: #eef2ff;"
            "border-radius: 8px;"
            "margin-top: -5px;"
            "margin-bottom: -5px;"
            "}"
        )
        self._speed_slider.valueChanged.connect(self._update_speed)
        theme_layout.addWidget(self._speed_slider)

        layout.addWidget(theme_card)

        preset_card = QtWidgets.QFrame()
        preset_card.setStyleSheet(
            "QFrame {"
            "background-color: rgba(18, 20, 30, 0.8);"
            "border-radius: 16px;"
            "border: 1px solid rgba(255, 255, 255, 0.06);"
            "}"
        )
        preset_layout = QtWidgets.QVBoxLayout(preset_card)
        preset_layout.setContentsMargins(16, 14, 16, 14)
        preset_layout.setSpacing(12)

        preset_title = QtWidgets.QLabel("Presets")
        preset_title.setStyleSheet("color: #cfd6e6; font-weight: 600;")
        preset_layout.addWidget(preset_title)

        form = QtWidgets.QHBoxLayout()
        self._preset_name = QtWidgets.QLineEdit()
        self._preset_name.setPlaceholderText("Preset name")
        self._preset_name.setStyleSheet(
            "QLineEdit {"
            "background-color: rgba(255, 255, 255, 0.08);"
            "border-radius: 8px;"
            "border: 1px solid rgba(255, 255, 255, 0.1);"
            "color: #e6ecff;"
            "padding: 6px 8px;"
            "}"
        )
        save_button = AnimatedButton("Save", self._accent, self._animation)
        save_button.clicked.connect(self._save_preset)
        form.addWidget(self._preset_name, 1)
        form.addWidget(save_button)
        preset_layout.addLayout(form)

        self._preset_scroll = QtWidgets.QScrollArea()
        self._preset_scroll.setWidgetResizable(True)
        self._preset_scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self._preset_scroll.setStyleSheet("QScrollArea { background: transparent; }")
        preset_container = QtWidgets.QWidget()
        self._preset_list = QtWidgets.QVBoxLayout(preset_container)
        self._preset_list.setContentsMargins(0, 0, 0, 0)
        self._preset_list.setSpacing(10)
        self._preset_scroll.setWidget(preset_container)
        preset_layout.addWidget(self._preset_scroll)

        layout.addWidget(preset_card)
        layout.addStretch()

        self._render_presets()
        return page

    def _render_presets(self) -> None:
        while self._preset_list.count():
            item = self._preset_list.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
        if not self._presets:
            empty = QtWidgets.QLabel("No presets yet.")
            empty.setStyleSheet("color: #9aa3b7; font-size: 12px;")
            self._preset_list.addWidget(empty)
        else:
            for preset in self._presets:
                row = PresetRow(preset, self._apply_preset, self._delete_preset)
                self._preset_list.addWidget(row)
        self._preset_list.addStretch()

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
                self._animation,
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

        if category == "Power":
            self._animate_page_switch(self._power_page)
            return
        if category == "Cleanup":
            self._animate_page_switch(self._cleanup_page)
            return
        if category == "Style":
            self._animate_page_switch(self._style_page)
            return

        self._animate_page_switch(self._tweaks_page)
        self._render_tweaks()

    def _animate_page_switch(self, target: QtWidgets.QWidget) -> None:
        if self._page_stack.currentWidget() is target:
            return
        effect = QtWidgets.QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)
        effect.setOpacity(0.0)

        self._page_stack.setCurrentWidget(target)
        target_pos = target.pos()
        target.move(target_pos + QtCore.QPoint(0, 12))

        fade = QtCore.QPropertyAnimation(effect, b"opacity")
        fade.setDuration(self._animation.scale(220))
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        slide = QtCore.QPropertyAnimation(target, b"pos")
        slide.setDuration(self._animation.scale(220))
        slide.setStartValue(target.pos())
        slide.setEndValue(target_pos)
        slide.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        group = QtCore.QParallelAnimationGroup(target)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(lambda: target.setGraphicsEffect(None))
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _handle_apply(self, tweak: Tweak) -> None:
        self._toast_manager.show_toast("Work in progress...", tone="neutral")
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
        if result.success:
            self._toast_manager.show_toast("Applied tweak successfully!", tone="success")
            if result.tweak and result.tweak.post_message:
                self._toast_manager.show_toast(result.tweak.post_message, tone="neutral")
            if result.tweak and result.tweak.explorer_notice:
                self._prompt_restart_explorer()
        else:
            self._toast_manager.show_toast(result.message, tone="error")

    def _handle_restore(self, tweak: Tweak) -> None:
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Select registry backup",
            str(Path("backups")),
            "Registry Files (*.reg);;All Files (*)",
        )
        if not file_path:
            return

        def task() -> str:
            from tweaks import restore_backup_file

            restore_backup_file(Path(file_path))
            return f"Restored backup for {tweak.label}."

        self._toast_manager.show_toast("Work in progress...", tone="neutral")
        self._start_task(task, success_tone="success")

    def _prompt_restart_explorer(self) -> None:
        prompt = QtWidgets.QMessageBox(self)
        prompt.setWindowTitle(APP_TITLE)
        prompt.setText("Sign out/in or restart Explorer may be required.")
        prompt.setInformativeText("Restart Explorer now?")
        prompt.setStandardButtons(QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if prompt.exec() == QtWidgets.QMessageBox.Yes:
            try:
                restart_explorer()
            except RuntimeError as exc:
                self._toast_manager.show_toast(str(exc), tone="error")

    def _start_task(self, task: Callable[[], str], success_tone: str = "success") -> None:
        worker = TaskWorker(task)
        thread = QtCore.QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(lambda result: self._handle_task_result(result, success_tone))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def _handle_task_result(self, result: TaskResult, success_tone: str) -> None:
        if result.success:
            self._toast_manager.show_toast(result.message, tone=success_tone)
        else:
            self._toast_manager.show_toast(result.message, tone="error")

    def _handle_clean_temp(self) -> None:
        self._toast_manager.show_toast("Work in progress...", tone="neutral")

        def task() -> str:
            result = clean_temp_files()
            return f"Temp cleanup complete. Deleted {result.deleted} items, skipped {result.skipped}."

        self._start_task(task, success_tone="success")

    def _handle_clean_roblox(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            self,
            APP_TITLE,
            "Delete Roblox cache folders and temp files?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
        )
        if confirm != QtWidgets.QMessageBox.Yes:
            return

        self._toast_manager.show_toast("Work in progress...", tone="neutral")

        def task() -> str:
            cleanup_roblox()
            return "Cleanup complete. If you still have issues, restart your PC and sign in again."

        self._start_task(task, success_tone="neutral")

    def _pick_main_color(self) -> None:
        dialog = ColorPickerDialog("Main color", self._main_color, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._main_color = dialog.color()
            self._main_color_button.set_color(self._main_color)
            self.update()

    def _pick_glow_color(self) -> None:
        dialog = ColorPickerDialog("Glow color", self._accent, self)
        if dialog.exec() == QtWidgets.QDialog.Accepted:
            self._accent = dialog.color()
            self._glow_color_button.set_color(self._accent)
            self._toast_manager.set_accent(self._accent)
            self._blob.set_color(self._accent)
            self._render_tweaks()

    def _update_speed(self, value: int) -> None:
        speed = value / 100
        self._animation.speed = speed
        self._speed_value.setText(f"{speed:.1f}x")

    def _save_preset(self) -> None:
        name = self._preset_name.text().strip()
        if not name:
            self._toast_manager.show_toast("Enter a preset name.", tone="error")
            return
        preset = ThemePreset(
            name=name,
            main_color=self._main_color.name(),
            glow_color=self._accent.name(),
            animation_speed=self._animation.speed,
        )
        self._presets = [p for p in self._presets if p.name.lower() != name.lower()]
        self._presets.append(preset)
        save_presets(self._presets)
        self._preset_name.clear()
        self._render_presets()
        self._toast_manager.show_toast("Preset saved.", tone="success")

    def _apply_preset(self, preset: ThemePreset) -> None:
        self._main_color = QtGui.QColor(preset.main_color)
        self._accent = QtGui.QColor(preset.glow_color)
        self._animation.speed = preset.animation_speed
        self._speed_slider.setValue(int(self._animation.speed * 100))
        self._speed_value.setText(f"{self._animation.speed:.1f}x")
        self._main_color_button.set_color(self._main_color)
        self._glow_color_button.set_color(self._accent)
        self._toast_manager.set_accent(self._accent)
        self._blob.set_color(self._accent)
        self._render_tweaks()
        self.update()
        self._toast_manager.show_toast(f"Preset '{preset.name}' applied.", tone="success")

    def _delete_preset(self, preset: ThemePreset) -> None:
        self._presets = [p for p in self._presets if p.name != preset.name]
        save_presets(self._presets)
        self._render_presets()
        self._toast_manager.show_toast("Preset deleted.", tone="neutral")

    def _start_intro_animation(self) -> None:
        self.setWindowOpacity(1.0)
        geo = self.geometry()
        start_pos = QtCore.QPoint(geo.x(), geo.y() + 20)
        move = QtCore.QPropertyAnimation(self, b"pos")
        move.setDuration(self._animation.scale(240))
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
