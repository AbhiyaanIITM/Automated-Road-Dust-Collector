#!/usr/bin/python3
import os
import sys

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import Node
from launch.launch_description_sources import PythonLaunchDescriptionSource

import xacro


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

# Helper function to safely get package share directory and check for None
def get_share_directory_or_exit(pkg_name):
    """Safely retrieves the package share directory or exits if not found."""
    try:
        share_dir = get_package_share_directory(pkg_name)
    except Exception as e:
        print(f"Error finding package '{pkg_name}': {e}", file=sys.stderr)
        share_dir = None

    if share_dir is None:
        print(
            f"\n\nFATAL ERROR: Package '{pkg_name}' not found. "
            f"Please ensure the package is built and the ROS 2 environment is sourced.\n",
            file=sys.stderr
        )
        raise SystemExit(1)
    print(pkg_name, "retrieved succefully")
    return share_dir

# Retrieve package directories
pkg_model = get_share_directory_or_exit('model_pkg')
pkg_patchworkpp = get_share_directory_or_exit('patchworkpp')
coverage_demo_dir = get_share_directory_or_exit('opennav_coverage_demo')


paths = {
    'pkg_model': pkg_model,
    'urdf': os.path.join(pkg_model, 'model', 'ardc_urdf.xacro'),
    'world': os.path.join(pkg_model, 'model', 'world.world'),
    'rviz_config': os.path.join(coverage_demo_dir, 'opennav_coverage_demo.rviz'),
    'bring_up': os.path.join(coverage_demo_dir, 'bringup_launch.py'),
    'gazebo_osm' : os.path.join(coverage_demo_dir, 'gazebo_map.osm'),
    'nav_param' : os.path.join(coverage_demo_dir, 'ardc_nav_params.yaml')
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_launch_arguments(default_urdf, default_rviz):
    """Declare launch arguments used in this file."""
    return [
        DeclareLaunchArgument(
            name='urdf_model',
            default_value=default_urdf,
            description='Absolute path to robot URDF (xacro) file',
        ),
        DeclareLaunchArgument(
            name='rviz_config_file',
            default_value=default_rviz,
            description='Full path to the RViz config file to use',
        ),
        DeclareLaunchArgument(
            name='gui',
            default_value='True',
            description='Flag to enable joint_state_publisher_gui',
        ),
        DeclareLaunchArgument(
            name='use_robot_state_pub',
            default_value='True',
            description='Whether to start the robot_state_publisher',
        ),
        DeclareLaunchArgument(
            name='use_rviz',
            default_value='True',
            description='Whether to start RViz',
        ),
        DeclareLaunchArgument(
            name='use_sim_time',
            default_value='True',
            description='Use simulation (Gazebo) clock if true',
        ),
    ]


# ---------------------------------------------------------------------------
# Main launch description
# ---------------------------------------------------------------------------

def generate_launch_description():

    # LaunchConfigurations
    use_sim_time = LaunchConfiguration('use_sim_time')
    use_gui = LaunchConfiguration('gui')
    use_robot_state_pub = LaunchConfiguration('use_robot_state_pub')
    use_rviz = LaunchConfiguration('use_rviz')

    rviz_config_file = LaunchConfiguration('rviz_config_file')
    robot_description_xml = xacro.process_file(paths['urdf']).toxml()
    common_params = {
        'robot_description': robot_description_xml,
        'use_sim_time': use_sim_time,
    }

    # ---------------- Gazebo server & client (like the example) ----------------
    start_gazebo_server_cmd = ExecuteProcess(
        cmd=[
            'gzserver',
            '-s', 'libgazebo_ros_init.so',
            '-s', 'libgazebo_ros_factory.so',
            paths['world'],
        ],
        cwd=paths['pkg_model'],
        output='screen',
    )

    start_gazebo_client_cmd = ExecuteProcess(
        cmd=['gzclient'],
        cwd=paths['pkg_model'],
        output='screen',
    )

    # ---------------- Robot + RViz + other includes ----------------

    spawn_model_node = Node(
        package='gazebo_ros',
        executable='spawn_entity.py',
        arguments=[
            '-topic', 'robot_description',
            '-entity', 'ardc_robot',
            '-x', '0.0',
            '-y', '0.0',
            '-z', '0.05',
        ],
        output='screen',
    )

    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        output='screen',
        parameters=[common_params],
        condition=IfCondition(use_robot_state_pub),
    )

    joint_state_publisher_node = Node(
        package='joint_state_publisher',
        executable='joint_state_publisher',
        name='joint_state_publisher',
        parameters=[common_params],
        condition=UnlessCondition(use_gui),
    )

    rviz_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', rviz_config_file],
        parameters=[{'use_sim_time': use_sim_time}],
        condition=IfCondition(use_rviz),
    )

    ekf_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_model, 'launch', 'ekf.launch.py')
        ),
    )

    patchwork_pp_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_patchworkpp, 'launch', 'demo.launch.py')
        ),
    )

    bringup_cmd = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(coverage_demo_dir, 'bringup_launch.py')),
        launch_arguments={'params_file': paths['nav_param']}.items())

    fake_localization_cmd = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        output='screen',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom']
    )

    demo_cmd = Node(
        package='opennav_coverage_demo',
        executable='coverage_navigator',
        emulate_tty=True,
        output='screen',
        parameters=[
            {'osm_file': paths['gazebo_osm']},
            {'frame_id': 'map'},
            {'origin_lat': 0.0},
            {'origin_lon': 0.0}
        ]
    )

    # ---------------- Build LaunchDescription ----------------

    ld = LaunchDescription()

    # Launch arguments
    for arg in get_launch_arguments(paths['urdf'], paths['rviz_config']):
        ld.add_action(arg)

    # Gazebo (server + client)
    ld.add_action(start_gazebo_server_cmd)
    ld.add_action(start_gazebo_client_cmd)

    # Robot + tools (Uncommented all actions)
    ld.add_action(spawn_model_node)
    ld.add_action(robot_state_publisher_node)
    ld.add_action(joint_state_publisher_node)
    ld.add_action(rviz_node)
    # ld.add_action(ekf_launch)
    ld.add_action(patchwork_pp_launch)
    ld.add_action(bringup_cmd)
    ld.add_action(fake_localization_cmd)
    ld.add_action(demo_cmd)

    return ld