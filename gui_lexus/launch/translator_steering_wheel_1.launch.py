from launch import LaunchDescription
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='gui_lexus',
            executable='translator_joy_vel',
            output='screen',
            parameters=[
                {"input_device": "steering_wheel1"},
                {"steer_gain": 5.2},
                {"accel_gain": -1.0},
                {"brake_gain": -1.0},
                {"accel_offset": 1.0},
                {"brake_offset": 1.0},
            ],
        ),
        # ros2 run joy joy_node 
        # ros2 param get joy_node device_id
        # ros2 param get /joy_node deadzone
        Node(
            package='joy',
            executable='joy_node',
            output='screen',
            parameters=[
                {
                    # "autorepeat_rate": 20,
                    # "device_id": "/dev/input/js0",
                    "deadzone": 0.01,
                    # "qos_history": "keep_last",
                    # "qos_history_depth": 2,
                    # "qos_reliability": "best_effort",                   
                }
            ],
        ),
    ])
