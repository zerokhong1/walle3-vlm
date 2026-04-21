"""sim_warehouse.launch.py — Launch simulation with VinMotion warehouse world.

Identical to sim.launch.py except:
  - World: walle_warehouse.sdf (20×15m warehouse with racks, pallets, forklift)
  - Default spawn: (1.0, 7.5, 0.0) — Zone A, facing Zone B (east)
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, RegisterEventHandler
from launch.conditions import IfCondition, UnlessCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command, FindExecutable, LaunchConfiguration,
    PathJoinSubstitution,
)
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time     = LaunchConfiguration('use_sim_time')
    start_demo       = LaunchConfiguration('start_demo')
    start_perception = LaunchConfiguration('start_perception')
    start_vlm        = LaunchConfiguration('start_vlm')
    headless         = LaunchConfiguration('headless')
    x = LaunchConfiguration('x')
    y = LaunchConfiguration('y')
    z = LaunchConfiguration('z')

    controllers_file = PathJoinSubstitution([
        FindPackageShare('walle_bringup'), 'config', 'controllers.yaml',
    ])
    bridge_file = PathJoinSubstitution([
        FindPackageShare('walle_bringup'), 'config', 'bridge.yaml',
    ])
    world_file = PathJoinSubstitution([
        FindPackageShare('walle_bringup'), 'worlds', 'walle_warehouse.sdf',
    ])
    xacro_file = PathJoinSubstitution([
        FindPackageShare('walle_description'), 'urdf', 'walle.urdf.xacro',
    ])

    robot_description_content = ParameterValue(
        Command([
            PathJoinSubstitution([FindExecutable(name='xacro')]),
            ' ', xacro_file,
            ' ', 'controllers_file:=', controllers_file,
        ]),
        value_type=str,
    )

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[
            {'use_sim_time': use_sim_time},
            {'robot_description': robot_description_content},
        ],
    )

    gazebo_headless = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments={'gz_args': ['-s -r -v 2 ', world_file]}.items(),
        condition=IfCondition(headless),
    )

    gazebo_gui = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([
            PathJoinSubstitution([FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])
        ]),
        launch_arguments={'gz_args': ['-r -v 2 ', world_file]}.items(),
        condition=UnlessCondition(headless),
    )

    spawn_entity = Node(
        package='ros_gz_sim',
        executable='create',
        output='screen',
        arguments=[
            '-topic', 'robot_description',
            '-name', 'walle',
            '-x', x, '-y', y, '-z', z,
            '-allow_renaming', 'false',
        ],
    )

    bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        output='screen',
        parameters=[{'config_file': bridge_file}],
    )

    joint_state_broadcaster = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['joint_state_broadcaster'],
        output='screen',
    )
    diff_drive_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['diff_drive_base_controller', '--param-file', controllers_file],
        output='screen',
    )
    head_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['head_controller', '--param-file', controllers_file],
        output='screen',
    )
    arm_controller = Node(
        package='controller_manager',
        executable='spawner',
        arguments=['arm_controller', '--param-file', controllers_file],
        output='screen',
    )

    cmd_vel_mux_node = Node(
        package='walle_demo', executable='cmd_vel_mux', output='screen',
        condition=IfCondition(start_demo),
        parameters=[{'use_sim_time': use_sim_time}],
    )
    stuck_watchdog_node = Node(
        package='walle_demo', executable='stuck_watchdog', output='screen',
        condition=IfCondition(start_demo),
        parameters=[{'use_sim_time': use_sim_time}],
    )
    wander_node = Node(
        package='walle_demo', executable='wander', output='screen',
        condition=IfCondition(start_demo),
        parameters=[{'use_sim_time': use_sim_time}],
    )
    expressive_node = Node(
        package='walle_demo', executable='expressive', output='screen',
        condition=IfCondition(start_demo),
        parameters=[{'use_sim_time': use_sim_time}],
    )
    perception_node = Node(
        package='walle_demo', executable='perception', output='screen',
        condition=IfCondition(start_perception),
        parameters=[{
            'use_sim_time': use_sim_time,
            'model': 'yolov8n.pt',
            'confidence': 0.45,
            'device': 'cpu',
        }],
    )

    vlm_config = PathJoinSubstitution([
        FindPackageShare('walle_bringup'), 'config', 'vlm_config.yaml',
    ])
    vlm_planner_node = Node(
        package='walle_demo', executable='vlm_planner', output='screen',
        condition=IfCondition(start_vlm),
        parameters=[vlm_config, {'use_sim_time': use_sim_time}],
    )
    vlm_perception_node = Node(
        package='walle_demo', executable='vlm_perception', output='screen',
        condition=IfCondition(start_vlm),
        parameters=[vlm_config, {'use_sim_time': use_sim_time}],
    )
    language_interface_node = Node(
        package='walle_demo', executable='language_interface', output='screen',
        condition=IfCondition(start_vlm),
        parameters=[{'use_sim_time': use_sim_time}],
        emulate_tty=True,
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time',     default_value='true',  description='Use Gazebo clock'),
        DeclareLaunchArgument('start_demo',       default_value='false', description='Start wander + expressive nodes'),
        DeclareLaunchArgument('start_perception', default_value='false', description='Start YOLOv8 perception node'),
        DeclareLaunchArgument('start_vlm',        default_value='false', description='Start VLM stack (Qwen2.5-VL)'),
        DeclareLaunchArgument('headless',         default_value='true',  description='Server-only (no Gazebo GUI)'),
        # Default spawn: Zone A, facing east toward Zone B
        DeclareLaunchArgument('x', default_value='1.0',  description='Initial X (Zone A)'),
        DeclareLaunchArgument('y', default_value='7.5',  description='Initial Y (center aisle)'),
        DeclareLaunchArgument('z', default_value='0.25', description='Initial Z'),

        robot_state_publisher,
        gazebo_headless,
        gazebo_gui,
        bridge,
        spawn_entity,

        RegisterEventHandler(OnProcessExit(
            target_action=spawn_entity,
            on_exit=[joint_state_broadcaster],
        )),
        RegisterEventHandler(OnProcessExit(
            target_action=joint_state_broadcaster,
            on_exit=[
                diff_drive_controller, head_controller, arm_controller,
                cmd_vel_mux_node, stuck_watchdog_node,
                wander_node, expressive_node, perception_node,
                vlm_planner_node, vlm_perception_node, language_interface_node,
            ],
        )),
    ])
