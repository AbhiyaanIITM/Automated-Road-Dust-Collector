import rclpy
from rclpy.node import Node
from serial import *
from std_msgs.msg import Int8
from std_msgs.msg import Int64MultiArray
from std_msgs.msg import Float64MultiArray


class LightControl(Node):
    def __init__(self, serPort):
        super().__init__('LightControl')

        # # Define the port of motor controller here with a parameter. 
        # self.declare_parameter('port', serPort)
        # # Get the value of port parameter
        self.serPort = serPort

        # Get the loop mode
        self.mode = "0"

        # Try to open the serial port and save it as self.ser
        try:
            self.ser = Serial(
                port = self.serPort,
                baudrate = 115200,
                parity = PARITY_NONE,
                stopbits = STOPBITS_ONE,
                bytesize = EIGHTBITS,
                timeout = 0.1
            )    
            self.ser.isOpen()
            print("Opened port", self.ser, "!")

        # If port is busy try closing it and opening it again
        except IOError:
            self.ser = Serial(
                port = self.serPort,
                baudrate = 115200,
                parity = PARITY_NONE,
                stopbits = STOPBITS_ONE,
                bytesize = EIGHTBITS,
                timeout = 0.1
            )
            print("Waiting for port to close")
            self.ser.close()
            self.ser.open()
            print("Opened port", self.ser, "!")

        # Subscribe to the thr topic. Data is Float array, of format [LeftThrottle, RightThrottle]
        self.rpm_sub = self.create_subscription(
            Float64MultiArray,
            'enc_RPM',
            self.rpm_callback,
            10
        )
        self.rpm_sub
        self.rpm = Float64MultiArray()
        self.rpm.data = [0.0, 0.0]
        self.counter=0

    def rpm_callback(self, msg):
        self.rpm = msg
        
        # Scales the PID loop frequency by a factor of the encoder feedback receive frequency.
        # Currently encoder gives at 100Hz. So reduce it to 10 Hz\

    
        self.counter += 1
        if self.counter == 10:
            self.send_msg()
            self.counter = 1
        
    def send_msg(self):
        if self.rpm.data[0]==0 and self.rpm.data[1]==0:
            x= self.ser.write(b"0\r")
            self.ser.write(x.encode('utf-8'))
        elif (self.rpm.data[0]<=300 and self.rpm.data[0]>250) or (self.rpm.data[1]<=300 and self.rpm.data[1]>250):
            x= self.ser.write(b"6\r")
            self.ser.write(x.encode('utf-8'))
        elif (self.rpm.data[0]<=250 and self.rpm.data[0]>200) or (self.rpm.data[1]<=250 and self.rpm.data[1]>200):
            x= self.ser.write(b"5\r")
            self.ser.write(x.encode('utf-8'))
        elif (self.rpm.data[0]<=200 and self.rpm.data[0]>150) or (self.rpm.data[1]<=200 and self.rpm.data[1]>150):
            x= self.ser.write(b"4\r")
            self.ser.write(x.encode('utf-8'))
        elif (self.rpm.data[0]<=150 and self.rpm.data[0]>100) or (self.rpm.data[1]<=150 and self.rpm.data[1]>100):
            x= self.ser.write(b"3\r")
            self.ser.write(x.encode('utf-8'))
        elif (self.rpm.data[0]<=100 and self.rpm.data[0]>50) or (self.rpm.data[1]<=100 and self.rpm.data[1]>50):
            x= self.ser.write(b"2\r")
            self.ser.write(x.encode('utf-8'))
        elif (self.rpm.data[0]<=50 and self.rpm.data[0]>0) or (self.rpm.data[1]<=50 and self.rpm.data[1]>0):
            x= self.ser.write(b"1\r")
            self.ser.write(x.encode('utf-8'))

def main(args=None):
    rclpy.init(args=args)

    light = LightControl(serPort="/dev/serial/by-id/")

    rclpy.spin(light)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    light.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
