#!/usr/bin/env python3
"""
Mission 4 (fixed): Fly to GPS location at relative altitude,
hover 10 s, then RTL.
- Robust arrival detection (no more stuck "waiting to reach target")
"""
import asyncio
import math
from mavsdk import System

# ========== FILL THESE IN ==========
TARGET_LAT = 37.412343          # degrees
TARGET_LON = -121.998426           # degrees
TARGET_REL_ALT = 5.0            # meters ABOVE home/rest position
# ===================================

def get_distance_metres(lat1, lon1, lat2, lon2):
    """Approximate distance in metres between two GPS points"""
    R = 6371000  # Earth radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

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

    # Get home absolute altitude
    print("Fetching home altitude...")
    async for home in drone.telemetry.home():
        home_abs_alt = home.absolute_altitude_m
        break

    target_abs_alt = home_abs_alt + TARGET_REL_ALT

    print(f"-- Target GPS          : {TARGET_LAT:.6f}, {TARGET_LON:.6f}")
    print(f"-- Relative altitude   : {TARGET_REL_ALT} m above home")
    print(f"-- Absolute altitude   : {target_abs_alt:.1f} m AMSL")

    print("-- Arming")
    await drone.action.arm()

    print("-- Taking off")
    await drone.action.set_takeoff_altitude(5.0)
    await drone.action.takeoff()
    await asyncio.sleep(8)

    print("-- Going to target location")
    await drone.action.goto_location(
        TARGET_LAT,
        TARGET_LON,
        target_abs_alt,
        0.0
    )

    # ---------- Robust arrival check ----------
    print("-- Waiting to reach target...")

    ARRIVAL_DISTANCE = 3.0      # metres – how close is "close enough"
    ALT_TOLERANCE = 1.5         # metres
    TIMEOUT = 60                # seconds – never wait forever
    start_time = asyncio.get_event_loop().time()

    async for position in drone.telemetry.position():
        dist = get_distance_metres(
            position.latitude_deg, position.longitude_deg,
            TARGET_LAT, TARGET_LON
        )
        alt_error = abs(position.relative_altitude_m - TARGET_REL_ALT)

        # Print progress every few seconds
        print(f"   Distance: {dist:.1f} m | Alt error: {alt_error:.1f} m")

        if dist < ARRIVAL_DISTANCE and alt_error < ALT_TOLERANCE:
            print("-- Reached target!")
            break

        # Safety timeout
        if asyncio.get_event_loop().time() - start_time > TIMEOUT:
            print("-- Timeout reached – continuing anyway")
            break

        await asyncio.sleep(1.0)

    # ---------- Hover ----------
    print("-- Hovering for 10 seconds")
    await asyncio.sleep(10)

    print("-- Returning to launch")
    await drone.action.return_to_launch()

    async for in_air in drone.telemetry.in_air():
        if not in_air:
            print("-- Landed at home")
            break

if __name__ == "__main__":
    asyncio.run(run())