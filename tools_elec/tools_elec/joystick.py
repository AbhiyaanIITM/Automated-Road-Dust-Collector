from evdev import InputDevice, categorize, ecodes, list_devices
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from std_msgs.msg import Int8

from time import sleep

class Joystick(Node):

    def __init__(self, controller):
        super().__init__('joystick')

        # Make a publisher to setpoint topic. Data type is Float array of format [LeftSetpoint, RightSetpoint]

        self.vel_setpoint_pub = self.create_publisher(Twist,'cmd_vel_nav', 10)
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

        # Define the name of controller here with a parameter.
        self.declare_parameter('controller', controller)
        self.started = False
        # Get the value of port parameter
        self.controllerName = self.get_parameter('controller').get_parameter_value().string_value

        # evdev device object
        self.dev = 0

        # If 1 brakes are not applied, if 0 brakes are on
        self.brake_status = 1

        # High speed = 1, low speed = 0
        self.speed = 0

        # Open the specified controller
        while self.selectDevice():
            print("Controller called", self.controllerName, "is not found.")
            sleep(1)

        # Values of analog inputs
        LeftThumbstickX = 0
        LeftTrigger = 0
        RightTrigger = 0

        LTX_old = 0
        RT_old = 0

        try:
            for event in self.dev.read_loop():
                
                # Key Press event (ignoring key release)
                if (event.type == ecodes.EV_KEY and event.value == 1) :

                    if (event.code in (ecodes.BTN_A, ecodes.BTN_B, ecodes.BTN_X, ecodes.BTN_Y,)) :

                        self.reset_vels()
                        self.vel_setpoint_pub.publish(self.vels)

                        self.estop.data = 1
                        self.pub_Estop.publish(self.estop)
                        self.estop.data = 0

                        print("Estop engaged. Press Start/Select to exit.")

                    # Left Shoulder Button
                    elif (event.code == ecodes.BTN_TL) :
                        if self.speed == 1:
                            self.speed = 0
                            print("Low Speed Mode (limit = 1.0 m/s)") 
                        else:
                            self.speed = -1
                            print("Reverse Mode Mode (limit = -1.0 m/s)") 

                    # Right Shoulder Button
                    elif (event.code == ecodes.BTN_TR) :
                        if self.speed == 0:
                            self.speed = 1
                            print("High Speed Mode (limit = 2.0 m/s)")   
                        elif self.speed == -1:
                            self.speed = 0
                            print("Low Speed Mode (limit = 1.0 m/s)") 

                    # Start and Select buttons: for disengaging Estop
                    elif (event.code == ecodes.BTN_START and not self.estop.data) :
                        self.pub_Estop.publish(self.estop)
                        self.estop.data = 1
                        print("Estop disengaged.")

                    elif (event.code == ecodes.BTN_SELECT and not self.estop.data) :
                        self.pub_Estop.publish(self.estop)
                        self.estop.data = 1
                        print("Estop disengaged.")

            
                elif (event.type == ecodes.EV_ABS) :
                    if event.value != 0:
                        # if (event.code == 17) and (event.value == -1):
                        #     print("Pressed D-Pad Up")
                        # elif (event.code == 17) and (event.value == 1):
                        #     print("Pressed D-Pad Down")
                        # elif (event.code == 16) and (event.value == -1):
                        #     print("Pressed D-Pad Left")
                        # elif (event.code == 16) and (event.value == 1):
                        #     print("Pressed D-Pad Right")
                        
                        # Left Thumbstick X Event
                        if (event.code == 0) :

                            # If thumbstick is out of deadzone then make it work
                            if ((event.value) not in range(-1000, 1000)) and self.brake_status:
                                LeftThumbstickX = event.value

                                try:
                                    # Floor divide absolute value, then multiply by sign
                                    LeftThumbstickX = int((abs(LeftThumbstickX) // 1536) * (LeftThumbstickX / abs(LeftThumbstickX)))

                                    if LTX_old != LeftThumbstickX and self.brake_status:
                                        self.vels.angular.z = -float(LeftThumbstickX * pow(abs(LeftThumbstickX), 0.8) * 0.015625 / 4)
                                        
                                        print("Setpoint is V :", self.vels.linear.x, "and W :", self.vels.angular.z, LeftThumbstickX)
                                        self.vel_setpoint_pub.publish(self.vels)
                                    LTX_old = LeftThumbstickX
                                except ZeroDivisionError:
                                    pass

                            # Deadzone calibration
                            else:
                                LeftThumbstickX = 0

                                if LTX_old != LeftThumbstickX:
                                    self.vels.angular.z = 0.0
                                    
                                    print("Setpoint is V :", self.vels.linear.x, "and W :", self.vels.angular.z)
                                    self.vel_setpoint_pub.publish(self.vels)

                                LTX_old = LeftThumbstickX

                        # Left Trigger Event
                        elif (event.code == 2):     
                            # If value is more than 50 apply brakes
                            if (event.value) > 450 and self.brake_status:
                                self.reset_vels()
                                self.vel_setpoint_pub.publish(self.vels)
                                self.brake_status = 0
                                print("Brakes engaged.", event.value)
                            elif event.value <= 450 and not self.brake_status:
                                self.brake_status = 1
                                print("Brakes disengaged.", event.value)

                        # Right Trigger Event
                        elif (event.code == 5):
                            if (event.value) not in range(0,10) and self.brake_status:
                                RightTrigger = (event.value+5) // 52

                                if RT_old != RightTrigger:
                                    if self.speed == 1:
                                        self.vels.linear.x = RightTrigger * 0.1 
                                        
                                        print("Setpoint is V :", self.vels.linear.x, "and W :", self.vels.angular.z, event.value)
                                        self.vel_setpoint_pub.publish(self.vels)
                                    elif self.speed == 0:
                                        self.vels.linear.x = RightTrigger * 0.05
                                        
                                        print("Setpoint is V :", self.vels.linear.x, "and W :", self.vels.angular.z, event.value)
                                        self.vel_setpoint_pub.publish(self.vels)
                                    if self.speed == -1:
                                        self.vels.linear.x = -RightTrigger * 0.1 
                                        
                                        print("Setpoint is V :", self.vels.linear.x, "and W :", self.vels.angular.z, event.value)
                                        self.vel_setpoint_pub.publish(self.vels)

                                RT_old = RightTrigger

                            else:
                                RightTrigger = 0

                                if RT_old != RightTrigger:
                                    self.vels.linear.x = 0.0
                                    print("Setpoint is V :", self.vels.linear.x, "and W :", self.vels.angular.z, event.value)
                                    self.vel_setpoint_pub.publish(self.vels)

                                RT_old = RightTrigger

                        elif (event.code in (1, 3, 4, 17, 16)) :
                            pass

                        else:
                            print("New button !")
                            print(event.code)
                            print(categorize(event))

        except OSError:
            self.reset_vels()
            self.vel_setpoint_pub.publish(self.vels)            
            print("Disconnected!")


    def selectDevice(self):
        devices = [InputDevice(path) for path in list_devices()]
        for device in devices:
            if device.name == self.controllerName:
                self.dev = InputDevice(device.path)
                print(self.dev)
                return 0

        if self.dev == 0:
            return 1

    def reset_vels(self):
        self.vels.linear.x = 0.0
        self.vels.linear.y = 0.0
        self.vels.linear.z = 0.0
        self.vels.angular.x = 0.0
        self.vels.angular.y = 0.0
        self.vels.angular.z = 0.0
    



def main(args=None):
    rclpy.init(args=args)

    js = Joystick("Xbox Wireless Controller")

    rclpy.spin(js)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    js.destroy_node()
    rclpy.shutdown()    


if __name__ == "main":
    main()
