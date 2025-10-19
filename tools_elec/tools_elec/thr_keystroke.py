import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8
from std_msgs.msg import Int64MultiArray,Bool
from geometry_msgs.msg import Twist

import time
import tty
import sys
import termios
import signal
import os

class timed_publisher(Node):
    def __init__(self,name,frequency):
        self.name = name
        self.frequency = frequency

        super().__init__(self.name)
        period = int(1/frequency)
        
        self.stop = False

        # Make a publisher to setpoint topic. Data type is Float array of format [LeftSetpoint, RightSetpoint]
        self.rpm_setpoint_pub = self.create_publisher(Int64MultiArray,'thr', 10)
        self.setpoint = Int64MultiArray()     
        self.setpoint.data = [0, 0]

        self.stop_sub = self.create_subscription(Bool,'stop',self.dstop_callback,10)
        
        # Make a publisher to estop topic. Data type is Int8. 0 if disengage and 1 if engage Estop.
        self.pub_Estop = self.create_publisher(Int8,'estop', 10)
        self.estop = Int8()
        self.estop.data = 1

        # Amount to decrease/increase the wheel RPM for each keystroke.
        # In case of differential steering, we use step/2 for adjustment to the RPM.
        self.step = 20

        print("\nRoboteq Keystroke")
        print(f"W :  Increase both throttle by {self.step} | S :  Decrease both throttle by {self.step} ")
        print(f"Q :  Increase left throttle by {self.step} | A :  Decrease left throttle by {self.step} ")
        print(f"E : Increase right throttle by {self.step} | A : Decrease right throttle by {self.step} ")
        print("Any other key : estop\n\n")
        
        # Get the current terminal setting, store fr=or the case where we exit program
        self.setting = termios.tcgetattr(sys.stdin)

        # Allow for single character read by terminal (no need to hit enter)
        tty.setcbreak(sys.stdin)

        # Stores input character
        self.x = None 

        # Disable control C from directly exiting program as this causes issues with terminal. Instead we redirect to self.handler
        signal.signal(signal.SIGINT, self.handler)

        self.setpoint.data = [0, 0]
        self.rpm_setpoint_pub.publish(self.setpoint)

        self.estop.data = 1
        self.pub_Estop.publish(self.estop)
        self.estop.data = 0

        print("Estop engaged. Press : to exit")      
          
        # Loop to read keystroke
        while True:
            # Blocking, waits till character is input
            self.x = sys.stdin.read(1)[0]
            
            # If mode is 1 go to Individual Throttle and if mode is 2 go to Differential Drive
            if self.x:
                self.KbPress(self.x)
    
    def dstop_callback(self,msg):
        print("rec")
        if(msg.data == True):
            self.setpoint.data = [0,0]
        self.stop = msg.data

    def handler(self, signum, frame):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.setting)
        self.setpoint.data = [0, 0]
        self.rpm_setpoint_pub.publish(self.setpoint)
        exit()

    def KbPress(self, key):
        # Clears above line in terminal output and goes to start of that line.
        print("\033[A                                                                    \033[A")
        
        if (self.estop.data) and key == 'w':
            self.setpoint.data[0] += self.step
            self.setpoint.data[1] += self.step
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)

        elif (self.estop.data) and key == 's':
            self.setpoint.data[0] -= self.step
            self.setpoint.data[1] -= self.step
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)
            
        elif (self.estop.data) and key == 'q':
            self.setpoint.data[0] += self.step
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)

        elif (self.estop.data) and key == 'a':
            self.setpoint.data[0] -= self.step
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)

        elif (self.estop.data) and key == 'e':
            self.setpoint.data[1] += self.step
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)

        elif (self.estop.data) and key == 'd':
            self.setpoint.data[1] -= self.step
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)

        elif (self.estop.data) and key == ' ':
            self.setpoint.data = [0, 0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])

        elif key == ':' and not self.estop.data:
            self.pub_Estop.publish(self.estop)
            self.estop.data = 1
            print("Estop disengaged.")
        
        elif (self.estop.data) and key == " ":
            self.setpoint.data = [0, 0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])

        elif key == '1':
            pass

        else:
            self.setpoint.data = [0, 0]
            self.rpm_setpoint_pub.publish(self.setpoint)

            self.estop.data = 1
            self.pub_Estop.publish(self.estop)
            self.estop.data = 0

            print("Estop engaged. Press : to exit")
        print("RPM control mode")

def main(args = None):
    rclpy.init(args = args)
    ks = timed_publisher('thr_keystroke',1)
    rclpy.spin(ks)
    ks.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()