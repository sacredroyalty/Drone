#!/usr/bin/env python3
"""
lidar_reader.py
Simple, reliable YDLIDAR X2 reader for Raspberry Pi.
Continuously updates:
  - obstacle_ahead  (bool)
  - min_distance    (metres in forward sector)
"""

import threading
import time
import math
from collections import deque

try:
    import serial
except ImportError:
    raise ImportError("Please install pyserial:  pip3 install pyserial")

class YDLidarX2:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200):
        self.port = port
        self.baudrate = baudrate
        self.ser = None

        # Public data that the mission script will read
        self.obstacle_ahead = False
        self.min_distance = 999.0          # metres
        self.last_update = 0.0

        # Configuration
        self.FORWARD_SECTOR = 30           # ±30 degrees
        self.OBSTACLE_THRESHOLD = 3.0      # metres
        self.MAX_RANGE = 8.0               # metres (ignore farther points)

        self._running = False
        self._thread = None
        self._lock = threading.Lock()

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            print(f"[LiDAR] Connected to {self.port}")
            return True
        except Exception as e:
            print(f"[LiDAR] Failed to open {self.port}: {e}")
            return False

    def start(self):
        if not self.ser or not self.ser.is_open:
            if not self.connect():
                return False

        self._running = True
        self._thread = threading.Thread(target=self._scan_loop, daemon=True)
        self._thread.start()
        print("[LiDAR] Scanning started")
        return True

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        if self.ser and self.ser.is_open:
            self.ser.close()
        print("[LiDAR] Stopped")

    def _scan_loop(self):
        """Very simple parser – good enough for obstacle avoidance"""
        buffer = bytearray()

        while self._running:
            try:
                data = self.ser.read(512)
                if data:
                    buffer.extend(data)

                # Look for packet header 0xAA 0x55
                while len(buffer) >= 10:
                    if buffer[0] == 0xAA and buffer[1] == 0x55:
                        # Basic packet length check
                        sample_count = buffer[3]
                        packet_len = 10 + sample_count * 2

                        if len(buffer) < packet_len:
                            break

                        # Extract distances (very simplified)
                        distances = []
                        for i in range(sample_count):
                            idx = 10 + i * 2
                            dist_raw = buffer[idx] | (buffer[idx + 1] << 8)
                            dist_m = (dist_raw / 4.0) / 1000.0   # mm → m

                            if 0.12 < dist_m < self.MAX_RANGE:
                                distances.append(dist_m)

                        # For simplicity we treat the whole scan as forward sector
                        # (works well when LiDAR is mounted pointing forward)
                        if distances:
                            min_d = min(distances)
                            with self._lock:
                                self.min_distance = min_d
                                self.obstacle_ahead = min_d < self.OBSTACLE_THRESHOLD
                                self.last_update = time.time()

                        # Remove processed packet
                        buffer = buffer[packet_len:]
                    else:
                        buffer.pop(0)

            except Exception as e:
                print(f"[LiDAR] Read error: {e}")
                time.sleep(0.1)

    def get_status(self):
        with self._lock:
            return self.obstacle_ahead, self.min_distance, self.last_update


# ---------- Quick test ----------
if __name__ == "__main__":
    lidar = YDLidarX2(port="/dev/ttyUSB0")   # change if needed
    if lidar.start():
        try:
            while True:
                obstacle, dist, _ = lidar.get_status()
                print(f"Obstacle: {obstacle} | Min distance: {dist:.2f} m")
                time.sleep(0.2)
        except KeyboardInterrupt:
            lidar.stop()