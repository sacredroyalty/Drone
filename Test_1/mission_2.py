#!/usr/bin/env python3
"""
Mission 2: Take off → fly 5 m North → hover at 7 m for 20 s → RTL
"""
import asyncio
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("-- Connected!")
            break

    print("Waiting for global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position OK")
            break

    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off to ~5 m")
    await drone.action.set_takeoff_altitude(5.0)
    await drone.action.takeoff()
    await asyncio.sleep(8)          # give it time to climb

    # ----- Offboard setup -----
    print("-- Setting initial Offboard setpoint")
    await drone.offboard.set_position_ned(PositionNedYaw(0.0, 0.0, -5.0, 0.0))

    try:
        await drone.offboard.start()
    except OffboardError as e:
        print(f"Offboard start failed: {e}")
        await drone.action.disarm()
        return

    # Fly 5 m North and climb to 7 m
    print("-- Going 5 m North, altitude 7 m")
    await drone.offboard.set_position_ned(PositionNedYaw(5.0, 0.0, -7.0, 0.0))
    await asyncio.sleep(8)          # travel time

    print("-- Hovering for 10 seconds")
    await asyncio.sleep(10)

    print("-- Stopping Offboard and returning to launch")
    await drone.offboard.stop()
    await drone.action.return_to_launch()

    # Wait until landed
    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("-- Landed at home")
            break

if __name__ == "__main__":
    asyncio.run(run())