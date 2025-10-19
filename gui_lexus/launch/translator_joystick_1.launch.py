from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='gui_lexus',
            executable='translator_joy_vel',
            output='screen',
            parameters=[
                {"input_device": "joystick1"},
                {"steer_gain": 6.0},
                {"accel_gain": 1.0},
                {"brake_gain": 1.0},
                {"accel_offset": 0.0},
                {"brake_offset": 0.0},
            ],
        ),
        # ros2 run joy joy_node 
        # ros2 param get joy_node device_id
        Node(
            package='joy',
            executable='joy_node',
            output='screen',
            # parameters=[
            #     {"autorepeat_rate": 20},
            #     {"device_id": "/dev/input/js0"},
            # ],
        ),
         

    ])
