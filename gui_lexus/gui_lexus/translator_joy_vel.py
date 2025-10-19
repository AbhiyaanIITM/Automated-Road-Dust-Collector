#!/usr/bin/env python
# joy to //lexus3/pacmod/accel_cmd brake and steer
# TODO: test and correct buttons


import rclpy
import pacmod3_msgs.msg as pac_msg
from sensor_msgs.msg import Joy
from std_msgs.msg import Bool
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult

class Translator(Node):
    def parameter_callback(self, params):
        for param in params:
            if param.name == "steer_gain":
                self.steer_gain = param.value
                self.get_logger().info("steer_gain: %.1f" % (self.steer_gain))
            if param.name == "accel_gain":
                self.accel_gain = param.value
                self.get_logger().info("accel_gain: %.1f" % (self.accel_gain))
            if param.name == "brake_gain":
                self.brake_gain = param.value
                self.get_logger().info("brake_gain: %.1f" % (self.brake_gain))
            if param.name == "input_device":
                param_input_dev = str(param.value)
                self.mapButtons(param_input_dev)
                self.get_logger().info("input_device: %s" % (param_input_dev))
        return SetParametersResult(successful=True)
        
    def __init__(self):
        super().__init__('joy_translator')
        self.get_logger().info("Started " + self.get_name())
        self.declare_parameter("input_device", "joystick1") # eg joystick or steering_wheel
        self.declare_parameter("steer_gain", 1.0) # 6 for local 5.2 for laptop
        self.declare_parameter("accel_gain", 1.0) # 
        self.declare_parameter("brake_gain", 1.0) # 
        self.declare_parameter("accel_offset", 0.0) # 
        self.declare_parameter("brake_offset", 0.0) # 
        param_input_dev = str(self.get_parameter("input_device").value)
        self.steer_gain = self.get_parameter("steer_gain").value
        self.accel_gain = self.get_parameter("accel_gain").value
        self.brake_gain = self.get_parameter("brake_gain").value
        self.accel_offset = self.get_parameter("accel_offset").value
        self.brake_offset = self.get_parameter("brake_offset").value
        self.get_logger().info("input_device: %s steer_gain: %.1f" % (param_input_dev, self.steer_gain))
        self.mapButtons(param_input_dev)
        self.sub1 = self.create_subscription(Joy, 'joy', self.callback, 10)
        self.sub2 = self.create_subscription(Bool, "/lexus3/pacmod/enabled", self.callbackEnabled, 10)
        self.sub1  
        self.sub2  
        
        self.pubA = self.create_publisher(pac_msg.SystemCmdFloat, "/lexus3/pacmod/accel_cmd", 10)
        self.pubB = self.create_publisher(pac_msg.SystemCmdFloat, "/lexus3/pacmod/brake_cmd", 10)
        self.pubS = self.create_publisher(pac_msg.SteeringCmd, "/lexus3/pacmod/steering_cmd", 10)
        self.pubTU = self.create_publisher(pac_msg.SystemCmdInt, "/lexus3/pacmod/turn_cmd", 10)
        self.pubHE = self.create_publisher(pac_msg.SystemCmdInt, "/lexus3/pacmod/headlight_cmd", 10)
        self.pubWI = self.create_publisher(pac_msg.SystemCmdInt, "/lexus3/pacmod/wiper_cmd", 10)
        self.pubSH = self.create_publisher(pac_msg.SystemCmdInt, "/lexus3/pacmod/shift_cmd", 10)
        self.pubHO = self.create_publisher(pac_msg.SystemCmdBool, "/lexus3/pacmod/horn_cmd", 10)
        self.pubF = self.create_publisher(Bool, "/lexus3/pacmod/enable", 10)
        #self.pubE = self.create_publisher(Bool, "/lexus3/pacmod/enabled", 10)
        self.add_on_set_parameters_callback(self.parameter_callback)

        self.last_published_time = self.get_clock().now()
        self.last_published = None
        timer_period = 0.5  # seconds
        self.timer = self.create_timer(timer_period, self.timer_callback)
        self.joyInit = True
        self.autonomStatusChanged = True
        self.autonomStatus = True
        self.headlight = False
        self.pacmodst = True
    
    def mapButtons(self, input_dev):
        if input_dev == "steering_wheel1":
            # buttons
            self.m_start = 0 # A button green
            self.m_stop = 1 # B button red
            self.m_horn = 2 # X button 
            
            #axes
            self.m_steer = 0 
            self.m_accel = 1 # -1.0 to + 1.0
            self.m_brake = 2 # -1.0 to + 1.0
            self.m_joy_init = 3
            self.m_lights_a = 4
            self.m_headlight = 3
        else: # joystick1
            # buttons
            self.m_start = 0 # A button green
            self.m_stop = 1 # B button red
            self.m_horn = 2 # X button 
            self.m_turn_index = 3 # Y button 
            
            #axes
            self.m_steer = 0
            self.m_joy_init = 1
            self.m_brake = 2
            self.m_lights_a = 4
            self.m_accel = 5
            self.m_headlight = 7

    def timer_callback(self):
        if (self.pacmodst == False):
            self.autonomStatus = False
            #self.get_logger().info("Pacmod says off")

    def callbackEnabled(self, message):
        self.pacmodst = message.data
            

    def callback(self, message):
        accelCmd = pac_msg.SystemCmdFloat()
        brakeCmd = pac_msg.SystemCmdFloat()
        steerCmd = pac_msg.SteeringCmd()
        TUCmd = pac_msg.SystemCmdInt()
        HECmd = pac_msg.SystemCmdInt()
        WICmd = pac_msg.SystemCmdInt()
        SHCmd = pac_msg.SystemCmdInt()
        HOCmd = pac_msg.SystemCmdBool()
        accelCmd.header.stamp = self.get_clock().now().to_msg()
        brakeCmd.header.stamp = self.get_clock().now().to_msg()
        steerCmd.header.stamp = self.get_clock().now().to_msg()
        steerCmd.command = message.axes[self.m_steer] * self.steer_gain  
        accelCmd.command = ((message.axes[self.m_accel] - 1) / -2) * self.accel_gain + self.accel_offset
        brakeCmd.command = ((message.axes[self.m_brake] - 1) / -2) * self.brake_gain + self.brake_offset
        if accelCmd.command < 0.0 or accelCmd.command >= 1.0:
            self.get_logger().warn("accel is %.2f" %(accelCmd.command))
        if(self.autonomStatus == False):
            if(message.buttons[self.m_start]): # start A
                self.autonomStatusChanged = True
                self.autonomStatus = True
                self.get_logger().info("Autonomous mode on")
        TUCmd.command = 1
        if(message.buttons[self.m_stop]): # stop B
            self.autonomStatusChanged = True
            self.autonomStatus = False
            self.get_logger().info("Autonomous mode off")
        elif(message.buttons[self.m_horn]): # horn  X
            HOCmd.command = True
            #self.get_logger().info("Horn")
        elif(message.axes[self.m_lights_a] > 0.5): # lights 
            TUCmd.command = 2
            # self.get_logger().info("Left")
        elif(message.axes[self.m_lights_a] < -0.5): # lights
            # self.get_logger().info(str(message.axes[self.m_lights_a]) + " llll")
            # self.get_logger().info("Right")
            TUCmd.command = 0
            #self.get_logger().info("Right")
        #elif(message.axes[5] < 0): # lights 
        #    TUCmd.command = 3
        #    self.get_logger().info("Down")
        elif(message.axes[self.m_headlight] > 0): # lights
            if self.headlight: 
                self.headlight = False
                HECmd.command = 2     
            else:
                self.headlight = True
                HECmd.command = 0            
            self.get_logger().info("Up")
        if(self.autonomStatusChanged):
            accelCmd.clear_override = True
            brakeCmd.clear_override = True
            accelCmd.clear_override = True
            steerCmd.clear_override = True
            TUCmd.clear_override = True
            HECmd.clear_override = True
            WICmd.clear_override = True
            SHCmd.clear_override = True
            HOCmd.clear_override = True
        else:
            accelCmd.clear_override = False
            brakeCmd.clear_override = False
            accelCmd.clear_override = False
            steerCmd.clear_override = False
            TUCmd.clear_override = False
            HECmd.clear_override = False
            WICmd.clear_override = False
            SHCmd.clear_override = False
            HOCmd.clear_override = False
        #//lexus3/pacmod/enable.data
        status = Bool()
        status.data = self.autonomStatus
        brakeCmd.enable = self.autonomStatus
        accelCmd.enable = self.autonomStatus
        steerCmd.enable = self.autonomStatus
        TUCmd.enable = self.autonomStatus
        HECmd.enable = self.autonomStatus
        WICmd.enable = self.autonomStatus
        SHCmd.enable = self.autonomStatus
        HOCmd.enable = self.autonomStatus            
        if(self.joyInit):
            if(message.axes[self.m_joy_init] == 0.0):
                accelCmd.command = 0.0 
            else:
                self.joyInit = False
        steerCmd.rotation_rate = 3.3
        accelCmd.header.frame_id = "pacmod"        
        ast = "----"
        if (self.autonomStatus):
            ast = "Auto  "
        else:
            ast = "Driver"
        self.get_logger().info("%s accel brake steer: %.1f %.1f %.1f" %(ast, accelCmd.command, brakeCmd.command, steerCmd.command))
        # self.get_logger().info("TUCmd: %d HECmd: %d WICmd: %d SHCmd: %d HOCmd: %d" %(TUCmd.command, HECmd.command, WICmd.command, SHCmd.command, HOCmd.command))
        self.last_published = message
        self.pubA.publish(accelCmd)
        self.pubB.publish(brakeCmd)
        self.pubS.publish(steerCmd)
        self.pubTU.publish(TUCmd)
        self.pubHE.publish(HECmd)
        self.pubWI.publish(WICmd)
        self.pubSH.publish(SHCmd)
        self.pubHO.publish(HOCmd)
        self.pubF.publish(status)


def main(args=None):
    rclpy.init(args=args)

    translator_cmd_joy = Translator()

    rclpy.spin(translator_cmd_joy)

    translator_cmd_joy.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()