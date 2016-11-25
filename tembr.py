import array
import math
import statistics
import struct

import numpy
from PyQt5.QtCore import QPointF


class TembrFile:
    channel_count = 0  # Количество каналов: 4 байта, целое (Количество каналов по которым принимался сигнал)
    sample_size = 0  # Размер выборки на один канал: 4 байта, целое (число дискретных точек на один временной интервал приема данных (блок даных) N)
    spectral_lines = 0  # Количество спектральных линий: 4 байта, целое (меньше или равно N/2)
    cut_off_frequency = 0  # Частота среза: 4 байта, целое  (заданная частота среза ФНЧ при приеме данных)
    frequency_resolution = 0  # Частотное разрешение: 4 байта, вещественное (шаг по частоте между спектральными линиями при анализе, Гц )
    block_time = 0  # Время приёма блока данных: 4 байта, вещественное (время за которое принимался  блок данных, величина обратная частотному разрешению)
    total_time = 0  # Общее время приёма данных: 4 байта, целое  (время приема всей реализации в секундах)
    user_block_number = 0  # Количество принятых блоков (задано пользователем): 4 байта, целое (то что было задано пользователем при приеме данных)
    data_size = 0  # размер данных: 4 байта, целое (количество дискретных отсчетов в файле даных)
    systemBlockNumber = 0  # число принятых блоков(принято системой): 4 байта, целое (реально принятое число блоков)
    max = 0  # максимальное значение принятых данных: 4 байта, вещественное (максимальное значение  сигнала)
    min = 0  # минимальное значение принятых данных: 4 байта, вещественное (минимальное значение  сигнала)
    signal = []  # далее идут данные в формате 4 байта, вещественное число для одного дискретного значения сигнала.

    def __init__(self, name, bytes: bytes):
        self.name = name
        (self.channel_count,
         self.sample_size,
         self.spectral_lines,
         self.cut_off_frequency,
         self.frequency_resolution,
         self.block_time,
         self.total_time,
         self.user_block_number,
         self.data_size,
         self.systemBlockNumber,
         self.max,
         self.min) = struct.unpack_from("iiiiffiiiiff", bytes, offset=4)

        self.signal = array.array("f", bytes[52:])

        self.current_sample_size = self.sample_size

    @property
    def discretization_period(self):
        return 1.0 / (self.frequency_resolution * self.sample_size)

    @property
    def sample_count(self):
        return math.ceil(self.data_size / self.current_sample_size)

    def get_points_sample(self, sample_num):
        start_point = sample_num * self.current_sample_size
        return self.signal[start_point: start_point + self.current_sample_size]

    def get_qpoints_sample(self, sample_num):
        start_point = sample_num * self.current_sample_size
        discretization_period = self.discretization_period
        return [QPointF((start_point + i) * discretization_period, y) for i, y in enumerate(self.get_points_sample(sample_num))]

    def rms(self, sample_num):
        return math.sqrt(statistics.mean([x ** 2 for x in self.get_points_sample(sample_num)]))

    def amplitude(self, sample_num):
        p = self.get_points_sample(sample_num)
        return max(p) - min(p)

    def fft(self, sample_num):
        y = self.get_points_sample(sample_num)
        yf = numpy.fft.fft(y)
        T = self.discretization_period
        N = self.current_sample_size
        xf = numpy.linspace(0.0, 1.0 / (2.0 * T), N / 2)
        return [QPointF(x, 2.0 / N * abs(y)) for x, y in zip(xf, yf[:N // 2])]

    def __str__(self, *args, **kwargs):
        return '\n'.join([
            "Имя: %(name)s",
            "Количество каналов: %(channel_count)d",
            "Размер выборки на один канал: %(sample_size)d",
            "Количество спектральных линий: %(spectral_lines)d",
            "Частота среза: %(cut_off_frequency)d",
            "Частотное разрешение: %(frequency_resolution)f",
            "Время приёма блока данных: %(block_time)f",
            "Общее время приёма данных: %(total_time)d",
            "Количество принятых блоков (задано пользователем): %(user_block_number)d",
            "размер данных: %(data_size)d",
            "число принятых блоков(принято системой): %(systemBlockNumber)d",
            "максимальное значение принятых данных: %(max)f",
            "минимальное значение принятых данных: %(min)f",
        ]) % vars(self)
