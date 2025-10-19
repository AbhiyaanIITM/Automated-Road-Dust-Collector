import os
from glob import glob
from setuptools import setup

package_name = 'gui_lexus'

setup(
    name=package_name,
    version='0.0.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'readfiles'), glob('readfiles/*.json')),     
        (os.path.join('share', package_name, 'img'), glob('img/*.png')),     
        (os.path.join('share', package_name), glob('launch/*launch.[pxy][yma]*')),        
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='he',
    maintainer_email='horverno@g.com',
    description='Simple lexus ROS2 GUI',
    license='BSD 3-Clause License',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'control_vehicle = gui_lexus.control_vehicle:main',
            'pub_lane_markers = gui_lexus.pub_lane_markers:main',
            'translator_joy_vel = gui_lexus.translator_joy_vel:main',
            'gui_ros = gui_lexus.gui_ros:main'
        ],
    },
)
