import tkinter as tk
from tkinter import messagebox
import threading
import time
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

        # Lock para hilos
        self.data_lock = threading.Lock()

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

        # Iniciar hilo de lectura
        self.read_thread = threading.Thread(target=self.read_data_loop, daemon=True)
        self.read_thread.start()

        # Actualizar GUI periódicamente
        self.update_gui()

    def read_data_loop(self):
        """Hilo para leer paquetes continuamente"""
        while self.running:
            try:
                for device in self.xdpcHandler.connectedDots():
                    if not device.isConnected():
                        # Intentar reconexión
                        try:
                            device.reconnect()
                        except Exception as e:
                            with self.data_lock:
                                self.data_text.insert(tk.END, f"{device.bluetoothAddress()} → Reconnection failed\n")
                        continue

                    # Leer todos los paquetes disponibles
                    while self.xdpcHandler.packetsAvailable():
                        packet = self.xdpcHandler.getNextPacket(device.portInfo().bluetoothAddress())
                        if packet.containsOrientation():
                            euler = packet.orientationEuler()
                            line = f"{device.bluetoothAddress()} → Roll:{euler.x():.2f}, Pitch:{euler.y():.2f}, Yaw:{euler.z():.2f}\n"
                            with self.data_lock:
                                self.data_text.insert(tk.END, line)

            except Exception as e:
                with self.data_lock:
                    self.data_text.insert(tk.END, f"Error reading data: {str(e)}\n")

            time.sleep(0.02)  # 20 ms de espera para no saturar el CPU

    def update_gui(self):
        """Actualiza la GUI sin bloquear el hilo principal"""
        with self.data_lock:
            self.data_text.see(tk.END)  # auto-scroll al final
        if self.running:
            self.root.after(100, self.update_gui)  # actualizar cada 100 ms

    def on_close(self):
        self.running = False
        # Esperar que el hilo termine
        if hasattr(self, "read_thread"):
            self.read_thread.join(timeout=1)

        for device in self.xdpcHandler.connectedDots():
            try:
                device.stopMeasurement()
                device.disableLogging()
            except:
                pass

        self.xdpcHandler.cleanup()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = XsensApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
