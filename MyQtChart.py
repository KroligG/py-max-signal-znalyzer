import bisect

from PyQt5.QtChart import QChart
from PyQt5.QtChart import QChartView
from PyQt5.QtChart import QLineSeries
from PyQt5.QtChart import QValueAxis
from PyQt5.QtCore import QPoint
from PyQt5.QtCore import QSize
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter


class MyChartView(QChartView):
    def __init__(self, series: QLineSeries, title: str, xTitle: str, yTitle: str,
                 minimumSize=QSize(400, 400), y_range=None,
                 allowZoom=True, allowPan=True, niceNumbers=True, showPoints=True, *args):
        super().__init__(*args)

        self.allowZoom = allowZoom
        self.allowPan = allowPan
        self.niceNumbers = niceNumbers
        self.showPoints = showPoints

        self.guidesEnabled = True
        self.coords = QPoint(0, 0)

        if y_range:
            self.y_range = y_range
            self.y_range_fixed = True
        else:
            self.y_range_fixed = False

        self.setRubberBand(QChartView.HorizontalRubberBand)

        chart = QChart()
        # chart.setTitle(title)

        axisX = QValueAxis(chart)
        # axisX.setTitleText(xTitle)
        axisX.setMinorTickCount(1)
        axisX.setTickCount(20)
        chart.setAxisX(axisX)

        axisY = QValueAxis(chart)
        # axisY.setTitleText(yTitle)
        axisY.setTickCount(10)
        chart.setAxisY(axisY)

        chart.legend().hide()
        # chart.legend().setAlignment(Qt.AlignBottom)

        self.setChart(chart)

        self.set_series(series)

        if minimumSize:
            self.setMinimumSize(minimumSize)
        self.setRenderHint(QPainter.Antialiasing)

        if self.allowPan:
            self.pan = Pan(self)

        self.keyPressActions = {}
        if self.allowZoom:
            self.keyPressActions[Qt.Key_Plus] = self.zoom_in
            self.keyPressActions[Qt.Key_Minus] = self.zoom_out
            self.keyPressActions[Qt.Key_Space] = self.zoom_reset
        if self.allowPan:
            self.keyPressActions[Qt.Key_Left] = lambda e: self.chart().scroll(-10, 0)
            self.keyPressActions[Qt.Key_Right] = lambda e: self.chart().scroll(10, 0)
            self.keyPressActions[Qt.Key_Up] = lambda e: self.chart().scroll(0, 10)
            self.keyPressActions[Qt.Key_Down] = lambda e: self.chart().scroll(0, -10)

    def zoom_in(self, e):
        aX = self.chart().axisX()
        d = (aX.max() - aX.min()) * 0.1
        aX.setRange(aX.min() + d, aX.max() - d)

    def zoom_out(self, e):
        aX = self.chart().axisX()
        d = (aX.max() - aX.min()) * 0.1
        aX.setRange(aX.min() - d, aX.max() + d)

    def zoom_reset(self, e):
        aX = self.chart().axisX()
        x_points = [p.x() for s in self.chart().series() for p in s.pointsVector()]
        aX.setRange(min(x_points), max(x_points))

    def update_range(self, series: QLineSeries):
        x_y_points = list(zip(*((e.x(), e.y()) for e in series.pointsVector())))

        self.x_range = min(x_y_points[0]), max(x_y_points[0])
        self.chart().axisX().setRange(*self.x_range)

        if not self.y_range_fixed:
            self.y_range = min(x_y_points[1]), max(x_y_points[1])
        self.chart().axisY().setRange(*self.y_range)

    def set_series(self, series: QLineSeries):
        self.chart().removeAllSeries()

        if series:
            self.add_series(series)

    def add_series(self, series: QLineSeries):
        self.chart().addSeries(series)

        self.update_range(series)

        if self.showPoints:
            series.setPointLabelsClipping(False)
            series.hovered.connect(lambda p, s: series.setPointLabelsVisible(s))

        axis_x = self.chart().axisX()
        axis_y = self.chart().axisY()

        self.chart().setAxisX(axis_x, series)
        self.chart().setAxisY(axis_y, series)
        self.chart().axisY().applyNiceNumbers()

    def drawForeground(self, painter: QPainter, rect):
        if self.guidesEnabled:
            rect = self.chart().plotArea()

            text = []
            for serie in self.chart().series():
                pointer_coords = self.chart().mapToValue(self.coords, serie)
                x_y_points = list(zip(*((e.x(), e.y()) for e in serie.pointsVector())))
                point_ind = bisect.bisect_left(x_y_points[0], pointer_coords.x())
                point = serie.at(point_ind - 1 if point_ind else 0)
                text.append("%f x %f" % (point.x(), point.y()))
            painter.drawText(70, 27, ', '.join(text))
            painter.setClipRect(rect)
            # painter.setPen(self.guidePen)
            painter.drawLine(self.coords.x(), rect.top(), self.coords.x(), rect.bottom())

    def mouseMoveEvent(self, event):
        self.coords = event.pos()
        self.chart().scene().invalidate()
        super().mouseMoveEvent(event)

    # def mousePressEvent(self, event):
    #     if event.button() == Qt.LeftButton and self.allowPan:
    #         self.pan.start(event)
    #     else:
    #         super().mousePressEvent(event)
    #
    # def mouseReleaseEvent(self, event):
    #     if event.button() == Qt.LeftButton and self.allowPan:
    #         self.pan.end(event)
    #     else:
    #         super().mouseReleaseEvent(event)
    #
    # def mouseMoveEvent(self, event):
    #     if self.allowPan and self.pan.active:
    #         dist = self.pan.move(event)
    #         self.chart().scroll(dist.x(), 0) #-dist.y()
    #         # alternative. keeps nice numbers, but doesnt follow mouse exactly
    #         # axis_x = self.chart().axisX()
    #         # axis_y = self.chart().axisY()
    #         # axis_x.setRange(axis_x.min() + dist.x(), axis_x.max() + dist.x())
    #         # axis_y.setRange(axis_y.min() - dist.y(), axis_y.max() - dist.y())
    #     else:
    #         super().mouseMoveEvent(event)

    # def wheelEvent(self, event: QWheelEvent):
    #     if self.allowZoom:
    #         if event.angleDelta().y() > 0:
    #             self.chart().zoomIn()
    #         else:
    #             self.chart().zoomOut()
    #     else:
    #         super().wheelEvent(event)

    def keyPressEvent(self, event):
        self.keyPressActions.get(event.key(), super().keyPressEvent)(event)


class Pan:
    def __init__(self, widget):
        self.active = False
        self.startX = 0
        self.startY = 0
        self.widget = widget

    def start(self, event):
        self.active = True
        self.startX = event.x()
        self.startY = event.y()
        self.widget.setCursor(Qt.ClosedHandCursor)

    def move(self, event):
        dist = QPoint(self.startX - event.x(), self.startY - event.y())
        self.startX = event.x()
        self.startY = event.y()
        return dist

    def end(self, event):
        self.active = False
        self.widget.setCursor(Qt.ArrowCursor)
