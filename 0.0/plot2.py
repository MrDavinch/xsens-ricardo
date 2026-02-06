from xdpchandler import *
import movelladot_pc_sdk
import sys
import threading
import queue
from collections import deque
import math
import numpy as np

from pyqtgraph.Qt import QtWidgets, QtCore
import pyqtgraph as pg
import pyqtgraph.opengl as gl

# =========================================
# Funciones auxiliares
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

def quaternion_to_matrix(qw, qx, qy, qz):
    xx = qx*qx; yy = qy*qy; zz = qz*qz
    xy = qx*qy; xz = qx*qz; yz = qy*qz
    wx = qw*qx; wy = qw*qy; wz = qw*qz

    return np.array([
        [1-2*(yy+zz), 2*(xy - wz), 2*(xz + wy)],
        [2*(xy + wz), 1-2*(xx+zz), 2*(yz - wx)],
        [2*(xz - wy), 2*(yz + wx), 1-2*(xx+yy)]
    ])

# =========================================
# Dashboard widget
# =========================================
class DOTDashboard(QtWidgets.QWidget):
    def __init__(self, plot_queue):
        super().__init__()
        self.plot_queue = plot_queue
        self.window = 200

        # Deques para señales
        self.ax_data = deque(maxlen=self.window)
        self.ay_data = deque(maxlen=self.window)
        self.az_data = deque(maxlen=self.window)

        self.gx_data = deque(maxlen=self.window)
        self.gy_data = deque(maxlen=self.window)
        self.gz_data = deque(maxlen=self.window)

        self.yaw_data = deque(maxlen=self.window)
        self.pitch_data = deque(maxlen=self.window)
        self.roll_data = deque(maxlen=self.window)

        self.last_matrix = np.eye(3)
        self.init_ui()

        # Timer de actualización ~60Hz
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_dashboard)
        self.timer.start(16)

    def init_ui(self):
        self.setWindowTitle("Movella DOT Dashboard 3D + Signals")
        layout = QtWidgets.QVBoxLayout()

        # Cubo 3D
        self.view3d = gl.GLViewWidget()
        self.view3d.opts['distance'] = 4
        layout.addWidget(self.view3d)

        verts = np.array([
            [-0.5,-0.5,-0.5],[0.5,-0.5,-0.5],[0.5,0.5,-0.5],[-0.5,0.5,-0.5],
            [-0.5,-0.5,0.5],[0.5,-0.5,0.5],[0.5,0.5,0.5],[-0.5,0.5,0.5]
        ])
        faces = np.array([
            [0,1,2],[0,2,3],[4,5,6],[4,6,7],
            [0,1,5],[0,5,4],[2,3,7],[2,7,6],
            [1,2,6],[1,6,5],[0,3,7],[0,7,4]
        ])
        colors = np.array([[1,0,0,0.3] for i in range(len(faces))])

        self.cube_verts = verts
        self.cube_faces = faces
        self.cube_colors = colors

        self.mesh = gl.GLMeshItem(vertexes=verts, faces=faces, faceColors=colors, smooth=False, drawEdges=True)
        self.view3d.addItem(self.mesh)

        # Plots 2D
        self.plot_acc = pg.PlotWidget(title="Acceleration")
        self.plot_acc.addLegend(); self.plot_acc.showGrid(x=True,y=True)
        self.curve_ax = self.plot_acc.plot(pen='r', name='Ax')
        self.curve_ay = self.plot_acc.plot(pen='g', name='Ay')
        self.curve_az = self.plot_acc.plot(pen='b', name='Az')
        layout.addWidget(self.plot_acc)

        self.plot_gyro = pg.PlotWidget(title="Gyroscope")
        self.plot_gyro.addLegend(); self.plot_gyro.showGrid(x=True,y=True)
        self.curve_gx = self.plot_gyro.plot(pen='r', name='Gx')
        self.curve_gy = self.plot_gyro.plot(pen='g', name='Gy')
        self.curve_gz = self.plot_gyro.plot(pen='b', name='Gz')
        layout.addWidget(self.plot_gyro)

        self.plot_euler = pg.PlotWidget(title="Euler Angles (Yaw, Pitch, Roll)")
        self.plot_euler.addLegend(); self.plot_euler.showGrid(x=True,y=True)
        self.curve_yaw = self.plot_euler.plot(pen='r', name='Yaw')
        self.curve_pitch = self.plot_euler.plot(pen='g', name='Pitch')
        self.curve_roll = self.plot_euler.plot(pen='b', name='Roll')
        layout.addWidget(self.plot_euler)

        self.setLayout(layout)
        self.resize(1000, 900)

    def update_dashboard(self):
        updated = False
        while not self.plot_queue.empty():
            d = self.plot_queue.get()

            ax, ay, az = d.get("ax",0), d.get("ay",0), d.get("az",0)
            gx, gy, gz = d.get("gx",0), d.get("gy",0), d.get("gz",0)
            qw, qx, qy, qz = d.get("qw",0), d.get("qx",0), d.get("qy",0), d.get("qz",0)
            yaw, pitch, roll = quaternion_to_euler(qw,qx,qy,qz)

            self.ax_data.append(ax); self.ay_data.append(ay); self.az_data.append(az)
            self.gx_data.append(gx); self.gy_data.append(gy); self.gz_data.append(gz)
            self.yaw_data.append(yaw); self.pitch_data.append(pitch); self.roll_data.append(roll)

            self.last_matrix = quaternion_to_matrix(qw,qx,qy,qz)
            updated = True

        if not updated:
            return

        # Actualizar cubo 3D
        verts_centered = self.cube_verts - np.mean(self.cube_verts, axis=0)
        rotated = verts_centered @ self.last_matrix.T
        self.mesh.setMeshData(vertexes=rotated + np.mean(self.cube_verts, axis=0),
                              faces=self.cube_faces,
                              faceColors=self.cube_colors)

        x = range(len(self.ax_data))
        self.curve_ax.setData(x,self.ax_data)
        self.curve_ay.setData(x,self.ay_data)
        self.curve_az.setData(x,self.az_data)

        self.curve_gx.setData(x,self.gx_data)
        self.curve_gy.setData(x,self.gy_data)
        self.curve_gz.setData(x,self.gz_data)

        self.curve_yaw.setData(x,self.yaw_data)
        self.curve_pitch.setData(x,self.pitch_data)
        self.curve_roll.setData(x,self.roll_data)

        # Auto-scale Y
        def autoscale(curves):
            y_all = []
            for data in curves:
                y_all += list(data)
            ymin, ymax = min(y_all), max(y_all)
            margin = max((ymax - ymin)*0.1, 0.01)
            return ymin-margin, ymax+margin

        self.plot_acc.setYRange(*autoscale([self.ax_data,self.ay_data,self.az_data]), padding=0)
        self.plot_gyro.setYRange(*autoscale([self.gx_data,self.gy_data,self.gz_data]), padding=0)
        self.plot_euler.setYRange(*autoscale([self.yaw_data,self.pitch_data,self.roll_data]), padding=0)

        self.plot_acc.setXRange(0,self.window,padding=0)
        self.plot_gyro.setXRange(0,self.window,padding=0)
        self.plot_euler.setXRange(0,self.window,padding=0)

# =========================================
# MAIN
# =========================================
if __name__ == "__main__":
    xdpcHandler = XdpcHandler()
    if not xdpcHandler.initialize(): sys.exit(-1)
    xdpcHandler.scanForDots()
    if len(xdpcHandler.detectedDots()) == 0: sys.exit(-1)
    xdpcHandler.connectDots()
    if len(xdpcHandler.connectedDots()) == 0: sys.exit(-1)

    device = xdpcHandler.connectedDots()[0]
    if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_CustomMode5):
        sys.exit(-1)

    plot_queue = queue.Queue(maxsize=500)  # Cola limitada para GUI
    data_log = []
    last_ts = None

    # Data acquisition thread
    def acquire_data():
        global last_ts
        while True:
            try:
                d = xdpcHandler.realtime_queue.get(timeout=0.01)
            except queue.Empty:
                continue

            if last_ts:
                dt = (d["timestamp"] - last_ts)/1e6
            else:
                dt = 0
            last_ts = d["timestamp"]

            row = {
                "timestamp": d.get("timestamp",0),
                "dt": dt,
                "ax": d.get("ax",0.0),
                "ay": d.get("ay",0.0),
                "az": d.get("az",0.0),
                "gx": d.get("gx",0.0),
                "gy": d.get("gy",0.0),
                "gz": d.get("gz",0.0),
                "qw": d.get("qw",0.0),
                "qx": d.get("qx",0.0),
                "qy": d.get("qy",0.0),
                "qz": d.get("qz",0.0)
            }

            data_log.append(row)

            # Evitar que la cola se llene y genere retrasos
            while True:
                try:
                    plot_queue.put_nowait(row)
                    break
                except queue.Full:
                    try:
                        plot_queue.get_nowait()
                    except queue.Empty:
                        break

    acq_thread = threading.Thread(target=acquire_data, daemon=True)
    acq_thread.start()

    # Run Qt Dashboard
    app = QtWidgets.QApplication(sys.argv)
    dashboard = DOTDashboard(plot_queue)
    dashboard.show()

    try:
        sys.exit(app.exec_())
    except KeyboardInterrupt:
        import pandas as pd
        df = pd.DataFrame(data_log)
        df.to_csv("movella_dot_dashboard.csv", index=False)
        print("Datos guardados")
