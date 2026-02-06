from xdpchandler import *
import movelladot_pc_sdk

import pandas as pd


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
    print("Press CTRL + C to stop and save CSV file")

    last_ts = None

    # ===============================
    # DATA STORAGE
    # ===============================
    data_log = []

    try:
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

                    "ax": d.get("ax", 0.0),
                    "ay": d.get("ay", 0.0),
                    "az": d.get("az", 0.0),

                    "gx": d.get("gx", 0.0),
                    "gy": d.get("gy", 0.0),
                    "gz": d.get("gz", 0.0),
                }

                data_log.append(row)

                print(
                    f"dt:{dt:.4f}  "
                    f"Q:[{row['qw']:.3f},{row['qx']:.3f},{row['qy']:.3f},{row['qz']:.3f}]  "
                    f"A:[{row['ax']:.3f},{row['ay']:.3f},{row['az']:.3f}]  "
                    f"G:[{row['gx']:.3f},{row['gy']:.3f},{row['gz']:.3f}]"
                )

    except KeyboardInterrupt:
        print("\nStopping measurement and saving CSV file...")

        df = pd.DataFrame(data_log)

        filename = "movella_dot_data.csv"
        df.to_csv(filename, index=False)

        print(f"Data saved to {filename}")
