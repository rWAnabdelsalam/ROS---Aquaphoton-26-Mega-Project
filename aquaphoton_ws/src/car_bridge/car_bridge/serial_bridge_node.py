#!/usr/bin/env python3
# Reads JSON telemetry from the car over serial and publishes it to ROS.
# Takes commands from ROS and sends them as text lines to the car.

import json

import rclpy
from rclpy.node import Node
import serial

from car_interfaces.msg import SensorReadings, MotionCommand


# what the car sends back
STATE_TO_NUMBER = {
    "STOPPED": 0, "FORWARD": 1, "BACKWARD": 2, "LEFT": 3, "RIGHT": 4
}
MODE_TO_NUMBER = {"MANUAL": 0, "AUTO": 1}
PWM_TO_LEVEL = {100: 0, 180: 1, 255: 2}

# what we send to the car
NUMBER_TO_DIRECTION = {
    0: "CMD:STOP", 1: "CMD:FORWARD", 2: "CMD:BACKWARD",
    3: "CMD:LEFT", 4: "CMD:RIGHT"
}
NUMBER_TO_SPEED = {0: "SPD:LOW", 1: "SPD:MED", 2: "SPD:HIGH"}
NUMBER_TO_MODE = {0: "MODE:MANUAL", 1: "MODE:AUTO"}

# the IMU sends raw numbers, these turn them into real units
ACCEL_SCALE = 16384.0
GYRO_SCALE = 131.0


class SerialBridge(Node):

    def __init__(self):
        super().__init__('serial_bridge')

        self.declare_parameter('port', '/dev/ttyACM0')
        self.port = self.get_parameter('port').value

        self.ser = None
        self.data = ""

        # remember what we last sent so we don't repeat mode and speed
        self.lastMode = None
        self.lastSpeed = None

        self.pub = self.create_publisher(SensorReadings, '/car/sensors', 10)
        self.create_subscription(MotionCommand, '/car/motion_command',
                                 self.got_command, 10)

        self.create_timer(0.02, self.check_serial)
        self.create_timer(2.0, self.connect)

        self.connect()

    def connect(self):
        if self.ser is not None:
            return

        try:
            self.ser = serial.Serial(self.port, 115200, timeout=0)
            self.data = ""
            self.lastMode = None
            self.lastSpeed = None
            self.get_logger().info("Connected to " + self.port)
        except serial.SerialException:
            self.ser = None
            self.get_logger().warning("Waiting for " + self.port,
                                      throttle_duration_sec=5.0)

    def lost_connection(self):
        self.get_logger().warning("Lost serial connection")
        if self.ser is not None:
            self.ser.close()
        self.ser = None

        msg = SensorReadings()
        msg.valid = False
        self.pub.publish(msg)

    def check_serial(self):
        if self.ser is None:
            return

        try:
            new = self.ser.read(512).decode('ascii', errors='ignore')
        except (serial.SerialException, OSError):
            self.lost_connection()
            return

        if new == "":
            return

        self.data = self.data + new

        # the car sends one json object per line
        while "\n" in self.data:
            line, self.data = self.data.split("\n", 1)
            self.read_line(line.strip())

        # if something went wrong and we never see a newline,
        # don't let the buffer grow forever
        if len(self.data) > 500:
            self.data = ""

    def read_line(self, line):
        if not line.startswith("{"):
            return

        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            return

        try:
            msg = SensorReadings()
            msg.voltage = float(d["voltage"])
            msg.current = float(d["current"])
            msg.ax = float(d["ax"]) / ACCEL_SCALE
            msg.ay = float(d["ay"]) / ACCEL_SCALE
            msg.az = float(d["az"]) / ACCEL_SCALE
            msg.gx = 0.0
            msg.gy = 0.0
            msg.gz = float(d["gz"]) / GYRO_SCALE
            msg.mode = MODE_TO_NUMBER.get(d["mode"], 0)
            msg.direction = STATE_TO_NUMBER.get(d["state"], 0)
            msg.speed = PWM_TO_LEVEL.get(int(d["speed"]), 1)
            msg.valid = True
            msg.distance = float(d.get("distance", 0.0))
        except (KeyError, ValueError):
            return

        self.pub.publish(msg)

    def send_line(self, text):
        try:
            self.ser.write((text + "\n").encode('ascii'))
        except (serial.SerialException, OSError):
            self.lost_connection()
            return False
        return True

    def got_command(self, msg):
        if msg.mode > 1 or msg.direction > 4 or msg.speed > 2:
            self.get_logger().warning("Bad command, ignoring it")
            return

        if self.ser is None:
            self.get_logger().warning("No serial connection, command dropped",
                                      throttle_duration_sec=5.0)
            return

        # mode and speed only change occasionally, so only send them
        # when they're different
        if msg.mode != self.lastMode:
            if not self.send_line(NUMBER_TO_MODE[msg.mode]):
                return
            self.lastMode = msg.mode

        if msg.speed != self.lastSpeed:
            if not self.send_line(NUMBER_TO_SPEED[msg.speed]):
                return
            self.lastSpeed = msg.speed

        if not self.send_line(NUMBER_TO_DIRECTION[msg.direction]):
            return

        self.get_logger().info("Sent: %s %s"
                               % (NUMBER_TO_DIRECTION[msg.direction],
                                  NUMBER_TO_SPEED[msg.speed]))


def main(args=None):
    rclpy.init(args=args)
    node = SerialBridge()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
