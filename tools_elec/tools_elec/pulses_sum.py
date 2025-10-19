#Import the usual libraries

import rclpy
from rclpy.node import Node
import math
import queue
import time

from std_msgs.msg import Float64MultiArray
#from virat_msgs.msg import WheelVel
import numpy as np

#Class to take enc input and publish odom output
class OdomOutput(Node):

    def __init__(self , odom_topic: str = 'enc_odom' , wheel_vel_topic: str = 'wheel_vel' , rate: int = 50):
        super().__init__('pulses_sum')

        # Subscribe to the enc_RPM topic. Data is Float array, of format [LeftRPM, RightRPM]
        self.rpm_sub = self.create_subscription(
            Float64MultiArray,
            'enc_pulses',
            self.rpm_callback,
            10
        )
        self.rpm_sub
        self.rpm = Float64MultiArray()
        self.rpm.data = [0.0, 0.0]

        self.sumL = 0
        self.sumR = 0

    def rpm_callback(self, msg):
        self.rpm = msg
        
        self.sumL += self.rpm.data[0]
        self.sumR += self.rpm.data[1]

        print(self.sumL, self.sumR)


def main(args=None):
    rclpy.init(args=args)

    pulses_sum = OdomOutput()

    rclpy.spin(pulses_sum)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    pulses_sum.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
