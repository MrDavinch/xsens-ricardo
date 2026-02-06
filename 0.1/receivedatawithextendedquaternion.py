from xdpchandler import *
import movelladot_pc_sdk
import matplotlib.pyplot as plt
from collections import deque
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

# Número de puntos para la gráfica de cuaterniones (2D)
N = 100
qw_vals = deque([0]*N, maxlen=N)
qx_vals = deque([0]*N, maxlen=N)
qy_vals = deque([0]*N, maxlen=N)
qz_vals = deque([0]*N, maxlen=N)

# Matplotlib interactivo
plt.ion()
fig = plt.figure(figsize=(12,6))

# Subplot 2D para los cuaterniones
ax2d = fig.add_subplot(1,2,1)
colors = ['r','g','b','k']
lines = [ax2d.plot([], [], color=c, label=l)[0] for c,l in zip(colors, ['qw','qx','qy','qz'])]
ax2d.set_xlim(0, N)
ax2d.set_ylim(-1.1, 1.1)
ax2d.set_title("Cuaterniones en tiempo real")
ax2d.set_xlabel("Muestras")
ax2d.set_ylabel("Valor")
ax2d.grid(True)
ax2d.legend(loc='upper right')

# Subplot 3D para orientación
ax3d = fig.add_subplot(1,2,2, projection='3d')
ax3d.set_xlim([-1, 1])
ax3d.set_ylim([-1, 1])
ax3d.set_zlim([-1, 1])
ax3d.set_title("Orientación 3D del sensor")
ax3d.set_xlabel("X")
ax3d.set_ylabel("Y")
ax3d.set_zlabel("Z")

# Vector de referencia del sensor (ej. eje X del sensor)
v_ref = np.array([1,0,0])

# Función para convertir cuaternión a matriz de rotación
def quat_to_rot_matrix(qw, qx, qy, qz):
    return np.array([
        [1-2*(qy**2 + qz**2), 2*(qx*qy - qz*qw), 2*(qx*qz + qy*qw)],
        [2*(qx*qy + qz*qw), 1-2*(qx**2 + qz**2), 2*(qy*qz - qx*qw)],
        [2*(qx*qz - qy*qw), 2*(qy*qz + qx*qw), 1-2*(qx**2 + qy**2)]
    ])

if __name__ == "__main__":
    xdpcHandler = XdpcHandler()
    if not xdpcHandler.initialize():
        exit(-1)

    xdpcHandler.scanForDots()
    if len(xdpcHandler.detectedDots()) == 0:
        print("No Movella DOT device(s) found.")
        exit(-1)

    xdpcHandler.connectDots()
    if len(xdpcHandler.connectedDots()) == 0:
        print("Could not connect to any Movella DOT device(s).")
        exit(-1)

    device = xdpcHandler.connectedDots()[0]
    print("Using device:", device.bluetoothAddress())

    if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_CustomMode5):
        print("Failed to start measurement")
        exit(-1)

    print("\nStreaming cuaterniones en tiempo real...\n")

    while True:
        if not xdpcHandler.realtime_queue.empty():
            d = xdpcHandler.realtime_queue.get()
            qw, qx, qy, qz = d.get("qw",0), d.get("qx",0), d.get("qy",0), d.get("qz",0)

            if qw==0 and qx==0 and qy==0 and qz==0:
                continue

            # Guardar en colas para 2D
            qw_vals.append(qw)
            qx_vals.append(qx)
            qy_vals.append(qy)
            qz_vals.append(qz)

            # Actualizar gráfica 2D
            for line, vals in zip(lines, [qw_vals, qx_vals, qy_vals, qz_vals]):
                line.set_ydata(vals)
                line.set_xdata(range(len(vals)))

            # --- Orientación 3D ---
            R = quat_to_rot_matrix(qw, qx, qy, qz)
            v_rot = R @ v_ref  # vector rotado

            ax3d.cla()  # limpiar plot 3D
            ax3d.set_xlim([-1, 1])
            ax3d.set_ylim([-1, 1])
            ax3d.set_zlim([-1, 1])
            ax3d.set_title("Orientación 3D del sensor")
            ax3d.set_xlabel("X")
            ax3d.set_ylabel("Y")
            ax3d.set_zlabel("Z")

            # Dibujar vector rotado
            ax3d.quiver(0,0,0, v_rot[0], v_rot[1], v_rot[2], length=1, color='r')

            plt.pause(0.01)
