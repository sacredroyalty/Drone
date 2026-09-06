#!/usr/bin/env python3
"""
test_pixhawk_connection.py
Simple script to verify MAVLink connection between Raspberry Pi and Pixhawk
using GPIO UART (GPIO 14/15) at 921600 baud.
"""

import asyncio
from mavsdk import System
import time

# ================== CONFIG ==================
# For Raspberry Pi GPIO UART (pins 14 & 15)
CONNECTION_STRING = "serial:///dev/serial0:921600"

# Alternative if serial0 doesn't work:
# CONNECTION_STRING = "serial:///dev/ttyAMA0:921600"
# ============================================

async def test_connection():
    print("=" * 60)
    print("Pixhawk ↔ Raspberry Pi Connection Test")
    print("=" * 60)
    print(f"Trying to connect using: {CONNECTION_STRING}")
    print("Make sure:")
    print("  - TELEM1 is connected to GPIO 14 (TX) & 15 (RX) + GND")
    print("  - Baudrate is 921600 on both sides")
    print("  - MAV_1_MODE = Onboard")
    print("-" * 60)

    drone = System()
    
    try:
        await drone.connect(system_address=CONNECTION_STRING)
    except Exception as e:
        print(f"\n[ERROR] Failed to create connection: {e}")
        return

    print("\nWaiting for heartbeat from Pixhawk...")
    print("(This can take up to 10–15 seconds)")

    start_time = time.time()
    connected = False

    try:
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("\n✅ SUCCESS! Connected to Pixhawk!")
                connected = True
                break

            if time.time() - start_time > 15:
                print("\n❌ Timeout – No heartbeat received after 15 seconds.")
                break

            await asyncio.sleep(0.5)

    except Exception as e:
        print(f"\n[ERROR] While waiting for connection: {e}")
        return

    if not connected:
        print("\nPossible problems:")
        print("  1. Wrong UART device (try /dev/ttyAMA0 instead of /dev/serial0)")
        print("  2. Baudrate mismatch (must be 921600 on both sides)")
        print("  3. TX/RX are swapped")
        print("  4. Serial console is still enabled (disable it in raspi-config)")
        print("  5. Pixhawk is not powered or MAV_1_CONFIG is wrong")
        return

    # -------- Extra useful information --------
    print("\nGathering some basic info from the flight controller...\n")

    # Autopilot version
    try:
        async for info in drone.info.get_version():
            print(f"Flight Controller : {info.flight_sw_major}.{info.flight_sw_minor}.{info.flight_sw_patch}")
            print(f"Vendor            : {info.vendor_id}")
            break
    except:
        print("Could not get version info")

    # Check if we have global position
    print("\nChecking sensors...")
    async for health in drone.telemetry.health():
        print(f"  GPS                : {'OK' if health.is_global_position_ok else 'Not ready'}")
        print(f"  Home position      : {'OK' if health.is_home_position_ok else 'Not set'}")
        print(f"  Armable            : {'Yes' if health.is_armable else 'No'}")
        break

    # Current flight mode
    async for mode in drone.telemetry.flight_mode():
        print(f"  Current mode       : {mode}")
        break

    print("\n" + "=" * 60)
    print("Connection test finished successfully!")
    print("You can now run your MAVSDK mission scripts.")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_connection())