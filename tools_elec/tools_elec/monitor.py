import rclpy
from rclpy.node import Node
from std_msgs.msg import Int8
from std_msgs.msg import Int64MultiArray
from std_msgs.msg import Float64MultiArray

import numpy as np
import matplotlib.pyplot as plt
import time

class Monitor(Node):
    def __init__(self):
        super().__init__('Monitor')

        # Subscribe to the thr topic. Data is Float array, of format [LeftThrottle, RightThrottle]
        self.thr_sub = self.create_subscription(
            Int64MultiArray,
            'thr',
            self.thr_callback,
            10
        )
        self.thr_sub
        self.thr = Int64MultiArray()
        self.thr.data = [0, 0]

        # Subscribe to the estop topic. Data is Int8. 0 if disengage and 1 if engage the Estop.
        self.estop_sub = self.create_subscription(
            Int8,
            'estop',
            self.estop_callback,
            10
        )
        self.estop_sub
        self.estop = Int8()

        # Subscribe to the setpoint topic. Data is Float array, of format [LeftSetpoint, RightSetpoint]
        self.setpoint_sub = self.create_subscription(
            Float64MultiArray,
            'setpoint',
            self.setpoint_callback,
            10
        )
        self.setpoint_sub
        self.setpoint = Float64MultiArray()
        self.setpoint.data = [0.0, 0.0]

        self.rpm_sub = self.create_subscription(
            Float64MultiArray,
            'enc_RPM',
            self.rpm_callback,
            10
        )
        self.rpm_sub
        self.rpm = Float64MultiArray()
        self.rpm.data = [0.0, 0.0]

        self.time = np.linspace(0, 200, 200)
        plt.ion()

        self.rpm0 = np.zeros(200)
        self.rpm1 = np.zeros(200)
        self.sp0 = np.zeros(200)
        self.sp1 = np.zeros(200)
        self.thr0 = np.zeros(200)
        self.thr1 = np.zeros(200)

        self.fig, ((self.ax_0, self.ax_1), (self.ax_thr0, self.ax_thr1) ) = plt.subplots(2,2)
        
        self.ax_0.set_ylim(-100, 100)
        self.ax_1.set_ylim(-100, 100)
        self.ax_thr0.set_ylim(-250, 250)
        self.ax_thr1.set_ylim(-250, 250)
        self.ax_0.set_ylabel('RPM-SP_0')
        self.ax_1.set_ylabel('RPM-SP_1')
        self.ax_thr0.set_ylabel('Thr0')
        self.ax_thr1.set_ylabel('Thr1')

        self.line_rpm0, = self.ax_0.plot(self.time, self.rpm0, 'r')
        self.line_sp0, = self.ax_0.plot(self.time, self.sp0, 'b', linestyle='dashed', alpha=0.5)
        self.line_rpm1, = self.ax_1.plot(self.time, self.rpm1, 'r')
        self.line_sp1, = self.ax_1.plot(self.time, self.sp1, 'b', linestyle='dashed', alpha=0.5)
        self.line_thr0, = self.ax_thr0.plot(self.time, self.thr0, 'g')
        self.line_thr1, = self.ax_thr1.plot(self.time, self.thr1, 'g')

        self.i = 0

    def setpoint_callback(self, msg):
        self.setpoint = msg

    def rpm_callback(self, msg):
        self.rpm = msg
        self.i += 1
        if self.i == 3:
            self.frame()
            self.i = 0
    
    def thr_callback(self, msg):
        self.thr = msg

    def estop_callback(self, msg):
        pass
    
    def frame(self):
        self.rpm0 = np.roll(self.rpm0, -1)
        self.sp0 = np.roll(self.sp0, -1)
        self.rpm1 = np.roll(self.rpm1, -1)
        self.sp1 = np.roll(self.sp1, -1)
        self.thr0 = np.roll(self.thr0, -1)
        self.thr1 = np.roll(self.thr1, -1)

        self.time = np.roll(self.time, -1)

        self.rpm0[-1] = self.rpm.data[0]
        self.rpm1[-1] = self.rpm.data[1]
        self.sp0[-1] = self.setpoint.data[0]
        self.sp1[-1] = self.setpoint.data[1]
        self.thr0[-1] = self.thr.data[0]
        self.thr1[-1] = self.thr.data[1]

        self.time[-1] = self.time[-2] + 1

        self.ax_0.set_xlim(self.time[0], self.time[-1])
        self.ax_1.set_xlim(self.time[0], self.time[-1])
        self.ax_thr0.set_xlim(self.time[0], self.time[-1])
        self.ax_thr1.set_xlim(self.time[0], self.time[-1])
        
        self.line_rpm0.set_ydata(self.rpm0)
        self.line_rpm0.set_xdata(self.time)

        self.line_rpm1.set_ydata(self.rpm1)
        self.line_rpm1.set_xdata(self.time)

        self.line_sp0.set_ydata(self.sp0)
        self.line_sp0.set_xdata(self.time)

        self.line_sp1.set_ydata(self.sp1)
        self.line_sp1.set_xdata(self.time)

        self.line_thr0.set_ydata(self.thr0)
        self.line_thr0.set_xdata(self.time)

        self.line_thr1.set_ydata(self.thr1)
        self.line_thr1.set_xdata(self.time)

        self.fig.canvas.draw()
        self.fig.canvas.flush_events()

def main(args=None):
    rclpy.init(args=args)

    monitor = Monitor()

    rclpy.spin(monitor)

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    monitor.destroy_node()
    rclpy.shutdown()


if __name__ == '__main__':
    main()
