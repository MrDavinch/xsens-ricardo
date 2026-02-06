from xdpchandler import *
import movelladot_pc_sdk
import pandas as pd
import sys
import threading
import queue
from collections import deque
import math

import pyqtgraph as pg
from pyqtgraph.Qt import QtWidgets, QtCore

# =========================================
# Conversión quaternion -> Euler
# =========================================
def quaternion_to_euler(qw, qx, qy, qz):
    sinr_cosp = 2 * (qw * qx + qy * qz)
    cosr_cosp = 1 - 2 * (qx*qx + qy*qy)
    roll = math.atan2(sinr_cosp, cosr_cosp)

    sinp = 2 * (qw*qy - qz*qx)
    if abs(sinp) >= 1:
        pitch = math.copysign(math.pi/2, sinp)
    else:
        pitch = math.asin(sinp)

    siny_cosp = 2 * (qw*qz + qx*qy)
    cosy_cosp = 1 - 2 * (qy*qy + qz*qz)
    yaw = math.atan2(siny_cosp, cosy_cosp)

    return math.degrees(yaw), math.degrees(pitch), math.degrees(roll)

# =========================================
# Realtime plot class
# =========================================
class RealtimePlot(QtWidgets.QWidget):
    def __init__(self, plot_queue):
        super().__init__()
        self.plot_queue = plot_queue
        self.window = 200  # muestras visibles

        # Deques para datos
        self.qw_data = deque(maxlen=self.window)
        self.qx_data = deque(maxlen=self.window)
        self.qy_data = deque(maxlen=self.window)
        self.qz_data = deque(maxlen=self.window)

        self.yaw_data = deque(maxlen=self.window)
        self.pitch_data = deque(maxlen=self.window)
        self.roll_data = deque(maxlen=self.window)

        self.init_ui()

        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(30)

    def init_ui(self):
        self.setWindowTitle("Quaternion y Euler en tiempo real")
        layout = QtWidgets.QVBoxLayout()

        # Subplot 1: Quaternion
        self.plot_q = pg.PlotWidget(title="Quaternion")
        self.plot_q.addLegend()
        self.plot_q.showGrid(x=True, y=True)
        self.curve_qw = self.plot_q.plot(pen="r", name="qw")
        self.curve_qx = self.plot_q.plot(pen="g", name="qx")
        self.curve_qy = self.plot_q.plot(pen="b", name="qy")
        self.curve_qz = self.plot_q.plot(pen="y", name="qz")

        # Subplot 2: Euler
        self.plot_e = pg.PlotWidget(title="Euler (Yaw, Pitch, Roll)")
        self.plot_e.addLegend()
        self.plot_e.showGrid(x=True, y=True)
        self.curve_yaw = self.plot_e.plot(pen="r", name="Yaw")
        self.curve_pitch = self.plot_e.plot(pen="g", name="Pitch")
        self.curve_roll = self.plot_e.plot(pen="b", name="Roll")

        layout.addWidget(self.plot_q)
        layout.addWidget(self.plot_e)
        self.setLayout(layout)
        self.resize(900, 600)

    def update_plot(self):
        updated = False
        while not self.plot_queue.empty():
            d = self.plot_queue.get()
            qw, qx, qy, qz = d["qw"], d["qx"], d["qy"], d["qz"]
            yaw, pitch, roll = quaternion_to_euler(qw, qx, qy, qz)

            self.qw_data.append(qw)
            self.qx_data.append(qx)
            self.qy_data.append(qy)
            self.qz_data.append(qz)

            self.yaw_data.append(yaw)
            self.pitch_data.append(pitch)
            self.roll_data.append(roll)

            updated = True

        if not updated:
            return

        x = range(len(self.qw_data))

        # Actualizar plots
        self.curve_qw.setData(x, self.qw_data)
        self.curve_qx.setData(x, self.qx_data)
        self.curve_qy.setData(x, self.qy_data)
        self.curve_qz.setData(x, self.qz_data)

        self.curve_yaw.setData(x, self.yaw_data)
        self.curve_pitch.setData(x, self.pitch_data)
        self.curve_roll.setData(x, self.roll_data)

        # Auto escala Y
        all_q = list(self.qw_data) + list(self.qx_data) + list(self.qy_data) + list(self.qz_data)
        ymin_q, ymax_q = min(all_q), max(all_q)
        margin_q = max((ymax_q - ymin_q) * 0.1, 0.01)
        self.plot_q.setYRange(ymin_q - margin_q, ymax_q + margin_q, padding=0)
        self.plot_q.setXRange(0, self.window, padding=0)

        all_e = list(self.yaw_data) + list(self.pitch_data) + list(self.roll_data)
        ymin_e, ymax_e = min(all_e), max(all_e)
        margin_e = max((ymax_e - ymin_e) * 0.1, 0.01)
        self.plot_e.setYRange(ymin_e - margin_e, ymax_e + margin_e, padding=0)
        self.plot_e.setXRange(0, self.window, padding=0)

# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    xdpcHandler = XdpcHandler()
    if not xdpcHandler.initialize():
        sys.exit(-1)

    xdpcHandler.scanForDots()
    if len(xdpcHandler.detectedDots()) == 0:
        print("No Movella DOT device(s) found.")
        sys.exit(-1)

    xdpcHandler.connectDots()
    if len(xdpcHandler.connectedDots()) == 0:
        print("Could not connect to any Movella DOT device(s).")
        sys.exit(-1)

    device = xdpcHandler.connectedDots()[0]
    print("Using device:", device.bluetoothAddress())
    if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_CustomMode5):
        print("Failed to start measurement")
        sys.exit(-1)

    data_log = []
    last_ts = None
    plot_queue = queue.Queue(maxsize=1000)

    # --- QT APP ---
    app = QtWidgets.QApplication(sys.argv)
    plotter = RealtimePlot(plot_queue)
    plotter.show()

    # =========================================
    # DATA ACQUISITION THREAD
    # =========================================
    def acquire_data():
        global last_ts
        while True:
            if not xdpcHandler.realtime_queue.empty():
                d = xdpcHandler.realtime_queue.get()

                if last_ts:
                    dt = (d["timestamp"] - last_ts) / 1e6
                else:
                    dt = 0
                last_ts = d["timestamp"]

                row = {
                    "timestamp": d.get("timestamp", 0),
                    "dt": dt,
                    "qw": d.get("qw", 0.0),
                    "qx": d.get("qx", 0.0),
                    "qy": d.get("qy", 0.0),
                    "qz": d.get("qz", 0.0),
                }
                data_log.append(row)
                try:
                    plot_queue.put_nowait(row)
                except queue.Full:
                    pass

    acq_thread = threading.Thread(target=acquire_data, daemon=True)
    acq_thread.start()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        df = pd.DataFrame(data_log)
        df.to_csv("movella_dot_data.csv", index=False)
        print("Datos guardados")
