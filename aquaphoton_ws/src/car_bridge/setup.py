import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'car_bridge'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*.launch.py'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='rorrgilmore',
    maintainer_email='rorrgilmore@todo.todo',
    description='Serial and ROS bridge for the car',
    license='TODO',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'serial_bridge = car_bridge.serial_bridge_node:main',
            'gui_backend = car_bridge.gui_backend_node:main',
        ],
    },
)
