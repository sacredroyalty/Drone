#!/usr/bin/env python3
"""
mission_with_avoidance.py
Stealth + Basic 2D Obstacle Avoidance using YDLIDAR X2 + MAVSDK
"""

import asyncio
import time
from mavsdk import System
from mavsdk.offboard import OffboardError, PositionNedYaw, VelocityNedYaw
from lidar_reader import YDLidarX2

# ===================== USER SETTINGS =====================
CONNECTION = "udpin://0.0.0.0:14540"      # change if needed

TAKEOFF_ALTITUDE = 4.0                    # metres
CRUISE_ALTITUDE = 4.0                     # low stealth altitude
MAX_HORIZONTAL_SPEED = 3.5                # m/s
MAX_VERTICAL_SPEED = 0.8                  # m/s

OBSTACLE_THRESHOLD = 3.0                  # metres
SIDE_STEP_DISTANCE = 2.5                  # metres left/right when avoiding

# Example simple mission (North, East relative to home)
WAYPOINTS = [
    (10.0,  0.0),   # 10 m North
    (10.0,  8.0),   # then 8 m East
    (0.0,   8.0),   # then South
]
# ========================================================


class AvoidanceMission:
    def __init__(self):
        self.drone = System()
        self.lidar = YDLidarX2(port="/dev/ttyUSB0")  # change port if needed
        self.current_north = 0.0
        self.current_east = 0.0
        self.current_yaw = 0.0

    async def connect(self):
        print("Connecting to drone...")
        await self.drone.connect(system_address=CONNECTION)

        async for state in self.drone.core.connection_state():
            if state.is_connected:
                print("-- Connected to drone")
                break

        print("Waiting for global position...")
        async for health in self.drone.telemetry.health():
            if health.is_global_position_ok and health.is_home_position_ok:
                print("-- Global position OK")
                break

    async def arm_and_takeoff(self):
        print("-- Arming")
        await self.drone.action.arm()

        print(f"-- Taking off to {TAKEOFF_ALTITUDE} m")
        await self.drone.action.set_takeoff_altitude(TAKEOFF_ALTITUDE)
        await self.drone.action.takeoff()
        await asyncio.sleep(8)

    async def start_offboard(self):
        # Set initial setpoint
        await self.drone.offboard.set_position_ned(
            PositionNedYaw(0.0, 0.0, -TAKEOFF_ALTITUDE, 0.0)
        )
        try:
            await self.drone.offboard.start()
            print("-- Offboard started")
        except OffboardError as e:
            print(f"Offboard start failed: {e}")
            await self.drone.action.disarm()
            raise

    async def hold_position(self, duration=2.0):
        """Hold current NED position"""
        await self.drone.offboard.set_position_ned(
            PositionNedYaw(self.current_north, self.current_east,
                           -CRUISE_ALTITUDE, self.current_yaw)
        )
        await asyncio.sleep(duration)

    async def go_to_relative(self, north, east, yaw=0.0):
        """Move to a relative NED position with continuous LiDAR check"""
        self.current_north = north
        self.current_east = east
        self.current_yaw = yaw

        print(f"→ Moving to N:{north:.1f}  E:{east:.1f}")

        await self.drone.offboard.set_position_ned(
            PositionNedYaw(north, east, -CRUISE_ALTITUDE, yaw)
        )

        # Simple arrival + continuous avoidance monitoring
        timeout = 40.0
        start = time.time()

        while time.time() - start < timeout:
            obstacle, min_dist, _ = self.lidar.get_status()

            if obstacle:
                print(f"!!! OBSTACLE DETECTED at {min_dist:.2f} m → AVOIDING")
                await self.avoid_obstacle()
                # After avoidance we re-issue the original target
                await self.drone.offboard.set_position_ned(
                    PositionNedYaw(north, east, -CRUISE_ALTITUDE, yaw)
                )
                start = time.time()   # reset timeout

            # Check if we are close enough (rough)
            # In real use you can add better position feedback
            await asyncio.sleep(0.3)

        print("  Reached (or timeout)")

    async def avoid_obstacle(self):
        """Simple left / right dodge"""
        print("  Holding position...")
        await self.hold_position(1.5)

        # Try right first
        print(f"  Stepping RIGHT {SIDE_STEP_DISTANCE} m")
        new_east = self.current_east + SIDE_STEP_DISTANCE
        await self.drone.offboard.set_position_ned(
            PositionNedYaw(self.current_north, new_east,
                           -CRUISE_ALTITUDE, self.current_yaw)
        )
        await asyncio.sleep(4)

        # Re-check
        obstacle, min_dist, _ = self.lidar.get_status()
        if not obstacle:
            print("  Path clear after right step")
            self.current_east = new_east
            return

        # Try left
        print(f"  Still blocked → Stepping LEFT {SIDE_STEP_DISTANCE * 2} m")
        new_east = self.current_east - SIDE_STEP_DISTANCE
        await self.drone.offboard.set_position_ned(
            PositionNedYaw(self.current_north, new_east,
                           -CRUISE_ALTITUDE, self.current_yaw)
        )
        await asyncio.sleep(5)

        obstacle, min_dist, _ = self.lidar.get_status()
        if not obstacle:
            print("  Path clear after left step")
            self.current_east = new_east
        else:
            print("  Still blocked – holding and waiting...")
            await self.hold_position(5.0)

        # Log the event (you can expand this)
        print(f"  [LOG] Avoidance performed | min_dist={min_dist:.2f} m")

    async def run_mission(self):
        # Start LiDAR
        if not self.lidar.start():
            print("Failed to start LiDAR – aborting")
            return

        await self.connect()
        await self.arm_and_takeoff()
        await self.start_offboard()

        # Climb / set cruise altitude
        await self.drone.offboard.set_position_ned(
            PositionNedYaw(0.0, 0.0, -CRUISE_ALTITUDE, 0.0)
        )
        await asyncio.sleep(3)

        # Fly the waypoints with avoidance
        for i, (n, e) in enumerate(WAYPOINTS):
            print(f"\n=== Waypoint {i+1}/{len(WAYPOINTS)} ===")
            await self.go_to_relative(n, e)

        print("\n=== Mission complete – Returning to Launch ===")
        await self.drone.offboard.stop()
        await self.drone.action.return_to_launch()

        # Wait until landed
        async for in_air in self.drone.telemetry.in_air():
            if not in_air:
                print("-- Landed")
                break

        self.lidar.stop()


async def main():
    mission = AvoidanceMission()
    await mission.run_mission()


if __name__ == "__main__":
    asyncio.run(main())