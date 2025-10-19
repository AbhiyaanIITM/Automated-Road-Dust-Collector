# ROS2 pyqt publisher 
# pip install pyqtgraph (or pip3)

import pyqtgraph as pg
import pyqtgraph.Qt as qtgqt
import pyqtgraph.dockarea as darea
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QLabel
from PyQt5 import QtCore, QtGui, QtWidgets
#import numpy as np
import rclpy
from rclpy.node import Node
from std_msgs.msg import String, Bool
from geometry_msgs.msg import Twist
from pacmod3_msgs.msg import SystemCmdFloat, SteeringCmd, VehicleSpeedRpt
from rclpy.clock import Clock

class PlotHandler(Node):
    def __init__(self):
        super().__init__('control_vehicle_node')
        pg.setConfigOptions(antialias=True)
        self.app = QApplication([])

    def initializePlot(self):

        self.win = QtWidgets.QMainWindow()
        node = Node("lexus_gui_node")
        self.accelPub = node.create_publisher(SystemCmdFloat, "/lexus3/pacmod/accel_cmd", 10)
        self.brakePub = node.create_publisher(SystemCmdFloat, "/lexus3/pacmod/brake_cmd", 10)
        self.steerPub = node.create_publisher(SteeringCmd, "/lexus3/pacmod/steer_cmd", 10)
        self.speedPub = node.create_publisher(Twist, "/lexus3/cmd_vel", 10)
        self.enablePub = node.create_publisher(Bool, "/lexus3/pacmod/enable", 10)
        ### self.speedSub = self.create_subscription(VehicleSpeedRpt, "/pacmod/parsed_tx/vehicle_speed_rpt", self.speed_callback, 10)
        ### self.speedSub  # prevent unused variable warning
        area = darea.DockArea()
        white = (200, 200, 200)
        red = (200, 66, 66); redB = pg.mkBrush(200, 66, 66, 200)
        blue = (6, 106, 166); blueB = pg.mkBrush(6, 106, 166, 200)
        green = (16, 200, 166); greenB = pg.mkBrush(16, 200, 166, 200)
        yellow = (244, 244, 160); yellowB = pg.mkBrush(244, 244, 160, 200)
        self.win.setWindowTitle("Lexus control")
        self.win.resize(500, 400)
        self.win.move(400, 400)
        self.win.setCentralWidget(area)
        dockLateralControl = darea.Dock("Lateral control", size = (1,1))  # give this dock minimum possible size
        dockSteeringControl = darea.Dock("Steering control", size = (1,1))  # give this dock minimum possible size
        dockButtons = darea.Dock("Buttons dock", size = (1,1))  # give this dock minimum possible size
        area.addDock(dockLateralControl, "left")
        area.addDock(dockSteeringControl, "bottom")
        area.addDock(dockButtons, "right")
        widgLateralControl = pg.LayoutWidget()
        widgSteeringControl = pg.LayoutWidget()
        widgButtons = pg.LayoutWidget()
        self.pidBtn = QtWidgets.QPushButton("PID")
        self.rawBtn = QtWidgets.QPushButton("RAW")
        self.enableBtn = QtWidgets.QPushButton("Enable\ncontrol");self.enableBtn.setStyleSheet("background-color: rgb(16, 200, 166);")
        self.stopBtn = QtWidgets.QPushButton("STOP"); self.stopBtn.setStyleSheet("background-color: rgb(200, 66, 66);")
        speedLabel = QLabel("Speed"); speedLabel.setStyleSheet("background-color: rgb(4, 4, 4);"); speedLabel.setAlignment(pg.QtCore.Qt.AlignRight); speedLabel.setFixedSize(50, 25)
        accLabel = QLabel("Accel"); accLabel.setStyleSheet("background-color: rgb(4, 4, 4);"); accLabel.setAlignment(pg.QtCore.Qt.AlignRight); accLabel.setFixedSize(50, 25)
        brakLabel = QLabel("Brake"); brakLabel.setStyleSheet("background-color: rgb(4, 4, 4);"); brakLabel.setAlignment(pg.QtCore.Qt.AlignRight); brakLabel.setFixedSize(50, 25)
        self.currentSpeedLabel = QLabel(""); self.currentSpeedLabel.setStyleSheet("background-color: rgb(4, 4, 4);");
        self.currentSpeedLabel.setStyleSheet("font: 12pt; color: rgb(200, 200, 200)")
        
        self.steerSlid = QtWidgets.QSlider(Qt.Horizontal)
        self.speedSlid = QtWidgets.QSlider(Qt.Vertical)
        self.accelSlid = QtWidgets.QSlider(Qt.Vertical)
        self.brakeSlid = QtWidgets.QSlider(Qt.Vertical)
        widgLateralControl.setStyleSheet("background-color: rgb(40, 44, 52); color: rgb(171, 178, 191);")
        dockLateralControl.setStyleSheet("background-color: rgb(18, 20, 23);")
        dockSteeringControl.setStyleSheet("background-color: rgb(40, 42, 46);")
        dockButtons.setStyleSheet("background-color: rgb(18, 20, 23);")
        dockLateralControl.addWidget(widgLateralControl)
        dockSteeringControl.addWidget(widgSteeringControl)
        dockButtons.addWidget(widgButtons)
        self.state = None
        self.pidBtn.clicked.connect(self.changeToPID)
        self.rawBtn.clicked.connect(self.changeToRaw)
        self.enableBtn.clicked.connect(self.enable_vehicle)
        self.stopBtn.clicked.connect(self.stop_vehicle)
        self.accelSlid.valueChanged.connect(self.accel_cmd)
        self.brakeSlid.valueChanged.connect(self.brake_cmd)
        self.steerSlid.valueChanged.connect(self.steer_cmd)
        self.speedSlid.valueChanged.connect(self.speed_cmd)
        self.accelSlid.setMinimum(0); self.accelSlid.setMaximum(100); self.accelSlid.setValue(0)
        self.brakeSlid.setMinimum(0); self.brakeSlid.setMaximum(100); self.brakeSlid.setValue(0)
        self.steerSlid.setMinimum(-20); self.steerSlid.setMaximum(20); self.steerSlid.setValue(0)
        # position GUI elements
        widgLateralControl.addWidget(self.pidBtn, row=0, col=0)
        widgLateralControl.addWidget(self.rawBtn, row=0, col=1)
        widgLateralControl.addWidget(speedLabel, row=1, col=0)
        widgLateralControl.addWidget(accLabel, row=1, col=1)
        widgLateralControl.addWidget(brakLabel, row=1, col=2)
        widgLateralControl.addWidget(self.speedSlid, row=2, col=0)
        widgLateralControl.addWidget(self.accelSlid, row=2, col=1)
        widgLateralControl.addWidget(self.brakeSlid, row=2, col=2)
        widgLateralControl.addWidget(self.currentSpeedLabel, row=3, col=0)
        widgLateralControl.addWidget(self.enableBtn, row=3, col=1)
        widgLateralControl.addWidget(self.stopBtn, row=3, col=2)
        widgSteeringControl.addWidget(self.steerSlid, row=1, col=0)
        self.rawCommands = True
        self.enableVehicleBool = True
        #self.enable_vehicle()
        self.steer_cmd()
        self.win.show()

        # /pacmod/as_rx/accel_cmd
        # /pacmod/as_rx/brake_cmd
        # /pacmod/as_rx/steer_cmd
        # /pacmod/as_rx/enable
        # /cmd_vel
        # /pacmod/parsed_tx/vehicle_speed_rpt

    def loop_slow(self):
        enabCmd = Bool()
        enabCmd.data = self.enableVehicleBool
        self.enablePub.publish(enabCmd)

    def accel_cmd(self):
        msg = SystemCmdFloat()
        msg.enable = True
        msg.command = float(self.accelSlid.value()) / 100
        self.accelPub.publish(msg)   

    def brake_cmd(self):
        msg = SystemCmdFloat()
        msg.enable = True
        msg.command = float(self.brakeSlid.value()) / 100
        self.brakePub.publish(msg)           

    def steer_cmd(self):
        if(self.rawCommands):
            msg = SteeringCmd()
            msg.enable = True
            msg.rotation_rate = 3.3
            msg.command = float(self.steerSlid.value()) / 10 * -1
            self.steerPub.publish(msg)        
            #print(msg.command)
        else:
            msg = Twist()
            msg.linear.x = float(self.speedSlid.value()) / 100 
            msg.angular.z = float(self.steerSlid.value()) / 10 * -1
            self.speedPub.publish(msg)   

    def speed_cmd(self):
        msg = Twist()
        msg.linear.x = float(self.speedSlid.value()) / 20
        msg.angular.z = float(self.steerSlid.value()) / 10 * -1
        #print("%.2f km/h" % (msg.linear.x * 3.6))
        self.currentSpeedLabel.setText("%.2f km/h" % (msg.linear.x * 3.6))
        self.speedPub.publish(msg)        
        #print(msg.linear.x)

    def stop_vehicle(self):
        self.enable_vehicle = False
        # TODO 

    def enable_vehicle(self):
        self.enableVehicleBool = not self.enableVehicleBool
        if(self.enableVehicleBool):
            self.enableBtn.setStyleSheet("background-color: rgb(16, 200, 166);")
        else:
            self.enableBtn.setStyleSheet("background-color: rgb(40, 42, 46);")
        print(self.enableVehicleBool)
        accelCmd = SystemCmdFloat()
        brakeCmd = SystemCmdFloat()
        steerCmd = SteeringCmd()
        # TODO
        accelCmd.clear_override = True #self.enableVehicleBool
        brakeCmd.clear_override = True #self.enableVehicleBool
        steerCmd.clear_override = True #self.enableVehicleBool
        #accelCmd.enable = not self.enableVehicleBool
        #brakeCmd.enable = not self.enableVehicleBool
        #steerCmd.enable = not self.enableVehicleBool
        self.accelPub.publish(accelCmd)
        self.brakePub.publish(brakeCmd)
        self.steerPub.publish(steerCmd)

    def changeToRaw(self):
        self.rawCommands = True
        self.rawBtn.setStyleSheet("background-color: rgb(16, 200, 166);")
        self.pidBtn.setStyleSheet("background-color: rgb(40, 42, 46);")
        self.currentSpeedLabel.setText("Accel + brake")

    def changeToPID(self):
        self.rawCommands = False
        self.pidBtn.setStyleSheet("background-color: rgb(6, 106, 166);")
        self.rawBtn.setStyleSheet("background-color: rgb(40, 42, 46);")
        self.currentSpeedLabel.setText("Lateral control")
        #msg = String()
        #msg.data = "Current time: %s" % Clock().now()
        #self.stringPub.publish(msg)         

    def speed_callback(self, msg):
        print(msg)
        self.currentSpeedLabel.setText("Current speed:\n%.1f Km/h" % (msg.vehicle_speed * 3.6))




def main(args=None):
    import sys
    rclpy.init(args=args)
    print(__file__, "- started ")
    ph = PlotHandler()
    ph.initializePlot()

    timer_slow = qtgqt.QtCore.QTimer()
    timer_slow.timeout.connect(ph.loop_slow)
    timer_slow.start(500)

    if (sys.flags.interactive != 1) or not hasattr(qtgqt.QtCore, "PYQT_VERSION"):
        QApplication.instance().exec_()
    

    # Destroy the node explicitly
    # (optional - otherwise it will be done automatically
    # when the garbage collector destroys the node object)
    #ph.destroy_node()
    #rclpy.shutdown()
    #ph.app.exit()

if __name__ == "__main__":
    main()    