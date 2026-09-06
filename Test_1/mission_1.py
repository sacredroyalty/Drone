#!/usr/bin/env python3
"""
Mission 1: Take off, hover at 5 m for 10 seconds, then land.
"""
import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14540")

    print("Waiting for drone to connect...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("-- Connected to drone!")
            break

    print("Waiting for global position estimate...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("-- Global position estimate OK")
            break

    print("-- Arming")
    await drone.action.arm()

    print("-- Setting take-off altitude to 5 m")
    await drone.action.set_takeoff_altitude(5.0)

    print("-- Taking off")
    await drone.action.takeoff()

    # Wait until we are roughly at the take-off altitude
    async for position in drone.telemetry.position():
        if position.relative_altitude_m >= 4.5:
            break

    print("-- Hovering for 10 seconds")
    await asyncio.sleep(10)

    print("-- Landing")
    await drone.action.land()

    # Wait until landed
    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("-- Landed")
            break

if __name__ == "__main__":
    asyncio.run(run())