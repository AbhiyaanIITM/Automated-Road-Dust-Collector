from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='gui_lexus',
            executable='gui_ros',
            output='screen',
            parameters=[
                {"buttons": "autoware_buttons.json"},
            ],
        )
    ])
