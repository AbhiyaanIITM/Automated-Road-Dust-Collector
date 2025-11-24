import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, DeclareLaunchArgument
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from launch.substitutions import LaunchConfiguration
import launch

def generate_launch_description():
    pkg_nav2_bringup = get_package_share_directory('nav2_bringup')

    # Declare the use_sim_time argument to specify simulation time
    declare_use_sim_time = DeclareLaunchArgument(
        'use_sim_time',
        default_value='true',  # Set to 'true' for simulation time
        description='Use simulation time if true'
    )

    # Launch description object
    launchDescriptionObject = LaunchDescription([
        declare_use_sim_time,
        
        # Launch the navigation stack with simulation time
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(pkg_nav2_bringup, 'launch', 'navigation_launch.py')),
            launch_arguments={
                'params_file': "/home/abhiyaan-cu/ardc/src/Automated-Road-Dust-Collector/model_pkg/config/nav2_params.yaml",
                'use_sim_time': LaunchConfiguration('use_sim_time')  # Pass use_sim_time parameter to nav2
            }.items()
        ),
    ])

    return launchDescriptionObject
