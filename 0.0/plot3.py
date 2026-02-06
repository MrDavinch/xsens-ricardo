import sys
import threading
import numpy as np
import pyqtgraph.opengl as gl
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QTimer

from xdpchandler import *
import movelladot_pc_sdk

# ==========================================================
# Quaternion → Rotation Matrix
# ==========================================================
def quat_to_matrix(q):
    w, x, y, z = q
    return np.array([
        [1 - 2*(y*y + z*z), 2*(x*y - z*w),     2*(x*z + y*w)],
        [2*(x*y + z*w),     1 - 2*(x*x + z*z), 2*(y*z - x*w)],
        [2*(x*z - y*w),     2*(y*z + x*w),     1 - 2*(x*x + y*y)]
    ])

# ==========================================================
# Global quaternion (shared)
# ==========================================================
current_quat = np.array([1.0, 0.0, 0.0, 0.0])
lock = threading.Lock()

# ==========================================================
# Sensor Thread
# ==========================================================
def sensor_loop():
    global current_quat

    xdpcHandler = XdpcHandler()

    if not xdpcHandler.initialize():
        print("❌ XdpcHandler init failed")
        return

    xdpcHandler.scanForDots()

    if len(xdpcHandler.detectedDots()) == 0:
        print("❌ No DOT devices found")
        return

    xdpcHandler.connectDots()

    if len(xdpcHandler.connectedDots()) == 0:
        print("❌ DOT detected but NOT connected")
        return

    device = xdpcHandler.connectedDots()[0]
    print("✅ Using device:", device.bluetoothAddress())

    if not device.startMeasurement(
        movelladot_pc_sdk.XsPayloadMode_CustomMode5
    ):
        print("❌ Failed to start measurement")
        return

    print("📡 Streaming orientation...")

    while True:
        if not xdpcHandler.realtime_queue.empty():
            d = xdpcHandler.realtime_queue.get()

            q = np.array([
                d.get("qw", 1.0),
                d.get("qx", 0.0),
                d.get("qy", 0.0),
                d.get("qz", 0.0)
            ])

            if np.linalg.norm(q) > 0:
                q /= np.linalg.norm(q)

                with lock:
                    current_quat = q

# ==========================================================
# Qt + OpenGL
# ==========================================================
app = QApplication(sys.argv)

view = gl.GLViewWidget()
view.setWindowTitle("Movella DOT – 3D Orientation")
view.setCameraPosition(distance=2)
view.setBackgroundColor('k')
view.show()

grid = gl.GLGridItem()
grid.scale(0.5, 0.5, 0.5)
view.addItem(grid)

# Sensor body
verts = np.array([
    [-0.25,-0.12,-0.05],
    [ 0.25,-0.12,-0.05],
    [ 0.25, 0.12,-0.05],
    [-0.25, 0.12,-0.05],
    [-0.25,-0.12, 0.05],
    [ 0.25,-0.12, 0.05],
    [ 0.25, 0.12, 0.05],
    [-0.25, 0.12, 0.05],
])

faces = np.array([
    [0,1,2],[0,2,3],
    [4,5,6],[4,6,7],
    [0,1,5],[0,5,4],
    [2,3,7],[2,7,6],
    [1,2,6],[1,6,5],
    [0,3,7],[0,7,4]
])

colors = np.ones((len(faces),4))
colors[:,0]=0.2
colors[:,1]=0.7
colors[:,2]=1.0
colors[:,3]=0.9

mesh = gl.GLMeshItem(
    vertexes=verts,
    faces=faces,
    faceColors=colors,
    smooth=False,
    drawEdges=True
)
view.addItem(mesh)

verts0 = verts - verts.mean(axis=0)

# ==========================================================
# Update loop (60 FPS)
# ==========================================================
def update():
    with lock:
        q = current_quat.copy()

    R = quat_to_matrix(q)
    rotated = verts0 @ R.T

    mesh.setMeshData(
        vertexes=rotated + verts.mean(axis=0),
        faces=faces,
        faceColors=colors
    )

timer = QTimer()
timer.timeout.connect(update)
timer.start(16)

# ==========================================================
# Start sensor thread
# ==========================================================
threading.Thread(
    target=sensor_loop,
    daemon=True
).start()

sys.exit(app.exec_())
