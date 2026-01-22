from __future__ import annotations

from PySide6 import QtCore, QtGui, QtWidgets


class LoadingSpinner(QtWidgets.QWidget):
    def __init__(self, accent: QtGui.QColor, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent = accent
        self._angle = 0
        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)
        self.setFixedSize(64, 64)

    def _tick(self) -> None:
        self._angle = (self._angle + 6) % 360
        self.update()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(6, 6, -6, -6)
        gradient = QtGui.QConicalGradient(rect.center(), -self._angle)
        gradient.setColorAt(0.0, QtGui.QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 30))
        gradient.setColorAt(0.4, QtGui.QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 220))
        gradient.setColorAt(1.0, QtGui.QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 40))

        pen = QtGui.QPen(QtGui.QBrush(gradient), 6)
        pen.setCapStyle(QtCore.Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)


class LoadingScreen(QtWidgets.QDialog):
    finished = QtCore.Signal()

    def __init__(
        self,
        app_title: str,
        accent: QtGui.QColor,
        base_color: QtGui.QColor,
        animation_speed: float = 1.0,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self._base = base_color
        self._speed = max(0.2, animation_speed)
        self.setWindowTitle(app_title)
        self.setWindowFlags(
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.Window
            | QtCore.Qt.WindowSystemMenuHint
        )
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        self.setModal(True)
        self.setFixedSize(520, 320)

        self._opacity_effect = QtWidgets.QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        top = QtWidgets.QHBoxLayout()
        top.addStretch()
        self._close_btn = QtWidgets.QPushButton("✕")
        self._close_btn.setFixedSize(32, 28)
        self._close_btn.setCursor(QtCore.Qt.PointingHandCursor)
        self._close_btn.setStyleSheet(
            "QPushButton {"
            "background: transparent;"
            "color: #e3e8f4;"
            "border: none;"
            "border-radius: 10px;"
            "font-size: 14px;"
            "}"
            "QPushButton:hover {"
            "background-color: rgba(125, 92, 255, 0.35);"
            "}"
        )
        self._close_btn.clicked.connect(self._close_and_quit)
        top.addWidget(self._close_btn)
        layout.addLayout(top)

        center = QtWidgets.QVBoxLayout()
        center.setSpacing(12)
        center.setAlignment(QtCore.Qt.AlignCenter)

        self._spinner = LoadingSpinner(self._accent)
        center.addWidget(self._spinner, alignment=QtCore.Qt.AlignCenter)

        title = QtWidgets.QLabel("Loading")
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet("color: #f5f7ff; font-size: 20px; font-weight: 600;")
        self._title_label = title
        self._title_effect = QtWidgets.QGraphicsOpacityEffect(self._title_label)
        self._title_label.setGraphicsEffect(self._title_effect)
        self._title_effect.setOpacity(1.0)
        center.addWidget(self._title_label)

        self._done_label = QtWidgets.QLabel("Finished loading")
        self._done_label.setAlignment(QtCore.Qt.AlignCenter)
        self._done_label.setStyleSheet("color: #e2e8f0; font-size: 16px; font-weight: 600;")
        self._done_effect = QtWidgets.QGraphicsOpacityEffect(self._done_label)
        self._done_label.setGraphicsEffect(self._done_effect)
        self._done_effect.setOpacity(0.0)
        center.addWidget(self._done_label)

        self._check_label = QtWidgets.QLabel("✓")
        self._check_label.setAlignment(QtCore.Qt.AlignCenter)
        self._check_label.setStyleSheet("color: #32d583; font-size: 18px; font-weight: 700;")
        self._check_effect = QtWidgets.QGraphicsOpacityEffect(self._check_label)
        self._check_label.setGraphicsEffect(self._check_effect)
        self._check_effect.setOpacity(0.0)
        center.addWidget(self._check_label)

        layout.addStretch()
        layout.addLayout(center)
        layout.addStretch()

        self._intro_animation()
        QtCore.QTimer.singleShot(int(1800 * self._speed), self._finish_loading)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self._close_and_quit()
        super().keyPressEvent(event)

    def _close_and_quit(self) -> None:
        QtWidgets.QApplication.quit()

    def _intro_animation(self) -> None:
        start_pos = self.pos() + QtCore.QPoint(0, 12)
        self.move(start_pos)

        fade = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity")
        fade.setDuration(int(420 * self._speed))
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        slide = QtCore.QPropertyAnimation(self, b"pos")
        slide.setDuration(int(420 * self._speed))
        slide.setStartValue(start_pos)
        slide.setEndValue(start_pos - QtCore.QPoint(0, 12))
        slide.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        group = QtCore.QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _finish_loading(self) -> None:
        crossfade = QtCore.QParallelAnimationGroup(self)

        fade_out = QtCore.QPropertyAnimation(self._title_effect, b"opacity")
        fade_out.setDuration(int(360 * self._speed))
        fade_out.setStartValue(1.0)
        fade_out.setEndValue(0.0)
        fade_out.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        fade_in = QtCore.QPropertyAnimation(self._done_effect, b"opacity")
        fade_in.setDuration(int(360 * self._speed))
        fade_in.setStartValue(0.0)
        fade_in.setEndValue(1.0)
        fade_in.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        check_in = QtCore.QPropertyAnimation(self._check_effect, b"opacity")
        check_in.setDuration(int(360 * self._speed))
        check_in.setStartValue(0.0)
        check_in.setEndValue(1.0)
        check_in.setEasingCurve(QtCore.QEasingCurve.OutCubic)

        crossfade.addAnimation(fade_out)
        crossfade.addAnimation(fade_in)
        crossfade.addAnimation(check_in)
        crossfade.finished.connect(self._outro_animation)
        crossfade.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _outro_animation(self) -> None:
        fade = QtCore.QPropertyAnimation(self._opacity_effect, b"opacity")
        fade.setDuration(int(520 * self._speed))
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QtCore.QEasingCurve.InCubic)

        slide = QtCore.QPropertyAnimation(self, b"pos")
        slide.setDuration(int(520 * self._speed))
        slide.setStartValue(self.pos())
        slide.setEndValue(self.pos() + QtCore.QPoint(0, 10))
        slide.setEasingCurve(QtCore.QEasingCurve.InCubic)

        group = QtCore.QParallelAnimationGroup(self)
        group.addAnimation(fade)
        group.addAnimation(slide)
        group.finished.connect(self._emit_finished)
        group.start(QtCore.QAbstractAnimation.DeleteWhenStopped)

    def _emit_finished(self) -> None:
        self.finished.emit()
        self.close()

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(1, 1, -1, -1)

        base = QtGui.QColor(self._base)
        darker = base.darker(135)
        lighter = base.lighter(130)
        gradient = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
        gradient.setColorAt(0.0, darker)
        gradient.setColorAt(1.0, lighter)
        painter.setBrush(gradient)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 22, 22)

        glow = QtGui.QRadialGradient(rect.center(), rect.width() * 0.5)
        glow.setColorAt(0.0, QtGui.QColor(self._accent.red(), self._accent.green(), self._accent.blue(), 90))
        glow.setColorAt(1.0, QtGui.QColor(0, 0, 0, 0))
        painter.setBrush(glow)
        painter.drawRoundedRect(rect, 22, 22)

        vignette = QtGui.QRadialGradient(rect.center(), rect.width() * 0.65)
        vignette.setColorAt(0.0, QtGui.QColor(0, 0, 0, 0))
        vignette.setColorAt(1.0, QtGui.QColor(0, 0, 0, 160))
        painter.setBrush(vignette)
        painter.drawRoundedRect(rect, 22, 22)

    def center_on_screen(self) -> None:
        screen = QtGui.QGuiApplication.primaryScreen()
        if not screen:
            return
        available = screen.availableGeometry()
        size = self.size()
        x = available.x() + (available.width() - size.width()) // 2
        y = available.y() + (available.height() - size.height()) // 2
        self.move(x, y)
