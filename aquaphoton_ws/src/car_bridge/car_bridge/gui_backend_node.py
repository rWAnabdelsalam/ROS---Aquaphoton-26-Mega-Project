#!/usr/bin/env python3
# Sits between ROS and the React GUI.
# Takes sensor readings off the ROS topic, checks them for problems,
# and sends them to the browser over websocket.
# Takes commands from the browser and publishes them for the car.

import asyncio
import json
import random
import threading

import rclpy
from rclpy.node import Node
import websockets

from car_interfaces.msg import SensorReadings, MotionCommand
from car_bridge.command_handler import process_command


# warning thresholds
VOLT_LOW = 10.5
VOLT_HIGH = 13.0
CURR_MAX = 4.5

# the GUI uses words, the car uses numbers
MODES = {"manual": 0, "autonomous": 1}
MOVEMENTS = {"stop": 0, "forward": 1, "backward": 2, "left": 3, "right": 4}
SPEEDS = {"low": 0, "medium": 1, "high": 2}

MODE_WORDS = {0: "manual", 1: "autonomous"}
MOVEMENT_WORDS = {0: "stop", 1: "forward", 2: "backward", 3: "left", 4: "right"}
SPEED_WORDS = {0: "low", 1: "medium", 2: "high"}


class GuiBackend(Node):

    def __init__(self):
        super().__init__('gui_backend')

        self.create_subscription(SensorReadings, '/car/sensors',
                                 self.got_readings, 10)
        self.pub = self.create_publisher(MotionCommand, '/car/motion_command', 10)

        self.latest = None       # most recent readings, ready to send
        self.warnings = set()    # what's currently wrong

        self.get_logger().info("GUI backend started")

    def check_readings(self, msg):
        found = set()

        if not msg.valid:
            found.add("no data from car")
        if msg.voltage < VOLT_LOW:
            found.add("battery voltage low")
        if msg.voltage > VOLT_HIGH:
            found.add("battery voltage high")
        if msg.current > CURR_MAX:
            found.add("current too high")

        return found

    def got_readings(self, msg):
        found = self.check_readings(msg)

        # only log when something changes, otherwise it spams
        for w in found - self.warnings:
            self.get_logger().warning("WARNING: " + w)
        for w in self.warnings - found:
            self.get_logger().info("cleared: " + w)
        self.warnings = found

        self.latest = {
            "type": "telemetry",
            "voltage": round(msg.voltage, 2),
            "current": round(msg.current, 2),
            "imu": {
                "ax": round(msg.ax, 2),
                "ay": round(msg.ay, 2),
                "az": round(msg.az, 2),
                "gx": round(msg.gx, 2),
                "gy": round(msg.gy, 2),
                "gz": round(msg.gz, 2),
            },
            "mode": MODE_WORDS.get(msg.mode, "unknown"),
            "movement": MOVEMENT_WORDS.get(msg.direction, "unknown"),
            "speed": SPEED_WORDS.get(msg.speed, "unknown"),
            "connected": msg.valid,
            "warnings": sorted(found),
            "distance": round(msg.distance, 1),
        }

    def send_to_car(self, command):
        # use the software team's validation
        result = process_command(command)

        if not result["accepted"]:
            self.get_logger().warning("Bad command: " + result["message"])
            return result

        msg = MotionCommand()
        msg.mode = MODES[result["mode"]]
        msg.direction = MOVEMENTS[result["movement"]]
        msg.speed = SPEEDS[result["speed"]]
        self.pub.publish(msg)

        self.get_logger().info("Command sent: %s %s %s"
                               % (result["mode"], result["movement"],
                                  result["speed"]))
        return result


# the websocket handlers need the node but asyncio calls them
# without arguments, so it's kept here
node = None


async def handle_client(websocket):
    node.get_logger().info("Frontend connected")

    async def receive():
        # listen for commands coming from the browser
        async for text in websocket:
            try:
                command = json.loads(text)
            except json.JSONDecodeError:
                continue

            result = node.send_to_car(command)
            await websocket.send(json.dumps(result))

    async def send():
        # push telemetry and stereo data out to the browser
        while True:
            if node.latest is not None:
                await websocket.send(json.dumps(node.latest))

            stereo = {
                "type": "stereo",
                "left_camera": {"status": "receiving", "frame": "LEFT CAMERA FRAME"},
                "right_camera": {"status": "receiving", "frame": "RIGHT CAMERA FRAME"},
                "depth": {"status": "available", "value": "DEPTH MAP"},
                "distance": round(random.uniform(0.5, 5.0), 2),
            }
            await websocket.send(json.dumps(stereo))

            await asyncio.sleep(0.5)

    try:
        await asyncio.gather(receive(), send())
    except websockets.exceptions.ConnectionClosed:
        node.get_logger().info("Frontend disconnected")


async def run_server():
    node.get_logger().info("Starting WebSocket server...")

    async with websockets.serve(handle_client, "localhost", 8765):
        node.get_logger().info("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()      # keeps the server running


def spin_ros():
    rclpy.spin(node)


def main(args=None):
    global node

    rclpy.init(args=args)
    node = GuiBackend()

    # ROS runs in its own thread so it doesn't block the websocket server
    thread = threading.Thread(target=spin_ros, daemon=True)
    thread.start()

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
