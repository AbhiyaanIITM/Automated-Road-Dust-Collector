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

class timed_publisher(Node):
    def __init__(self,name,frequency):
        self.name = name
        self.frequency = frequency

        super().__init__(self.name)
        period = int(1/frequency)
        
        self.stop = False

        # Make a publisher to setpoint topic. Data type is Float array of format [LeftSetpoint, RightSetpoint]
        self.rpm_setpoint_pub = self.create_publisher(Float64MultiArray,'setpoint', 10)
        self.setpoint = Float64MultiArray()     
        self.setpoint.data = [0.0, 0.0]
        self.stop_sub = self.create_subscription(Bool,'stop',self.dstop_callback,10)
        self.vel_setpoint_pub = self.create_publisher(Twist,'/cmd_vel', 10)
        self.vels = Twist()
        self.vels.linear.x = 0.0
        self.vels.linear.y = 0.0
        self.vels.linear.z = 0.0
        self.vels.angular.x = 0.0
        self.vels.angular.y = 0.0
        self.vels.angular.z = 0.0
        
        # Make a publisher to estop topic. Data type is Int8. 0 if disengage and 1 if engage Estop.
        self.pub_Estop = self.create_publisher(Int8,'estop', 10)
        self.estop = Int8()
        self.estop.data = 1
        # Make a publisher for Odom Reset
        self.odom_reset = self.create_publisher(Bool,'O_reset',10)
        self.reset = Bool()
        self.reset.data = False
        # Switch between Differential Drive Mode and Individual Throttle Mode.
        # 1 is Individual Throttle
        # 2 is Differential Drive
        self.mode = 2

        # Amount to decrease/increase the wheel RPM for each keystroke.
        # In case of differential steering, we use step/2 for adjustment to the RPM.
        self.step = 10
        self.v_step = 0.25
        self.w_step = 0.015625*4

        print("\nRoboteq Keystroke")
        print("Press 2 to switch to Differential Drive , and 1 to switch back to rpm control")
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

        self.setpoint.data = [0.0, 0.0]
        self.reset_vels()
        self.rpm_setpoint_pub.publish(self.setpoint)
        self.vel_setpoint_pub.publish(self.vels)

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
                if(self.mode == 1):
                    self.individualThrottleKbPress(self.x)

                elif(self.mode == 2):
                    self.differentialDriveKbPress(self.x)
    
    def dstop_callback(self,msg):
        print("rec")
        if(msg.data == True):
            self.reset_vels()
            self.setpoint.data = [0.0,0.0]
        self.stop = msg.data
    
    
    def reset_vels(self):
        self.vels.linear.x = 0.0
        self.vels.linear.y = 0.0
        self.vels.linear.z = 0.0
        self.vels.angular.x = 0.0
        self.vels.angular.y = 0.0
        self.vels.angular.z = 0.0
    
    def set_vels(self):
        self.vels.linear.x = self.setpoint.data[0]
        self.vels.linear.y = 0.0
        self.vels.linear.z = 0.0
        self.vels.angular.x = 0.0
        self.vels.angular.y = 0.0
        self.vels.angular.z = self.setpoint.data[1]

    def handler(self, signum, frame):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.setting)
        self.setpoint.data = [0.0, 0.0]
        self.reset_vels()
        self.rpm_setpoint_pub.publish(self.setpoint)
        self.vel_setpoint_pub.publish(self.vels)
        exit()
    
    def differentialDriveKbPress(self,key):

        # Clears above line in terminal output and goes to start of that line.
        print("\033[A                                                                    \033[A")
        if(self.stop):
            print("Digital stop engaged")
        elif (self.estop.data) and key == 'w':
            self.setpoint.data[0] += self.v_step
            self.set_vels()
            print("Setpoint is V :", self.setpoint.data[0], "and W :", self.setpoint.data[1])
            self.vel_setpoint_pub.publish(self.vels)

        elif (self.estop.data) and key == 's':
            self.setpoint.data[0] -= self.v_step
            self.set_vels()
            print("Setpoint is V :", self.setpoint.data[0], "and W :", self.setpoint.data[1])
            self.vel_setpoint_pub.publish(self.vels)

        elif (self.estop.data) and key == 'd':
            self.setpoint.data[1] -= self.w_step
            self.set_vels()
            print("Setpoint is V :", self.setpoint.data[0], "and W :", self.setpoint.data[1])
            self.vel_setpoint_pub.publish(self.vels)


        elif (self.estop.data) and key == 'a':
            self.setpoint.data[1] += self.w_step
            self.set_vels()
            print("Setpoint is V :", self.setpoint.data[0], "and W :", self.setpoint.data[1])
            self.vel_setpoint_pub.publish(self.vels)
        
        elif (self.estop.data) and key == 'f':
            self.setpoint.data[1] = 0.0
            self.set_vels()
            print("Setpoint is V :", self.setpoint.data[0], "and W :", self.setpoint.data[1])
            self.vel_setpoint_pub.publish(self.vels)

        elif key == ':' and not self.estop.data:
            self.pub_Estop.publish(self.estop)
            self.estop.data = 1
            print("Estop disengaged.")
        
        elif (self.estop.data) and key == ' ':
            self.setpoint.data = [0.0, 0.0]
            self.reset_vels()
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)
            print("Setpoint is V :", self.setpoint.data[0], "and W :", self.setpoint.data[1])

        
        elif key == 'o':
            self.setpoint.data = [0.0,0.0]
            self.reset.data = True
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)
            self.odom_reset.publish(self.reset)
        elif key == '1':
            self.mode = 1
            self.setpoint.data = [0.0,0.0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)
            self.reset_vels()

        elif key == '2':
            pass

        else:
            self.setpoint.data = [0.0, 0.0]
            self.reset_vels()
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)

            self.estop.data = 1
            self.pub_Estop.publish(self.estop)
            self.estop.data = 0

            print("Estop engaged. Press : to exit")
        print("Differential drive mode")


    def individualThrottleKbPress(self, key):
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
            self.setpoint.data = [0.0, 0.0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)

            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])
            self.rpm_setpoint_pub.publish(self.setpoint)

        elif key == ':' and not self.estop.data:
            self.pub_Estop.publish(self.estop)
            self.estop.data = 1
            print("Estop disengaged.")

        elif key == 'o':
            self.setpoint.data = [0.0,0.0]
            self.reset.data = True
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)
            self.odom_reset.publish(self.reset)
        elif key == '2':
            self.mode = 2
            self.setpoint.data = [0.0,0.0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)
            self.reset_vels()
        
        elif (self.estop.data) and key == " ":
            self.setpoint.data = [0.0, 0.0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)
            print("Setpoint is L :", self.setpoint.data[0], "and R :", self.setpoint.data[1])

        elif key == '1':
            pass

        else:
            self.setpoint.data = [0.0, 0.0]
            self.rpm_setpoint_pub.publish(self.setpoint)
            self.vel_setpoint_pub.publish(self.vels)

            self.estop.data = 1
            self.pub_Estop.publish(self.estop)
            self.estop.data = 0

            print("Estop engaged. Press : to exit")
        print("RPM control mode")

def main(args = None):
    rclpy.init(args = args)
    ks = timed_publisher('keystroke',1)
    rclpy.spin(ks)
    ks.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()
