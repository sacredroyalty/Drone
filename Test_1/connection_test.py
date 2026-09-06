#!/usr/bin/env python3
"""
test_pixhawk_connection.py  (Improved version)
Automatically tries the most common serial ports on Raspberry Pi.
"""

import asyncio
import os
from mavsdk import System
import time

# List of ports we will try (in order of preference)
PORTS_TO_TRY = [
    "/dev/serial0",      # Preferred symlink
    "/dev/ttyAMA0",      # Most common on newer Pi OS
    "/dev/ttyS0",        # Sometimes used
    "/dev/ttyAMA1",      # Rare
]

BAUDRATE = 921600


async def try_connect(port: str) -> bool:
    connection_string = f"serial://{port}:{BAUDRATE}"
    print(f"\nTrying: {connection_string}")

    drone = System()
    try:
        await drone.connect(system_address=connection_string)
    except Exception as e:
        print(f"  → Failed to open port: {e}")
        return False

    print("  Waiting for heartbeat (max 8 seconds)...")
    start = time.time()

    try:
        async for state in drone.core.connection_state():
            if state.is_connected:
                print(f"\n✅ SUCCESS! Connected using {port}")
                return True

            if time.time() - start > 8:
                print("  → Timeout - no heartbeat")
                break

            await asyncio.sleep(0.3)
    except Exception as e:
        print(f"  → Error while waiting: {e}")

    return False


async def main():
    print("=" * 65)
    print("Pixhawk ↔ Raspberry Pi Connection Tester")
    print("=" * 65)
    print(f"Baudrate: {BAUDRATE}")
    print("Make sure TX/RX are correct and MAV_1 settings are set.")
    print("-" * 65)

    # First show what serial devices exist
    print("\nAvailable serial devices on your system:")
    os.system("ls -l /dev/serial* /dev/ttyAMA* /dev/ttyS* 2>/dev/null || true")
    print("-" * 65)

    success = False
    working_port = None

    for port in PORTS_TO_TRY:
        if not os.path.exists(port):
            print(f"\nSkipping {port} (does not exist)")
            continue

        if await try_connect(port):
            success = True
            working_port = port
            break

    print("\n" + "=" * 65)
    if success:
        print(f"GOOD NEWS: Connection works with → {working_port}")
        print(f"\nUse this in your future scripts:")
        print(f'CONNECTION = "serial://{working_port}:{BAUDRATE}"')
    else:
        print("❌ Could not connect with any port.")
        print("\nNext things to check:")
        print("1. Run:  ls -l /dev/serial* /dev/ttyAMA* /dev/ttyS*")
        print("2. Swap TX and RX wires")
        print("3. Make sure serial console is disabled:")
        print("     sudo raspi-config → Interface Options → Serial Port")
        print("     → Login shell: No  |  Serial hardware: Yes")
        print("4. Confirm baudrate is really 921600 in QGroundControl")
        print("5. Try a lower baudrate temporarily (57600) for testing")
    print("=" * 65)


if __name__ == "__main__":
    asyncio.run(main())