import tkinter as tk
from tkinter import messagebox
from xdpchandler import *
import movelladot_pc_sdk

class XsensApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Xsens DOT Live Viewer")

        # UI Elements
        self.status_label = tk.Label(root, text="Click 'Start' to connect sensors")
        self.status_label.pack(pady=10)

        self.data_text = tk.Text(root, height=15, width=60)
        self.data_text.pack(pady=10)

        self.start_button = tk.Button(root, text="Start", command=self.start_system)
        self.start_button.pack()

        # Xsens handler
        self.xdpcHandler = XdpcHandler()
        self.running = False

    def start_system(self):
        if not self.xdpcHandler.initialize():
            messagebox.showerror("Error", "Could not initialize Xsens handler.")
            return

        self.xdpcHandler.scanForDots()
        if len(self.xdpcHandler.detectedDots()) == 0:
            messagebox.showerror("Error", "No Xsens DOT devices found.")
            return

        self.xdpcHandler.connectDots()
        if len(self.xdpcHandler.connectedDots()) == 0:
            messagebox.showerror("Error", "Could not connect to any device.")
            return

        # Configure each sensor
        for device in self.xdpcHandler.connectedDots():
            device.setLogOptions(movelladot_pc_sdk.XsLogOptions_Quaternion)
            device.startMeasurement(movelladot_pc_sdk.XsPayloadMode_ExtendedEuler)

        self.status_label.config(text="Connected! Streaming live data...")
        self.running = True
        self.update_stream()

    def update_stream(self):
        if not self.running:
            return

        if self.xdpcHandler.packetsAvailable():
            self.data_text.delete(1.0, tk.END)
            for device in self.xdpcHandler.connectedDots():
                packet = self.xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                if packet.containsOrientation():
                    euler = packet.orientationEuler()
                    line = f"{device.bluetoothAddress()} → Roll:{euler.x():.2f}, Pitch:{euler.y():.2f}, Yaw:{euler.z():.2f}\n"
                    self.data_text.insert(tk.END, line)

        # Repeat the function every 50ms
        self.root.after(50, self.update_stream)

    def on_close(self):
        self.running = False
        for device in self.xdpcHandler.connectedDots():
            device.stopMeasurement()
            device.disableLogging()
        self.xdpcHandler.cleanup()
        self.root.destroy()

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    app = XsensApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
