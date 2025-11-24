from launch import LaunchDescription
import launch_ros.actions
import launch.actions

def generate_launch_description():
    parameters_file_path = '/home/abhiyaan-cu/ardc/src/Automated-Road-Dust-Collector/model_pkg/config/dual_ekf.yaml'
    
    return LaunchDescription([
        launch.actions.DeclareLaunchArgument(
            'output_final_position',
            default_value='false'),
        launch.actions.DeclareLaunchArgument(
            'output_location',
            default_value='~/dual_ekf_navsat_example_debug.txt'),
    
        launch_ros.actions.Node(
            package='robot_localization', 
            executable='ekf_node', 
            name='ekf_filter_node_odom',
            output='screen',
            parameters=[parameters_file_path, {'use_sim_time': True}],
            remappings=[('odometry/filtered', 'odometry/local')]           
        ),
        
        launch_ros.actions.Node(
            package='robot_localization', 
            executable='ekf_node', 
            name='ekf_filter_node_map',
            output='screen',
            parameters=[parameters_file_path, {'use_sim_time': True}],
            remappings=[('odometry/filtered', 'odometry/global')]
        ),
        
        launch_ros.actions.Node(
            package='robot_localization', 
            executable='navsat_transform_node', 
            name='navsat_transform',
            output='screen',
            parameters=[parameters_file_path, {'use_sim_time': True}],
            remappings=[('imu/data', 'imu/data'),
                        ('gps/fix', 'gps/fix'), 
                        ('gps/filtered', 'gps/filtered'),
                        ('odometry/gps', 'odometry/gps'),
                        ('odometry/filtered', 'odometry/global')]           
        )
    ])
