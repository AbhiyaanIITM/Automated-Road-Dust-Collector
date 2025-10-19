from __future__ import print_function

import sys
import os
import subprocess
import re
from functools import partial

import rclpy
from rclpy.node import Node

from .jsonreader import JSONReader

import pyqtgraph as pg
import pyqtgraph.Qt as qtgqt
import pyqtgraph.dockarea as darea
from ament_index_python.packages import get_package_share_directory

class PlotHandler(Node):
    def __init__(self):
        super().__init__('gui_buttons')
        # may raise PackageNotFoundError
        self.scriptDir = get_package_share_directory('gui_lexus')
        try:
            self.buttonJSON = self.get_parameter('buttons').value
        except:
            self.declare_parameter('buttons', 'default.json')
            self.buttonJSON = self.get_parameter('buttons').value
        buttonReader = JSONReader(self.scriptDir + '/readfiles/' + self.buttonJSON)
        self.buttonData = buttonReader.data['buttons']
        self.screenButtons = {}
        self.dictOfWidgets = {}
        self.runningScreens = []
        pg.setConfigOptions(antialias=True)
        self.app = qtgqt.QtWidgets.QApplication([])

    def initButtons(self, widget):
        col, row = (0, 4)
        countRows = len(self.buttonData)//5
        for button in self.buttonData:
            buttonName = button.get("id", "")
            buttonLabel = button.get("label", "")
            buttonFunction = button.get("command", "")
            buttonBgColor = button.get("bgColor", "rgb(40, 44, 52)")
            buttonTextColor = button.get("textColor", "rgb(171, 178, 191)")

            # If only "id" is present and no label/command, treat as a layout marker (e.g., new line)
            if not buttonLabel and not buttonFunction:
                if buttonName == "new_line":
                    # spacer = qtgqt.QtWidgets.QLabel("----") # TODO: Spacer label
                    # spacer.setFixedHeight(200)  # Set a minimum height for the spacer
                    # widget.addWidget(spacer, row+1, 0, 1, 5) # Add spacer to the layout
                    col = 0
                    row += 1
                continue

            self.screenButtons[buttonName] = qtgqt.QtWidgets.QPushButton(buttonLabel)
            widget.addWidget(self.screenButtons[buttonName], row=row, col=col)

            buttonFunction = buttonFunction.replace("'", "")
            buttonFunction = re.split(r'[,]\s*', buttonFunction)
            self.screenButtons[buttonName].clicked.connect(partial(self.buttonClicked, buttonFunction))
            self.screenButtons[buttonName].setMouseTracking(True)
            self.screenButtons[buttonName].enterEvent = partial(self.buttonHover, buttonName, buttonBgColor, buttonTextColor)
            self.screenButtons[buttonName].setStyleSheet("background-color: " + buttonBgColor + "; color: " + buttonTextColor)
            if col < 4:
                col += 1
            else:
                col = 0
                row += 1

    def initializePlot(self):
        self.win = qtgqt.QtWidgets.QMainWindow()
        area = darea.DockArea()
        white = (200, 200, 200)
        red = (200, 66, 66); redB = pg.mkBrush(200, 66, 66, 200)
        blue = (6, 106, 166); blueB = pg.mkBrush(6, 106, 166, 200)
        green = "(16, 200, 166)"; greenB = pg.mkBrush(16, 200, 166, 200)
        yellow = (244, 244, 160); yellowB = pg.mkBrush(244, 244, 160, 200)
        self.win.setWindowTitle("Screen handler")
        self.win.setWindowIcon(qtgqt.QtGui.QIcon(self.scriptDir + "/img/icon03.png"))
        #self.get_logger().info("Icon path: " + self.scriptDir + "/img/icon03.png")
        self.win.setFixedSize(800, 600)
        self.win.move(600, 200)
        self.win.setCentralWidget(area)
        
        dock1 = darea.Dock("GUI: " + self.buttonJSON, size = (1,1))  # give this dock minimum possible size
        area.addDock(dock1, "left")
        widg1 = pg.LayoutWidget()
        self.initButtons(widg1)
        self.updateBtn = qtgqt.QtWidgets.QPushButton("update screen list")
        self.wipeBtn = qtgqt.QtWidgets.QPushButton("wipe screens")

        widg1.addWidget(self.wipeBtn, row=1, col=0)
        widg1.addWidget(self.updateBtn, row=1, col=4)
        widg1.setStyleSheet("background-color: rgb(40, 44, 52); color: rgb(171, 178, 191);")
        dock1.setStyleSheet("background-color: rgb(18, 20, 23);")
        dock1.addWidget(widg1)

        self.state = None
        self.updateBtn.clicked.connect(self.update)
        self.wipeBtn.clicked.connect(self.wipeAllScreens)
        self.listwidget = qtgqt.QtWidgets.QListWidget()
        self.listwidget.setStyleSheet("""QListWidget{ color: rgb(171, 178, 191);}""")
        self.listwidget.clicked.connect(self.listclick)
        
        self.listwidget.itemDoubleClicked.connect(self.openscreen)
        self.listwidget
        
        dock1.addWidget(self.listwidget)

        widg2 = pg.LayoutWidget()
        self.dispHoverCmdTextLabel = qtgqt.QtWidgets.QLabel("Hovered command:")
        self.dispHoverCmd = qtgqt.QtWidgets.QPlainTextEdit("None")
        self.dispHoverCmd.setFixedHeight(60) # more lines
        self.dispHoverCmd.setStyleSheet("background-color: rgb(40, 44, 52); color: rgb(171, 178, 191);")
        self.saveWayPointsButton = qtgqt.QtWidgets.QPushButton("Save Waypoints")
        self.loadWayPointsButton = qtgqt.QtWidgets.QPushButton("Load Waypoints")
        widg2.setStyleSheet("background-color: rgb(40, 44, 52); color: rgb(230, 240, 250);")
        widg2.addWidget(self.dispHoverCmdTextLabel, row=0, col=1)
        widg2.addWidget(self.dispHoverCmd, row=1, col=1)
        widg2.addWidget(self.saveWayPointsButton, row=2, col=1)
        widg2.addWidget(self.loadWayPointsButton, row=3, col=1)

        self.loadWayPointsButton.clicked.connect(self.loadWaypoints)
        self.saveWayPointsButton.clicked.connect(self.saveWaypoints)

        dock1.addWidget(widg2)

        self.update()
        self.timer = qtgqt.QtCore.QTimer()
        self.timer.timeout.connect(self.update)
        self.timer.start(1000*10)
        self.win.show()
    
    def checkIfScreenIsRunning(self):
        p = subprocess.Popen(['screen', '-ls'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)        
        output, err = p.communicate()
        lines = output.splitlines()
        return {'localrun': [lines[0] == b'There is a screen on:' or lines[0] == b'There are screens on:', output]}

    def buttonClicked(self, command):
        executeCommand = []
        if(command[0]=='screen'):
            for i in range(0, len(command)-1):
                executeCommand.append(command[i])
            executeCommand.append('bash')
            executeCommand.append('-c')
            executeCommand.append(command[len(command)-1])
        else:
            executeCommand.append('bash')
            executeCommand.append('-c')
            for i in range(0, len(command)):
                executeCommand.append(command[i])
        if executeCommand[2] not in self.dictOfWidgets:
            self.dictOfWidgets[executeCommand[2]] = 1
        else:
            self.dictOfWidgets[executeCommand[2]] += 1
        executeCommand[2] = executeCommand[2]+'_'+str(self.dictOfWidgets[executeCommand[2]])
        p = subprocess.Popen(executeCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
        print(p.communicate()[0])
        self.update()

    def buttonHover(self, buttonName, buttonBgColor, buttonTextColor, event):
        # self.get_logger().info("Button: " + buttonName + " hovered")
        # display the command of the hovered button
        for button in self.buttonData:
            if button["id"] == buttonName:
                self.dispHoverCmd.setPlainText(button["command"])
                break

    def update(self, screenName=None):
        self.listwidget.clear()
        AllScreens = self.checkIfScreenIsRunning()

        if AllScreens['localrun'][0]:
            lines = AllScreens['localrun'][1].splitlines()
            for i in range(1, len(lines)-1):
                line = lines[i].decode('utf-8') 
                if line[0] == '\t':
                    actual_screen = line.split()[0].strip().split('.')[1]
                    self.listwidget.insertItem(0, actual_screen)
                

    def openscreen(self):
        item = self.listwidget.currentItem()
        self.dictOfWidgets.clear()
        toexec = ''.join(['screen -r ', str(item.text()), '; exec bash'])
        subprocess.Popen(['gnome-terminal', '--', 'bash', '-c', toexec])

    def listclick(self, qmodelindex):
        item = self.listwidget.currentItem()

    def wipeAllScreens(self):
        self.runningScreens = []
        subprocess.Popen(['pkill', 'screen'])
        subprocess.Popen(['screen', '-wipe'])
        self.update()

    def loadWaypoints(self):
        filename = qtgqt.QtWidgets.QFileDialog.getOpenFileName(directory=".", filter="Text files (*.txt);; CSV files (*.csv)")

        executeCommand = ['screen', '-mdS', 'waypoint_loader', 'bash', '-c', 'ros2', 'run' f'wayp_plan_tools waypoint_loader --ros-args -p file_name:={filename[0]} -p file_dir:=/mnt/bag/waypoints']

        if filename[0]:
            p = subprocess.Popen(executeCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)
    
    def saveWaypoints(self):
        filename = qtgqt.QtWidgets.QFileDialog.getSaveFileName(directory=".", filter="All Files(*);;Text Files(*.txt);; CSV files(*.csv)")

        executeCommand = ['screen', '-mdS', 'waypoint_saver', 'bash', '-c', 'ros2', 'run' f'wayp_plan_tools waypoint_saver --ros-args -p file_name:={filename[0]} -p file_dir:=/mnt/bag/waypoints']

        if filename[0]:
            p = subprocess.Popen(executeCommand, stdin=subprocess.PIPE, stdout=subprocess.PIPE)

def main(args=None):
    rclpy.init(args=args)
    # print(scriptDir)
    ph = PlotHandler()
    ph.initializePlot()
    if (sys.flags.interactive != 1) or not hasattr(qtgqt.QtCore, "PYQT_VERSION"):
        qtgqt.QtWidgets.QApplication.instance().exec()
    rclpy.shutdown()

if __name__ == '__main__':
    main()