from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='gui_lexus',
            executable='gui_ros',
            name='gui_ros_lexus1',
            output='screen',
            parameters=[
                {"buttons": "lexus_buttons.json"},
            ],
        )
    ])
