"""vlm.launch.py — Launch VLM stack (without starting Gazebo).

Use when simulation is already running and you only need VLM nodes:
  ros2 launch walle_bringup vlm.launch.py

Or integrated via sim.launch.py with start_vlm:=true
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    start_perception = LaunchConfiguration('start_vlm_perception')

    vlm_config = PathJoinSubstitution([
        FindPackageShare('walle_bringup'), 'config', 'vlm_config.yaml',
    ])

    vlm_planner_node = Node(
        package='walle_demo',
        executable='vlm_planner',
        name='walle_vlm_planner',
        output='screen',
        parameters=[
            vlm_config,
            {'use_sim_time': use_sim_time},
        ],
    )

    vlm_perception_node = Node(
        package='walle_demo',
        executable='vlm_perception',
        name='walle_vlm_perception',
        output='screen',
        condition=IfCondition(start_perception),
        parameters=[
            vlm_config,
            {'use_sim_time': use_sim_time},
        ],
    )

    language_interface_node = Node(
        package='walle_demo',
        executable='language_interface',
        name='walle_language_interface',
        output='screen',
        parameters=[{'use_sim_time': use_sim_time}],
        # stdin forwarding for interactive terminal
        emulate_tty=True,
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='Use Gazebo simulation clock'),
        DeclareLaunchArgument(
            'start_vlm_perception', default_value='false',
            description='Also start VLM perception node (shares GPU with planner)'),

        vlm_planner_node,
        vlm_perception_node,
        language_interface_node,
    ])
