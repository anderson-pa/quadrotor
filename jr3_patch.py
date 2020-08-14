import asyncio
import os
import sys

import pandas as pd

from PySide2.QtWidgets import (QPushButton, QLabel, QHBoxLayout, QVBoxLayout,
                               QFrame, QGridLayout,
                               QSpinBox, QWidget)
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas,
    NavigationToolbar2QT as NavigationToolBar)
from matplotlib.figure import Figure
from patchbay.patch import BaseUiPatch

base_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, base_dir)

from jr3 import Jr3

j = Jr3()


class Patch(BaseUiPatch):
    def __init__(self, parent):
        self._parent = parent
        self.widgets = {}

        self.data = pd.DataFrame(columns=['fx', 'fy', 'fz'])
        self.task = None

        self.ui = self.make_ui()

    def make_ui(self):
        """Create and lay out UI elements."""

        filter = QSpinBox()
        filter.setRange(1, 6)
        self.widgets['filter'] = filter

        btn_start = QPushButton()
        btn_start.setText('Start')
        btn_start.clicked.connect(self.run)
        self.widgets['btn_start'] = btn_start

        side_panel = QGridLayout()
        side_panel.setColumnStretch(0, 0)
        side_panel.setColumnStretch(1, 1)
        side_panel.setColumnStretch(2, 1)
        side_panel.setRowStretch(6, 1)  # shove everything to the top

        side_panel.addWidget(QLabel('<h2>Controls</h2>'), 0, 0, 1, 2)
        side_panel.addWidget(QLabel('Filter:'), 1, 0)
        side_panel.addWidget(filter, 1, 1)
        side_panel.addWidget(btn_start, 2, 0, 1, 2)

        graph = FigureCanvas(Figure(tight_layout=True))
        graph_toolbar = NavigationToolBar(graph, None)
        graph_toolbar.setObjectName('GraphToolBar')
        self.widgets['graph'] = graph
        axis = graph.figure.subplots()
        axis.grid()
        axis.set_xlim(0, 100)
        axis.set_ylim(0, 10)

        self.widgets['axis'] = axis

        vbox = QVBoxLayout()
        vbox.addWidget(graph)
        vbox.addWidget(graph_toolbar)

        hbox = QHBoxLayout()
        hbox.addLayout(side_panel)
        hbox.addLayout(vbox, 1)

        main_widget = QFrame()
        main_widget.setLayout(hbox)

        return main_widget

    def run(self):
        if self.task is None:
            self.widgets['btn_start'].setText('Stop')
            self.data = self.data[0:0]  # clear all data
            axis = self.widgets['axis']
            if axis.lines:
                axis.lines = []
                axis.set_prop_cycle(None)

            loop = asyncio.get_event_loop()
            filter_num = self.widgets['filter'].value()
            self.task = loop.create_task(self.show_data(filter_num))
        else:
            self.task.cancel()
            self.widgets['btn_start'].setText('Start')
            out_path = os.path.expanduser('~/Desktop/jr3_data.csv')
            self.data.to_csv(out_path)
            self.task = None

    async def show_data(self, filter=1):
        # self.widgets['btn_start'].setEnabled(False)
        graph = self.widgets['graph']
        axis = self.widgets['axis']

        for name in ['fx', 'fy', 'fz']:
            axis.plot([], [], '.-', label=name)
        axis.legend(loc='upper left')
        fx_line, fy_line, fz_line = axis.lines[:3]

        t0 = j.counters[filter - 1]
        t_cycles = 0
        clock = 0
        while True:
            last_clock = clock
            clock, force_array = j.read_clocked_forces(filter)

            if clock < last_clock:
                t_cycles += 1

            ds = pd.Series(force_array._asdict(),
                           name=(clock - t0 + 2 ** 16 * t_cycles) / (
                                       8e3 / 4 ** (filter - 1)))
            self.data = self.data.append(ds)

            for line_name in ['fx', 'fy', 'fz']:
                locals()[f'{line_name}_line'].set_data(self.data.index,
                                                       self.data[line_name])
            axis.relim()
            axis.autoscale()
            graph.draw()

            try:
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break

        # self.widgets['btn_start'].setEnabled(True)

    def stop(self):
        pass

    def close(self):
        self.stop()
