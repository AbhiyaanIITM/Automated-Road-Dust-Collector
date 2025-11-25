25/11/25 
  Integrated the opennav_coverage package with simulator. 

TODO:
    1. Something's wrong with nav2, bot doesn't turn!!
    2. It goes out of the road for turns.
    3. Doesn't avoid obstacles. It just stops when it sees one.

DEPENDENCIES:
    1. Field2Cover : https://github.com/Fields2Cover/Fields2Cover (switch to v1.2.1-devel branch)
    2. livox_ros_driver2
    
launch command:
  ros2 launch opennav_coverage_demo coverage_ardc.launch.py

--------------------------------------------------------------------------------------------------------------------------------------------
Download required Gazebo models here: [https://github.com/osrf/gazebo_models](https://github.com/osrf/gazebo_models)  
Copy all the models to `$HOME/.gazebo/models`

Update the launch file to use robot.xacro and world.world for now.


