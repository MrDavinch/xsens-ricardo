import sys
import threading
import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from xdpchandler import *
import movelladot_pc_sdk

# ==========================================================
# Quaternion utilities
# ==========================================================
def quat_to_matrix(q):
    w, x, y, z = q
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w),     2*(x*z + y*w)],
        [2*(x*y + z*w),     1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w),     2*(y*z + x*w),     1 - 2*(x*x + y*y)]
    ])

# ==========================================================
# Shared state
# ==========================================================
lock = threading.Lock()

current_quat = np.array([1.,0.,0.,0.])
pos = np.zeros(3)
vel = np.zeros(3)
trajectory = []

last_ts = None

# ==========================================================
# ZUPT parameters
# ==========================================================
ACC_THR = 0.15      # m/s²
GYR_THR = 0.05      # rad/s
G = 9.81

# ==========================================================
# Sensor thread
# ==========================================================
def sensor_loop():
    global current_quat, pos, vel, last_ts

    xdpcHandler = XdpcHandler()
    if not xdpcHandler.initialize():
        return

    xdpcHandler.scanForDots()
    xdpcHandler.connectDots()

    if len(xdpcHandler.connectedDots()) == 0:
        return

    device = xdpcHandler.connectedDots()[0]
    print("Using device:", device.bluetoothAddress())

    device.startMeasurement(
        movelladot_pc_sdk.XsPayloadMode_CustomMode5
    )

    while True:
        if xdpcHandler.realtime_queue.empty():
            continue

        d = xdpcHandler.realtime_queue.get()
        ts = d.get("timestamp", None)
        if ts is None:
            continue

        if last_ts is None:
            last_ts = ts
            continue

        dt = (ts - last_ts) / 1e6
        last_ts = ts
        if dt <= 0 or dt > 0.1:
            continue

        q = np.array([
            d.get("qw",1.0),
            d.get("qx",0.0),
            d.get("qy",0.0),
            d.get("qz",0.0)
        ])
        q /= np.linalg.norm(q)

        acc = np.array([
            d.get("ax",0.0),
            d.get("ay",0.0),
            d.get("az",0.0)
        ])

        gyr = np.array([
            d.get("gx",0.0),
            d.get("gy",0.0),
            d.get("gz",0.0)
        ])

        # Rotate acceleration to world frame
        R = quat_to_matrix(q)
        acc_world = R @ acc - np.array([0,0,G])

        # =========================
        # ZUPT DETECTION
        # =========================
        zupt = (
            abs(np.linalg.norm(acc) - G) < ACC_THR and
            np.linalg.norm(gyr) < GYR_THR
        )

        if zupt:
            vel[:] = 0.0
        else:
            vel += acc_world * dt
            pos += vel * dt

        with lock:
            current_quat = q
            trajectory.append(pos.copy())
            if len(trajectory) > 2000:
                trajectory.pop(0)

# ==========================================================
# Qt + OpenGL
# ==========================================================
app = QApplication(sys.argv)

view = gl.GLViewWidget()
view.setWindowTitle("Movella DOT – 3D Trajectory (ZUPT)")
view.setCameraPosition(distance=4)
view.show()

grid = gl.GLGridItem()
grid.scale(1,1,1)
view.addItem(grid)

# Trajectory
traj_line = gl.GLLinePlotItem(
    pos=np.zeros((1,3)),
    color=(1,0,0,1),
    width=2,
    antialias=True
)
view.addItem(traj_line)

# ==========================================================
# Update loop
# ==========================================================
def update():
    with lock:
        traj = np.array(trajectory)
    if len(traj) > 1:
        traj_line.setData(pos=traj)

timer = QTimer()
timer.timeout.connect(update)
timer.start(16)

threading.Thread(target=sensor_loop, daemon=True).start()

sys.exit(app.exec_())
