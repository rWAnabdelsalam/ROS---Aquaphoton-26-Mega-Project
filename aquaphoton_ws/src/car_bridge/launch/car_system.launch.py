# Starts both nodes of the communication subsystem together.

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    serial_bridge = Node(
        package='car_bridge',
        executable='serial_bridge',
        name='serial_bridge',
        output='screen',
        parameters=[{'port': '/dev/ttyACM0'}],
    )

    gui_backend = Node(
        package='car_bridge',
        executable='gui_backend',
        name='gui_backend',
        output='screen',
    )

    return LaunchDescription([serial_bridge, gui_backend])
