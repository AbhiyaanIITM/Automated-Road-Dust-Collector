# 9th December 2025
Updated nav_params

### TODO
1. Experiment with nav servers and controllers to find a best way to follow path as well as avoid obstacles. (Need to test route-server + MPPI controller configuration)

# 8th December 2025

### Update
Succesfully integrated navigate_to_pose action with coverage_planner. Added coverage_navigator.py file that gets the path coverage_planner node and calls navigate_to_pose to follow the path. 

Not tuned nav params, so it doesnt follow the path properly yet, but navigate_to_pose call works.

### TODO
1. Tune Nav params
2. Experiment with nav servers and controllers to find a best way to follow path as well as avoid obstacles. (Need to test route-server + MPPI controller configuration)

##  25 November 2025 

### Update
Integrated the `opennav_coverage` package with the simulator.

### Current Issues / TODO
1. Robot does not execute turns correctly when navigating using Nav2.
2. Robot moves outside the roadway boundary during turning maneuvers.
3. Obstacle avoidance is not functioning as expected; the robot stops upon detecting obstacles instead of replanning.

### Dependencies
| Package | Notes | Repository |
|--------|------|-------------|
| Field2Cover | Use branch: `v1.2.1-devel` | https://github.com/Fields2Cover/Fields2Cover |
| livox_ros_driver2 | Required for Livox LiDAR integration | (provide specific repository link if applicable) |

### Launch Coverage Planner
```bash
ros2 launch opennav_coverage_demo coverage_ardc.launch.py
```

### Launch Nav Bringup Only
```bash
ros2 launch model_pkg nav_launch.py
```

### Launch Simulation Only
```bash
ros2 launch model_pkg model_launch.py

```
## 17 October 2025

### Simulation Setup
Download required Gazebo models here: [https://github.com/osrf/gazebo_models](https://github.com/osrf/gazebo_models)  
Copy all the models to `$HOME/.gazebo/models`

Update the launch file to use robot.xacro and world.world for now.


