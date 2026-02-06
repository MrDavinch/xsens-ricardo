from xdpchandler import *
import movelladot_pc_sdk
import matplotlib.pyplot as plt
from collections import deque

# Número de puntos a mostrar en la gráfica
N = 100

# Colas para almacenar los últimos N valores
qw_vals = deque([0]*N, maxlen=N)
qx_vals = deque([0]*N, maxlen=N)
qy_vals = deque([0]*N, maxlen=N)
qz_vals = deque([0]*N, maxlen=N)

# Configuración de matplotlib en modo interactivo
plt.ion()
fig, ax = plt.subplots(figsize=(10,5))

colors = ['r','g','b','k']  # colores para cada componente
lines = [ax.plot([], [], color=c, label=l)[0] for c,l in zip(colors, ['qw','qx','qy','qz'])]

ax.set_xlim(0, N)
ax.set_ylim(-1.1, 1.1)  # rango un poco más amplio para ver cambios pequeños
ax.set_title("Cuaterniones en tiempo real")
ax.set_xlabel("Muestras")
ax.set_ylabel("Valor")
ax.grid(True)
ax.legend(loc='upper right')

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

            # Ignorar datos vacíos
            if qw==0 and qx==0 and qy==0 and qz==0:
                continue

            # Mostrar en terminal
            print(f"Q: [{qw:.3f}, {qx:.3f}, {qy:.3f}, {qz:.3f}]")

            # Guardar en colas
            qw_vals.append(qw)
            qx_vals.append(qx)
            qy_vals.append(qy)
            qz_vals.append(qz)

            # Actualizar plot
            for line, vals in zip(lines, [qw_vals, qx_vals, qy_vals, qz_vals]):
                line.set_ydata(vals)
                line.set_xdata(range(len(vals)))

            plt.pause(0.01)
