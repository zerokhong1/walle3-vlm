from setuptools import find_packages, setup

package_name = 'walle_demo'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Cong Thai',
    maintainer_email='sunshinforwho@gmail.com',
    description='Autonomy and expressive behavior nodes for the WALL-E inspired robot.',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'wander = walle_demo.wander:main',
            'expressive = walle_demo.expressive:main',
            'perception = walle_demo.perception:main',
            'vlm_planner = walle_demo.vlm_planner:main',
            'vlm_perception = walle_demo.vlm_perception:main',
            'language_interface = walle_demo.language_interface:main',
            'mission_logger = walle_demo.mission_logger_node:main',
            'cmd_vel_mux = walle_demo.cmd_vel_mux:main',
            'stuck_watchdog = walle_demo.stuck_watchdog_node:main',
            'rosbag_trigger = walle_demo.rosbag_trigger_node:main',
            'walle_terminal = walle_demo.walle_terminal:main',
        ],
    },
)
