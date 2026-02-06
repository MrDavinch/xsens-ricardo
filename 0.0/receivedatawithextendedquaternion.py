from xdpchandler import *
import movelladot_pc_sdk


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

    # === USAMOS SOLO UN SENSOR ===
    device = xdpcHandler.connectedDots()[0]
    print("Using device:", device.bluetoothAddress())

    if not device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_CustomMode5):
        print("Failed to start measurement")
        exit(-1)

    print("\nStreaming data in real time...\n")

    last_ts = None

    while True:
        if not xdpcHandler.realtime_queue.empty():
            d = xdpcHandler.realtime_queue.get()

            if last_ts:
                dt = (d["timestamp"] - last_ts) / 1e6
            else:
                dt = 0

            last_ts = d["timestamp"]

            print(
                f"dt:{dt:.4f}  "
                f"Q:[{d.get('qw',0):.3f},{d.get('qx',0):.3f},{d.get('qy',0):.3f},{d.get('qz',0):.3f}]  "
                f"A:[{d.get('ax',0):.3f},{d.get('ay',0):.3f},{d.get('az',0):.3f}]  "
                f"G:[{d.get('gx',0):.3f},{d.get('gy',0):.3f},{d.get('gz',0):.3f}]"
            )
