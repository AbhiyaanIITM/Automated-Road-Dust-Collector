from setuptools import find_packages, setup

package_name = 'tools_elec'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='igvc2024',
    maintainer_email='ee22b069@smail.iitm.ac.in',
    description='TODO: Package description',
    license='TODO: License declaration',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'pulses_sum = tools_elec.pulses_sum:main',
            'keystroke = tools_elec.keystroke:main',
            'monitor = tools_elec.monitor:main',
            'dstop = tools_elec.dstop:main',
            'joystick = tools_elec.joystick:main',
            'thr_keystroke = tools_elec.thr_keystroke:main',
            'lightcontroller = tools_elec.LED:main'
        ],
    },
)
