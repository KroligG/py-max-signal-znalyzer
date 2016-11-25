import math
import os
import sys

from PyQt5 import QtCore
from PyQt5.QtChart import QLineSeries
from PyQt5.QtCore import QLocale, QSize
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import QAction, QVBoxLayout, QScrollBar, QComboBox, QLabel, QMessageBox, QCheckBox, QScrollArea
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import QMainWindow
from PyQt5.QtWidgets import QWidget, QApplication

import MyQtChart
from tembr import TembrFile


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.initUI()

    def initUI(self):
        exitAction = QAction('&Exit', self)
        exitAction.setShortcut('Ctrl+Q')
        exitAction.setStatusTip('Exit application')
        exitAction.triggered.connect(self.close)

        openFile = QAction('Open', self)
        openFile.setShortcut('Ctrl+O')
        openFile.setStatusTip('Open Data File')
        openFile.triggered.connect(self.openDataFile)

        saveFile = QAction('Save', self)
        saveFile.setShortcut('Ctrl+S')
        saveFile.setStatusTip('Save Data File')
        saveFile.triggered.connect(self.saveDataFile)

        self.statusBar().showMessage('Ready.')

        self.toolbar = self.addToolBar('Toolbar')
        self.sample_size_select = QComboBox()
        self.sample_size_select.addItems([str(2 ** i) for i in range(8, 16)])
        self.toolbar.addWidget(QLabel("Sample Size: "))
        self.toolbar.addWidget(self.sample_size_select)

        showInfoAction = QAction('Show Info', self)
        showInfoAction.triggered.connect(self.show_info)
        self.toolbar.addAction(showInfoAction)

        show_fft_check = QCheckBox("Show FFT")
        show_fft_check.stateChanged.connect(lambda i: self.centralWidget().toggle_fft(i))
        self.toolbar.addWidget(show_fft_check)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu('&File')
        fileMenu.addAction(openFile)
        fileMenu.addAction(saveFile)
        fileMenu.addAction(exitAction)

        cw = CentralWidget(self)
        self.setCentralWidget(cw)

        # self.setGeometry(300, 300, 250, 150)
        geometry = QApplication.desktop().screenGeometry()
        self.setMaximumHeight(geometry.height() - 100)
        self.resize(1200, 300)
        self.setWindowTitle('Max Signal Analyzer')
        self.show()

    def show_info(self):
        msgBox = QMessageBox()
        msgBox.setWindowTitle("Info")
        msgBox.setText('\n\n'.join((str(f) for f in self.files)))
        msgBox.exec()

    def openDataFile(self):
        fnames = QFileDialog.getOpenFileNames(self, 'Open file', filter='Файл данных (*.bin);;Список файлов данных (*.txt)')[0]

        self.files = []

        def read_tembr(file_name):
            file = TembrFile(os.path.split(file_name)[1], open(file_name, 'rb').read())
            print(file)
            return file

        for file_name in fnames:
            if file_name.endswith(".bin"):
                self.files.append(read_tembr(file_name))
            else:
                (text_file_path, _) = os.path.split(file_name)
                for binary_name in open(file_name, 'r').readlines():
                    self.files.append(read_tembr(os.path.join(text_file_path, binary_name.strip())))

        self.centralWidget().repaintChartsEvent.emit()

        self.statusBar().showMessage('Data loaded.')

    def saveDataFile(self):
        fname = QFileDialog.getSaveFileName(self, 'Save file', filter='*.png')

        if fname[0]:
            central_widget = self.centralWidget()
            pixmap = QPixmap(central_widget.size())
            central_widget.render(pixmap)
            pixmap.save(fname[0])
            self.statusBar().showMessage('Image was saved successfully')

    def closeEvent(self, event):
        reply = QMessageBox.question(self, 'Confirm', "Are you sure to quit?",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes)
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.close()


class CentralWidget(QWidget):
    repaintChartsEvent = QtCore.pyqtSignal()

    def __init__(self, window):
        super().__init__()

        self.windowWidget = window

        self.repaintChartsEvent.connect(self.init_charts)

        grid = QVBoxLayout()
        self.setLayout(grid)

        self.fft = False

        self.windowWidget.sample_size_select.activated.connect(self.on_sample_size_changed)

    def toggle_fft(self, state):
        self.fft = bool(state)
        self.init_charts()

    def clear_widget(self):
        for i in reversed(range(self.layout().count())):
            self.layout().itemAt(i).widget().setParent(None)
        self.charts = []
        self.chart_descriptions = []

    def init_charts(self):
        self.clear_widget()

        self.current_sample = 0

        self.chart_scroll = QScrollBar(Qt.Horizontal)
        self.chart_scroll.valueChanged.connect(self.on_slider_changed)

        self.chart_area_scroll = QScrollArea(self)
        self.chart_area_scroll.setWidgetResizable(True)
        self.layout().addWidget(self.chart_area_scroll)

        self.chart_area_scroll_widget = QWidget()
        self.chart_area_scroll.setWidget(self.chart_area_scroll_widget)

        self.chart_area_scroll_widget.setLayout(QVBoxLayout())

        for tembrFile in self.windowWidget.files:
            self.add_chart(tembrFile)

        self.windowWidget.setGeometry(200, 40, 1200, 300 * len(self.charts))

        self.layout().addWidget(self.chart_scroll)

    def on_slider_changed(self, e):
        self.current_sample = e
        self.update_chart_points()
        self.update_chart_description()

    def on_sample_size_changed(self, i):
        for file in self.windowWidget.files:
            file.current_sample_size = 2 ** (i + 8)
        self.init_charts()

    def add_chart(self, tembrFile: TembrFile):
        series = QLineSeries()
        series.setName(tembrFile.name)
        # series.setUseOpenGL(True)

        if self.fft:
            series.append(tembrFile.fft(self.current_sample))
        else:
            series.append(tembrFile.get_qpoints_sample(self.current_sample))
        self.charts.append(MyQtChart.MyChartView(series, "Chart", "Time", "Value", minimumSize=QSize(1200, 300), y_range=(tembrFile.min, tembrFile.max),
                                                 allowZoom=True, allowPan=True, niceNumbers=True, showPoints=False))
        self.chart_descriptions.append(QLabel())
        self.chart_area_scroll_widget.layout().addWidget(self.chart_descriptions[-1])
        self.chart_area_scroll_widget.layout().addWidget(self.charts[-1])

        self.chart_scroll.setMaximum(tembrFile.sample_count - 1)
        self.windowWidget.sample_size_select.setCurrentIndex(math.log2(tembrFile.current_sample_size) - 8)

        self.update_chart_description()

    def update_chart_points(self):
        for chart, file in zip(self.charts, self.windowWidget.files):
            first_serie = chart.chart().series()[0]
            if self.fft:
                first_serie.replace(file.fft(self.current_sample))
            else:
                first_serie.replace(file.get_qpoints_sample(self.current_sample))
            chart.update_range(first_serie)

    def update_chart_description(self):
        for descr, file in zip(self.chart_descriptions, self.windowWidget.files):
            rms, amplitude = file.rms(self.current_sample), file.amplitude(self.current_sample)
            sample = file.get_points_sample(self.current_sample)
            descr.setText("Мин: %f, Макс: %f, СКЗ: %f, Амплитуда: %f, Пик фактор: %f" % (min(sample), max(sample), rms, amplitude, amplitude / rms))


if __name__ == '__main__':
    QLocale.setDefault(QLocale("en-US"))
    app = QApplication(sys.argv)
    ex = MainWindow()
    sys.exit(app.exec_())
