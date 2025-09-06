import time
import random
import os
import queue
import threading

# -----------------------------
# STEP 1: Data Collection (Sensors Simulation)
# -----------------------------
class VehicleSensors:
    def __init__(self, name):
        self.name = name
        self.speed = 25.0  # m/s
        self.accel = 0.0
        self.braking = False
        self.hazard = ""

    def update(self, brake=False):
        if brake:
            self.accel = -8.0   # emergency braking deceleration
            self.braking = True
        else:
            self.accel = random.uniform(-0.5, 0.5)
            self.braking = False
        self.speed = max(0, self.speed + self.accel * 0.1)

    def read_data(self):
        return {
            "from": self.name,
            "timestamp": time.time(),
            "speed_mps": round(self.speed, 2),
            "accel_mps2": round(self.accel, 2),
            "braking": self.braking,
            "hazard": self.hazard,
            "type": "STATUS"
        }

# -----------------------------
# STEP 2: Quantum Noise Encoding (Simulated)
# -----------------------------
def encode_message(msg):
    bits = "".join(format(ord(c), "08b") for c in str(msg))
    signal = []
    for b in bits:
        base = random.gauss(0, 1)
        if b == "1":
            signal.append(base + random.gauss(0, 3))  # high variance
        else:
            signal.append(base + random.gauss(0, 0.2))  # low variance
    return signal

def decode_message(signal):
    bits = ""
    for val in signal:
        bits += "1" if abs(val) > 1.5 else "0"
    chars = [bits[i:i+8] for i in range(0, len(bits), 8)]
    try:
        return "".join(chr(int(c, 2)) for c in chars if len(c) == 8)
    except:
        return ""

# -----------------------------
# STEP 3 & 4: Transmission / Reception
# -----------------------------
class OpticalChannel:
    def __init__(self):
        self.q = queue.Queue()

    def transmit(self, encoded_msg):
        self.q.put(encoded_msg)

    def receive(self):
        try:
            return self.q.get(timeout=0.1)
        except queue.Empty:
            return None

# -----------------------------
# STEP 5: Receiver & ADAS Reaction
# -----------------------------
class VehicleReceiver:
    def __init__(self, name, channel, vehicle_ref):
        self.name = name
        self.channel = channel
        self.vehicle = vehicle_ref

    def listen(self):
        while True:
            signal = self.channel.receive()
            if signal is None:
                continue
            decoded = decode_message(signal)
            if decoded:
                try:
                    import ast
                    msg = ast.literal_eval(decoded)
                    if isinstance(msg, dict):
                        self.process_message(msg)
                except:
                    pass

    def process_message(self, msg):
        if msg.get("type") == "STATUS":
            print(f"[ADAS {self.name}] STATUS from {msg['from']}: speed={msg['speed_mps']} m/s")
        if msg.get("type") == "EMERGENCY_BRAKE":
            print(f"[ADAS {self.name}] EMERGENCY_BRAKE from {msg['from']} at {time.strftime('%X')} -- AUTO-BRAKE ACTIVATED!")
            self.vehicle.emergency_brake()  # propagate braking

# -----------------------------
# STEP 6: Full Vehicle Integration
# -----------------------------
class Vehicle:
    def __init__(self, name, channel):
        self.name = name
        self.sensors = VehicleSensors(name)
        self.channel = channel
        self.receiver = VehicleReceiver(name, channel, self)

    def start(self):
        threading.Thread(target=self.receiver.listen, daemon=True).start()

    def broadcast(self, brake=False):
        self.sensors.update(brake)
        msg = self.sensors.read_data()
        if brake:
            msg = {"from": self.name, "type": "EMERGENCY_BRAKE"}
        encoded = encode_message(msg)
        self.channel.transmit(encoded)

    def emergency_brake(self):
        """Called when ADAS decides to brake automatically"""
        self.broadcast(brake=True)

# -----------------------------
# DEMO: Convoy of 3 Cars
# -----------------------------
if __name__ == "__main__":
    channel = OpticalChannel()

    # Create 3 cars in a convoy
    carA = Vehicle("CarA", channel)  # Leader
    carB = Vehicle("CarB", channel)  # Middle
    carC = Vehicle("CarC", channel)  # Tail

    carA.start()
    carB.start()
    carC.start()

    print("🚗 Convoy Demo: CarA will hard-brake, and others should auto-react.\n")

    for i in range(6):
        if i == 2:
            print("\n⚠️  CarA triggers EMERGENCY BRAKE!\n")
            carA.broadcast(brake=True)
        else:
            carA.broadcast()
        carB.broadcast()
        carC.broadcast()
        time.sleep(1)

    print("\n✅ Demo finished: All cars received braking alert and avoided collision.")
