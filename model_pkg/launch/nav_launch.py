import os

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

pkg_model = get_package_share_directory('model_pkg')
pkg_patchworkpp = get_package_share_directory('patchworkpp')

paths = {
    'pkg_model': pkg_model,
    'urdf': os.path.join(pkg_model, 'model', 'ardc_urdf.xacro'),
    'world': os.path.join(pkg_model, 'model', 'world.world'),
    'rviz_config': os.path.join(pkg_model, 'rviz', 'rviz_basic_settings.rviz'),
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

    # Robot description from xacro
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
        cwd=[paths['pkg_model']],
        output='screen',
    )

    start_gazebo_client_cmd = ExecuteProcess(
        cmd=['gzclient'],
        cwd=[paths['pkg_model']],
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

    nav_bringup = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_model, 'launch', 'bringup_launch.py')
        ),
    )

    # ---------------- Build LaunchDescription ----------------

    ld = LaunchDescription()

    # Launch arguments
    for arg in get_launch_arguments(paths['urdf'], paths['rviz_config']):
        ld.add_action(arg)

    # Gazebo (server + client)
    ld.add_action(start_gazebo_server_cmd)
    ld.add_action(start_gazebo_client_cmd)

    # Robot + tools
    ld.add_action(spawn_model_node)
    ld.add_action(robot_state_publisher_node)
    ld.add_action(joint_state_publisher_node)
    ld.add_action(rviz_node)
    ld.add_action(ekf_launch)
    ld.add_action(patchwork_pp_launch)
    ld.add_action(nav_bringup)

    return ld
