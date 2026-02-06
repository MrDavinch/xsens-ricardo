from xdpchandler import *
import movelladot_pc_sdk
import matplotlib.pyplot as plt
from collections import deque

plt.ion()

N = 100

# Colas para quaterniones
qw_vals = deque([0]*N, maxlen=N)
qx_vals = deque([0]*N, maxlen=N)
qy_vals = deque([0]*N, maxlen=N)
qz_vals = deque([0]*N, maxlen=N)

# Colas para aceleración
ax_vals = deque([0]*N, maxlen=N)
ay_vals = deque([0]*N, maxlen=N)
az_vals = deque([0]*N, maxlen=N)

# Colas para giroscopio
gx_vals = deque([0]*N, maxlen=N)
gy_vals = deque([0]*N, maxlen=N)
gz_vals = deque([0]*N, maxlen=N)

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

    # === Usar CustomMode5 para recibir todo ===
    if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_CustomMode5):
        print("Failed to start measurement")
        exit(-1)

    # Configurar figura
    fig, axs = plt.subplots(3, 1, figsize=(12, 8))
    axs[0].set_title("Quaterniones (Q)")
    axs[1].set_title("Aceleración (A)")
    axs[2].set_title("Giroscopio (G)")

    lines_q = [axs[0].plot([], [])[0] for _ in range(4)]
    lines_a = [axs[1].plot([], [])[0] for _ in range(3)]
    lines_g = [axs[2].plot([], [])[0] for _ in range(3)]

    for ax in axs:
        ax.set_xlim(0, N)
        ax.grid(True)

    print("\nStreaming data in real time...\n")

    while True:
        if not xdpcHandler.realtime_queue.empty():
            d = xdpcHandler.realtime_queue.get()

            # Mostrar en consola
            print(
                f"Q:[{d.get('qw',0):.3f},{d.get('qx',0):.3f},{d.get('qy',0):.3f},{d.get('qz',0):.3f}]  "
                f"A:[{d.get('ax',0):.3f},{d.get('ay',0):.3f},{d.get('az',0):.3f}]  "
                f"G:[{d.get('gx',0):.3f},{d.get('gy',0):.3f},{d.get('gz',0):.3f}]"
            )

            # Guardar datos en colas
            qw_vals.append(d.get("qw",0))
            qx_vals.append(d.get("qx",0))
            qy_vals.append(d.get("qy",0))
            qz_vals.append(d.get("qz",0))

            ax_vals.append(d.get("ax",0))
            ay_vals.append(d.get("ay",0))
            az_vals.append(d.get("az",0))

            gx_vals.append(d.get("gx",0))
            gy_vals.append(d.get("gy",0))
            gz_vals.append(d.get("gz",0))

            # Actualizar plots
            for line, vals, ax in zip(lines_q, [qw_vals,qx_vals,qy_vals,qz_vals], [axs[0]]*4):
                line.set_ydata(vals)
                line.set_xdata(range(len(vals)))
                ax.set_ylim(min(vals)-0.1, max(vals)+0.1)

            for line, vals, ax in zip(lines_a, [ax_vals,ay_vals,az_vals], [axs[1]]*3):
                line.set_ydata(vals)
                line.set_xdata(range(len(vals)))
                ax.set_ylim(min(vals)-1, max(vals)+1)

            for line, vals, ax in zip(lines_g, [gx_vals,gy_vals,gz_vals], [axs[2]]*3):
                line.set_ydata(vals)
                line.set_xdata(range(len(vals)))
                ax.set_ylim(min(vals)-1, max(vals)+1)

            plt.pause(0.001)
