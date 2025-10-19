import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8
from std_msgs.msg import Float64MultiArray,Bool
from geometry_msgs.msg import Twist

import time
import tty
import sys
import termios
import signal
import os


class stopper(Node):
    def __init__(self):
        super().__init__("dstop")
        self.stop = False
        self.stop_pub = self.create_publisher(Bool,'stop', 10)
        if(self.stop):
            print("Press ':' to remove the estop")
        else:
            print("Press any key to overwrite velocity setpoint to 0")
        
        # Get the current terminal setting, store fr=or the case where we exit program
        self.setting = termios.tcgetattr(sys.stdin)

        # Allow for single character read by terminal (no need to hit enter)
        tty.setcbreak(sys.stdin)

        # Stores input character
        self.x = None 

        # Disable control C from directly exiting program as this causes issues with terminal. Instead we redirect to self.handler
        signal.signal(signal.SIGINT, self.handler)

          
        # Loop to read keystroke
        while True:
            if(self.stop):
                print("Press ':' to remove the estop")
            else:
                print("Press any key to overwrite velocity setpoint to 0")
            # Blocking, waits till character is input
            self.x = sys.stdin.read(1)[0]
            
            # If key is : while estop is engaged then disengage it
            # Any other case: engage Estop
            if self.x:
                if(self.x == ':' and self.stop):
                    self.stop = False
                else:
                    self.stop = True

                msg = Bool()
                msg.data = self.stop
                self.stop_pub.publish(msg)

    def handler(self, signum, frame):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.setting)
        exit()

def main(args = None):
    rclpy.init(args = args)
    dstop= stopper()
    rclpy.spin(dstop)
    dstop.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()