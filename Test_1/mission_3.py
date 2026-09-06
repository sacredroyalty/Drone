#!/usr/bin/env python3
"""
Mission 3:
  - Take off
  - Go North 7 m @ 7 m altitude → hover 10 s
  - Go East 5 m                → hover 10 s
  - Go South 5 m               → hover 10 s
  - Return to Launch
"""
import asyncio
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    print("Waiting for drone...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("-- Connected")
            break

    print("Waiting for global position...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Position OK")
            break

    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off")
    await drone.action.set_takeoff_altitude(5.0)
    await drone.action.takeoff()
    await asyncio.sleep(8)

    # Start Offboard
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -5.0, 0.0))
    try:
        await drone.offboard.start()
    except OffboardError as e:
        print(f"Offboard failed: {e}")
        await drone.action.disarm()
        return

    # ---------- Waypoints (NED relative to home) ----------
    # 1. North 7 m, altitude 7 m
    print("-- Going North 7 m @ 7 m")
    await drone.offboard.set_position_ned(PositionNedYaw(7.0, 0.0, -7.0, 0.0))
    await asyncio.sleep(10)          # travel
    print("-- Hover 10 s")
    await asyncio.sleep(10)

    # 2. From current position → East 5 m  →  (7 N, 5 E)
    print("-- Going East 5 m")
    await drone.offboard.set_position_ned(PositionNedYaw(7.0, 5.0, -7.0, 0.0))
    await asyncio.sleep(8)
    print("-- Hover 10 s")
    await asyncio.sleep(10)

    # 3. From current position → South 5 m →  (2 N, 5 E)
    print("-- Going South 5 m")
    await drone.offboard.set_position_ned(PositionNedYaw(2.0, 5.0, -7.0, 0.0))
    await asyncio.sleep(8)
    print("-- Hover 10 s")
    await asyncio.sleep(10)

    # ---------- Return ----------
    print("-- Stopping Offboard → RTL")
    await drone.offboard.stop()
    await drone.action.return_to_launch()

    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("-- Landed")
            break

if __name__ == "__main__":
    asyncio.run(run())