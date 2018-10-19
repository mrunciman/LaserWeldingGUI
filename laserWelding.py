import tkinter as tk
from tkinter import filedialog
import tkinter.messagebox as msg
import ntpath
import serial
import socket
import select
import struct
import sys
import time
import os


class LaserWeld(tk.Tk):
    def __init__(self):
        super().__init__()

        #Create file that robot will use to stop itself. It will later be deleted when window is closed.
        with open("stopRobot.txt", 'w') as self.stopFile:
            self.stopFile.write('def ProgStop():\n  stopl(1)\nend\n\nProgStop()')

#################################################################################
#       Setup of Widgets in Centre Frame
#################################################################################

    #The frame for the main user inputs
        self.centreFrame = tk.Frame(self, bg="gray79", borderwidth=2, relief="flat")
        self.centreFrame.grid(         row = 0, column = 0, columnspan = 2, sticky = 'wens')
        #Title bar and grid instantiation.
        self.title("Laser Welding System")

        #Heading for GUI
        self.subTitle = tk.Label(self.centreFrame, bg="SteelBlue3", text = "Input desired options, then click START to begin operation.", relief = "groove")
        self.subTitle.configure(font='TkDefaultFont 16')

        #Create file choosing button, file name wil be displayed here.
        self.fileLabelName = tk.StringVar(self)
        self.fileLabelName.set("1. Choose a .txt file describing desired weld pattern:")
        self.fileLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.fileLabelName)
        #Instantiate program name handle that will be reassigned to txt file name.
        #See fileOpen() function
        #Instantiate flags to indicate if a file has been chosen or if speed has been changed.
        self.speedFlag = 0
        self.fileFlag = 0
        #Create Browse button that calls fileOpen()
        self.fileChooserButton= tk.Button(self.centreFrame, bg="azure3", text="Browse", command = self.fileOpen)
        
        #Label for COM Port selection
        self.COMLabelName = tk.StringVar(self)
        self.COMLabelName.set("2. Choose Laser COM Port:")
        self.COMLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.COMLabelName)
        #Create drop down list containing available COM Ports - one should be
        #the laser.
        self.optionsCOM = tk.StringVar(self)
        self.optionsCOM.set("Select...")
        self.portNumber = tk.StringVar(self)
        self.listOptions = self.comPorts()
        if self.listOptions == []:
            self.listOptions = ["Connect Laser to a COM Port"]
        #Using the list calls comPorts()
        self.optionsList = tk.OptionMenu(self.centreFrame, self.optionsCOM, *self.listOptions)
        
        self.optionsList.configure(bg="gray79")
        #The Connect button calls laserConnect(), using the selected COM port.
        #Clicking the test button will also call the getStatus function.
        self.laser = serial.Serial()
        self.connectLaser = tk.Button(self.centreFrame, bg="azure3", text="Test Laser Connection", command = lambda: self.laserConnect(self.laser))

        #IP Address label
        self.ipLabelName = tk.StringVar(self)
        self.ipLabelName.set("3. Input Robot IP Address:")
        self.ipLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.ipLabelName)
        #Allows the user to input the IP address of UR5 robot.
        #Configure Entry box
        self.ipAddressText = tk.StringVar(self)
        self.ipAddressText.set("192.168.0.117") #This should be the IP address
        self.ipAddress = tk.Entry(self.centreFrame, textvariable = self.ipAddressText)
        #Use IP address input and connect to robot by calling robotConnect()
        #then immediately disconnect, so connection can be made when sending program 
        self.connectRobot = tk.Button(self.centreFrame, bg="azure3", text="Test Robot Connection", command = self.robotTest)

        #Check box to allow for testing with the pilot laser
        self.laserFlag = tk.IntVar(self)
        self.pilotLaser = tk.Checkbutton(self.centreFrame, bg="gray79", text = "Use Pilot Laser", variable = self.laserFlag, command = lambda: self.appearCurrent(self.laser), onvalue = 0, offvalue = 1)

        #Robot speed input label
        self.speedLabelName = tk.StringVar(self)
        self.speedLabelName.set("4. Input Weld Speed (mm/s):")
        self.speedLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.speedLabelName)
        #Input the laser current in mA and set by clicking button
        #If no value is set, use Pilot Laser
        self.weldSpeed = tk.StringVar(self)
        self.weldSpeed.set("25")
        self.weldSpeedEntry = tk.Entry(self.centreFrame, textvariable = self.weldSpeed)
        self.weldSpeedButton = tk.Button(self.centreFrame, bg="azure3", text = "Set Weld Speed", command = self.setWeldSpeed)

        #Robot focal point label
        self.focusLabelName = tk.StringVar(self)
        self.focusLabelName.set("5. Input Offset from Focal Point (mm):")
        self.focusLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.focusLabelName)
        #Input the vertical offset from focal point in mm and set by clicking button
        #If no value is set, no offset is added
        self.focusOffset = tk.StringVar(self)
        self.focusOffset.set("0")
        self.focusOffsetEntry = tk.Entry(self.centreFrame, textvariable = self.focusOffset)
        self.focusOffsetButton = tk.Button(self.centreFrame, bg="azure3", text = "Set Focus Offset", command = self.setFocusOffset)

        #Current input label
        self.currentLabelName = tk.StringVar(self)
        self.currentLabelName.set("5. Input Laser Current (mA):")
        self.currentLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.currentLabelName)
        #Input the laser current in mA and set by clicking button
        #If no value is set, use Pilot Laser
        self.laserCurrentText = tk.StringVar(self)
        self.laserCurrentText.set("0000")
        self.laserCurrent = tk.Entry(self.centreFrame, textvariable = self.laserCurrentText)
        self.laserCurrentLabel = tk.Button(self.centreFrame, bg="azure3", text = "Set Laser Current", command = lambda: self.setLaserCurrent(self.laser))

        #Make a button to start welding process.
        self.weldFlag = 0 # For indicating connection to robot, used at close of window.
        self.runWeld = tk.Button(self.centreFrame, bg="red", text = "START WELDING PROCESS", command = lambda: self.confirmWelding(self.laser))

        #Message Box
        self.messageLabelText = tk.StringVar(self)
        self.messageLabelText.set("Status:")
        self.messageLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.messageLabelText)
        self.messageLabel.configure(font = 'TkDefaultFont 10 bold')
        #Output box
        self.messageBoxText = tk.StringVar(self)
        self.messageBox = tk.Entry(self.centreFrame, textvariable = self.messageBoxText)
        self.messageBox.configure(font = 'TkDefaultFont 10 italic')

        #Time label
        self.timeLabelName = tk.StringVar(self)
        self.timeLabelName.set("Time: ")
        self.timeLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.timeLabelName)

        #Z Position label
        self.ZCoordLabelName = tk.StringVar(self)
        self.ZCoordLabelName.set("Target Z Coord: ")
        self.ZCoordLabel = tk.Label(self.centreFrame, bg="gray79", textvar = self.ZCoordLabelName)

#################################################################################
#       Organisation of Centre Frame

        #Centre frame
        self.subTitle.grid(         row = 0, column = 0, columnspan = 3, sticky = 'wens', padx = 1, pady = 5, ipadx = 0)
        self.fileLabel.grid(        row = 1, column = 0, columnspan = 2, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)        
        self.fileChooserButton.grid(row = 1, column = 2, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)

        self.COMLabel.grid(         row = 2, column = 0, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)
        self.optionsList.grid(      row = 2, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)
        self.connectLaser.grid(     row = 2, column = 2, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)

        self.ipLabel.grid(          row = 3, column = 0, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)        
        self.ipAddress.grid(        row = 3, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)
        self.connectRobot.grid(     row = 3, column = 2, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)

        self.speedLabel.grid(       row = 4, column = 0, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)
        self.weldSpeedEntry.grid(   row = 4, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)
        self.weldSpeedButton.grid(  row = 4, column = 2, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)

        self.focusLabel.grid(      row = 5, column = 0, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)
        self.focusOffsetEntry.grid( row = 5, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)
        self.focusOffsetButton.grid(row = 5, column = 2, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)

        self.pilotLaser.grid(       row = 6, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)

       # See function "self.appearCurrent()" below for current setting widgets.

        self.runWeld.grid(          row = 8, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 10, ipadx = 40)

        self.messageLabel.grid(     row = 9, column = 0, columnspan = 1, sticky = 'wns',  padx = 5, pady = 0,  ipadx = 5)
        self.messageBox.grid(       row = 10, column = 0, columnspan = 3, sticky = 'wens', padx = 10,pady = 10, ipadx = 40)

        self.timeLabel.grid(        row = 11, column = 0, columnspan = 2, sticky = 'wns',  padx = 5, pady = 5, ipadx = 5)
        self.ZCoordLabel.grid(      row = 11, column = 2, columnspan = 1, sticky = 'wns',  padx = 5, pady = 5, ipadx = 5)

#################################################################################
#       Setup of Widgets in Right Frame
#################################################################################

    #Frame for output from laser
        self.rightFrame = tk.Frame(self, bg="gray70", borderwidth=2, relief="sunken")
        self.rightFrame.grid(       row = 1, column = 0, columnspan = 2, sticky = 'wnes')

        #Sub title
        self.subTitle2 = tk.Label(self.rightFrame, bg="SlateGray3", text = "Laser Status", relief = "groove")
        self.subTitle2.configure(font='TkDefaultFont 12 bold')        

        #Response from laser label
        self.laserLabelText = tk.StringVar(self)
        self.laserLabelText.set("Message from Laser:")
        self.laserLabel = tk.Label(self.rightFrame, bg="gray70", textvar = self.laserLabelText)
        self.laserLabel.configure(font = 'TkDefaultFont 10 bold')

        #Response from laser
        self.laserReplyText = tk.StringVar(self)
        self.laserReplyText.set("Laser Reply")
        self.laserReply = tk.Entry(self.rightFrame, textvariable = self.laserReplyText)
        self.laserReply.configure(font = 'TkDefaultFont 10 italic')

        #Status check boxes - first make variables then add to checkbutton
        statusLabelNames = 'Laser Current On:', 'Laser Current OK:', 'Laser Temperature Maximum OK:', 'Crystal Temperature Sensor OK:', 'Crystal Temperature Control On:', 'Crystal Temp. Lower Limit OK:', 'Crystal Temp. Upper Limit OK:', 'Laser Temp. Lower Limit OK:', 'Laser Temp. Upper Limit OK:', 'Driver Temperature OK:', 'Driver Supply OK:', 'Laser Interlock OK:', 'LASER ARMED:'
        #There are 13 status flags that are received from the laser, make a
        #name label and a display label for each.
        self.displayNames = {}
        for number in range(1,14):
            #Instantiate and assign names to labels and display boxes
            label = tk.StringVar(self)
            label.set(statusLabelNames[number-1])
            self.name = tk.Label(self.rightFrame, bg="gray70", textvar = label)
            self.display = tk.Label(self.rightFrame, bg="gray64", textvar = "", relief="sunken")
            self.displayNames["self.statusDisplay_"+str(number-1)] = self.display
            #Organise display boxes and labels
            self.name.grid(      row = number+1, column = 0, columnspan = 1, sticky = 'w', padx = 5, pady = 1, ipadx = 0)
            self.display.grid(   row = number+1, column = 1, columnspan = 1, sticky = 'w', padx = 5, pady = 1, ipadx = 8)
        #print(self.displayNames)
        #Check status button
        #self.checkStatusB = tk.Button(self.rightFrame, bg="azure3", text = "Check Laser Status", command = self.getStatus((self.laser)))
             
#################################################################################
#       Organisation of Right Frame

        #Right frame
        self.subTitle2.grid(        row = 0, column = 0, columnspan = 3, sticky = 'wens', padx = 5, pady =  10, ipadx = 0)
        self.laserLabel.grid(       row = 1, column = 0, columnspan = 1, sticky = 'wns', padx = 5, pady = 10, ipadx = 0)
        self.laserReply.grid(       row = 1, column = 1, columnspan = 2, sticky = 'wens', padx = 5, pady = 10, ipadx = 40)
        #self.checkStatusB.grid(     row = 2, column = 1, columnspan = 2, sticky = 'wens', padx = 5, pady = 10, ipadx = 40)


        self.centreFrame.columnconfigure(1, weight = 1)
        self.centreFrame.rowconfigure(0,weight = 1)

        self.rightFrame.rowconfigure(15, weight=1)
        self.rightFrame.columnconfigure(1, weight=1)

        self.rowconfigure(1, weight=1)
        self.columnconfigure(0, weight=1)
        #self.rowconfigure(13, weight=1)
        #self.columnconfigure(0, weight=1)
        windaeWidth = int(self.winfo_screenwidth()/2)
        windaeHeight = int(self.winfo_screenheight())
        self.geometry('%sx%s+%s+%s'%(windaeWidth, windaeHeight ,windaeWidth-5,0))

        self.graveyardList = []

#################################################################################
#   Definition of Functions
#################################################################################
#   Functions used by pressing buttons/checkboxes/text box
        
    #Open dialogue box for choosing urscript file in txt format
    def fileOpen(self, event=None):
        self.programFile = filedialog.askopenfilename()
        while self.programFile and not self.programFile.endswith(".txt"):
            msg.showerror("Wrong Filetype", "Please select a .txt file")
            self.programFile = filedialog.askopenfilename()
        if self.programFile:
            self.program = open(self.programFile,'r+b')
            self.programName = ntpath.normpath(self.program.name)
            self.programNameOriginal = self.programName
            self.programNameShort = ntpath.basename(self.programNameOriginal)
            fileLabelString = "1. File chosen: " + self.programNameShort
            self.fileLabelName.set(fileLabelString)
            self.fileFlag = 1
            

    #Function to list available COM ports.
    def comPorts(self, event=None):
        ports = ['COM%s' % (i + 1) for i in range(256)]
        self.listOptions = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                self.listOptions.append(str(port))
            except (OSError, serial.SerialException):
                pass
        return self.listOptions

    #Function to connect to Laser
    def laserConnect(self, serialConnection, event=None):
        #Get port number, the format will be "COM X" where X is the port number
        portName = self.optionsCOM.get()
        #Set self.portNumber so that laser connection can be made in other functions
        self.portNumber.set(portName)
        laserPort = self.portNumber.get()
        if laserPort == "Select...":
            msg.showerror("Laser Connection Error", "Please select a COM port from the drop-down menu.")
        else:
            try:
                if serialConnection.is_open==False:
                    serialConnection.port = laserPort
                    serialConnection.baudrate = 9600
                    serialConnection.bytesize = serial.EIGHTBITS
                    serialConnection.parity = serial.PARITY_NONE
                    serialConnection.stopbits = serial.STOPBITS_ONE
                    serialConnection.timeout = 0
                    serialConnection.open()                    
                status = self.getStatus(serialConnection,1)
                if status == 1:
                    self.connectLaser['bg'] = "green"
            except Exception as e_Laser:
                msg.showerror("Laser Connection Error", "Could not connect to laser on port: %s. Exception is: %s" %(laserPort, e_Laser))
                  

    #Connect to robot using user-supplied IP Address.
    def robotTest(self, event=None):
        PORT = 30003
        HOST = self.ipAddressText.get()
        robotSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #print(robotSocket)
        errorFlag = False
        try:
            robotSocket.connect((HOST, PORT))
            #while 1:
                #inputready, o, e = select.select([robotSocket],[],[], 0.0)
                #if len(inputready)==0: break
                #robotSocket.recv(1)
        except Exception as e:
            msg.showerror("Robot Connection Error", "Something's wrong with combination of  Host: %s and Port: %d. Exception is: %s" %(HOST, PORT, e))
            errorFlag = True
        if not errorFlag:
            #Close connection, open it later when sending program to robot to avoid synchronisation problems.
            robotSocket.shutdown(socket.SHUT_RDWR)
            robotSocket.close()
            self.connectRobot['bg'] = "green"


    # Read file at option 1 and re-write speed value, saving in separate file.
    def setWeldSpeed(self, event=None):
        self.weldSpeedButton['bg'] = "gray79"
        if self.fileFlag == 1:
            weldProgram = open(self.programName,'r')
            urScriptLines = weldProgram.readlines()
            fileName = ntpath.basename(self.programName)
            fileName = os.path.splitext(fileName)[0]
            #fileName = fileName.split('.')
            speedWeld = self.weldSpeed.get()
            if int(speedWeld) < 500:
                speedWeldmm = str(int(speedWeld)/1000)
                for lineNo in range(len(urScriptLines)):
                    line = urScriptLines[lineNo].split()
                    if line == []:
                        pass
                    elif line[0] == "speed_ms":
                        urScriptLines[lineNo] = "  speed_ms = " + speedWeldmm + "\n"
                self.programName = fileName+' '+speedWeldmm+" .txt"
                self.graveyardList.append(self.programName)
                self.speedFlag = 1
                with open(self.programName, 'w') as modifiedFile:
                    modifiedFile.writelines(urScriptLines)
                self.program = open(self.programName,'r+b')
                self.weldSpeedButton['bg'] = "green"
            else:
                msg.showerror("Weld Speed Limit Exceeded", "Please input a value below 500 mm/s in option 4.")
        else:
            msg.showerror("Please Select a Program", "Please select a welding pattern .txt file at option 1.")

#Edit urscript file to change tcp declaration
    def setFocusOffset(self, event=None):
        self.focusOffsetButton['bg'] = "gray79"
        if (self.fileFlag == 1):
            ur5Program = open(self.programName, 'r')
            ur5ScriptLines = ur5Program.readlines()
            fileNameOld = ntpath.basename(self.programName)
            fileNameOld = os.path.splitext(fileNameOld)[0]
            focusOffset = int(self.focusOffset.get())
            magfocusOffset = abs(focusOffset)
            if (magfocusOffset <= 25)or(magfocusOffset!=''):
                focusOffsetM = focusOffset/1000
                for lineNo in range(len(ur5ScriptLines)):
                    line = ur5ScriptLines[lineNo].split()
                    if line == []:
                        pass
                    elif "set_tcp(p[0.000000," in line:
                        line[1] = 0.217+focusOffsetM
                        line[1] = "%.6f" % line[1]
                        line[1] = str(line[1])+','
                        ur5ScriptLines[lineNo] = '  ' + ' '.join(line) + "\n"
                self.programName = fileNameOld + ' ' + str(focusOffset) + " .txt"
                self.graveyardList.append(self.programName)
                self.focusFlag = 1
                with open(self.programName, 'w') as modifiedFile:
                    modifiedFile.writelines(ur5ScriptLines)
                self.program = open(self.programName,'r+b')
                self.focusOffsetButton['bg'] = "green"
            else:
                msg.showerror("Offset Limit Exceeded/Empty", "Please input a value of magnitude below 25 mm in option 5.")
        else:
             msg.showerror("Please Select a Program", "Please select a welding pattern .txt file at option 1")

    #Make inputs for setting the laser current appear, based on pilot laser checkbox
    def appearCurrent(self, serialConnection, event=None):
        if serialConnection.is_open==True:
            self.getStatus(serialConnection,1)
        if self.laserFlag.get() == 1:
            self.currentLabel.grid(     row = 6, column = 0, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 5)
            self.laserCurrent.grid(     row = 6, column = 1, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)
            self.laserCurrentLabel.grid(row = 6, column = 2, columnspan = 1, sticky = 'wens', padx = 1, pady = 5, ipadx = 40)
        else:
            self.currentLabel.grid_forget()
            self.laserCurrent.grid_forget()
            self.laserCurrentLabel.grid_forget()
            if serialConnection.is_open==True:
                setCurrentCommand = "LCT0"
                serialConnection.write(setCurrentCommand.encode('utf-8') + b'\r')
                time.sleep(0.1)
                self.laserReplyText.set(self.laserResponse(serialConnection))
                self.getStatus(serialConnection,0)
            
        
################################################################################
#   Functions 'hidden' from the user, used in background

    # Get status number and present it as a binary string.
    # Each bit represents a flag for given conditions, e.g. interlock OK.
    # See Laser Driver User Manual p28, Status Commands for more information.
    def getStatus(self, serialConnection, printFlag, event=None):
        getStatusCommand = "GS"
        serialConnection.write(getStatusCommand.encode('utf-8') + b'\r')
        time.sleep(0.1)
        statusMessage = self.laserResponse(serialConnection)
        if statusMessage == "":
            msg.showerror("Laser Connection Failure", "Please ensure laser is connected and turned on.")
            return statusMessage

        statusCheck = 1
        for number in statusMessage.split():
            if number.isdigit():
                statusNumber = format(int(number),'016b')
                statusNumber = list(statusNumber)
                #Status bits [0,2,8,9,10,11] give a 0 for desired values, so
                # they are inverted
                for invert in [0,2,8,9,10,11]:
                    statusNumber[invert]=int(not(statusNumber[invert]==1))
                    
                #Relevant indices = [0,1,2,4,5,8,9,10,11,12,13,15] so create
                # new status list containing only these, and check overall status.
                #First, switch status bits 0 and 1 to make for more logical display
                # this also excludes the "Laser On" bit from statusCheck
                newStatus = [statusNumber[1]]
                #If using pilot laser, don't check door interlock. Check interlock for real laser.
                if self.laserFlag.get() == 1:
                    indices = [0,2,4,5,8,9,10,11,12,13,15]
                    for index in indices:
                        newStatus.append(statusNumber[index])
                        statusCheck = statusCheck*int(statusNumber[index]) #statusCheck multiplied by interlock bit.
                else:
                    indices = [0,2,4,5,8,9,10,11,12,13]
                    for index in indices:
                        newStatus.append(statusNumber[index])
                        statusCheck = statusCheck*int(statusNumber[index]) #statusCheck not multiplied by interlock bit here.
                    newStatus.append(statusNumber[15])
                    
                #Check each status bit and set the GUI indicator as appropriate.
                for displayNumber in range(0,12):
                    if int(newStatus[displayNumber])==1:
                        self.displayNames["self.statusDisplay_"+str(displayNumber)]['bg']="green"
                    else:
                        self.displayNames["self.statusDisplay_"+str(displayNumber)]['bg']="red"
                if statusCheck==1:
                    self.displayNames["self.statusDisplay_"+str(12)]['bg']="green"
                else:
                    self.displayNames["self.statusDisplay_"+str(12)]['bg']="red"
        if printFlag:
            mensaje = statusMessage + " - Laser Ready: " + str(statusCheck==1)
            self.laserReplyText.set(mensaje)
        return statusCheck


    # Read and print responses from laser after commands are sent.
    def laserResponse(self, serialConnection, event=None):
        replyCount = 0
        reply = []
        replyString = str()
        while serialConnection.in_waiting > 0:
            for c in serialConnection.read():
                reply.append(chr(c))
                if chr(c) == "\r":
                    replyString = ''.join(str(v) for v in reply)
                    if replyCount ==0:
                        replyCount = 1
                    else:
                        replyCount = 0
                    reply = []
        return replyString


    #Set power of the laser through setting the current in mA.
    ##Use text input: self.laserCurrentText
    def setLaserCurrent(self, serialConnection, event=None):
        laserCurrent = self.laserCurrentText.get()
        if int(laserCurrent) > 9800:
            msg.showwarning("Choose current value below 9800 mA","Do not exceed laser currents of 9800 mA")
            return
        setCurrentCommand = "LCT" + str(laserCurrent)
        serialConnection.write(setCurrentCommand.encode('utf-8') + b'\r')
        time.sleep(0.1)
        self.laserReplyText.set(self.laserResponse(serialConnection))
        self.getStatus(serialConnection,0)


    # Activates the laser temperature controller
    def setTempControl(self, serialConnection, event=None):
        setTempCommand = "TCR"
        serialConnection.write(setTempCommand.encode('utf-8') + b'\r')
        time.sleep(0.1)
        self.laserReplyText.set(self.laserResponse(serialConnection))

    def stopTempControl(self,serialConnection, event=None):
        setTempCommand = "TCS"
        serialConnection.write(setTempCommand.encode('utf-8') + b'\r')
        time.sleep(0.1)
        self.laserReplyText.set(self.laserResponse(serialConnection))

    # Requests the current laser temperature as measured by the cooling block
    # and returns it. Then finds the target temp and returns that too.
    def getTempLaser(self, serialConnection, event=None):
        # Get the actual temperature
        getTempCommand = "TA"
        serialConnection.write(getTempCommand.encode('utf-8') + b'\r')
        time.sleep(0.1)
        tempLaserMessage = self.laserResponse(serialConnection)# e.g. "Laser Temp. Actual: 23.030 øC"
        self.laserReplyText.set(tempLaserMessage)
        tempLaserMessage = tempLaserMessage.split()
        tempLaser = float(tempLaserMessage[3])
        # Find the target temperature
        getTargetCommand = "TT"
        serialConnection.write(getTargetCommand.encode('utf-8') + b'\r')
        time.sleep(0.1)
        tempTargetMessage = self.laserResponse(serialConnection)
        tempTargetMessage = tempTargetMessage.split()
        tempTarget = float(tempTargetMessage[3])
        #Find difference between actual temp and target.
        tempDiff = abs(tempLaser - tempTarget)
        return tempLaser, tempTarget, tempDiff

    def tempLoop(self, serialConnection, laserTempArg, targetTempArg, diffTempArg, event=None):
        if diffTempArg > 0.5:
            laserTemp, targetTemp, self.diffTemp = self.getTempLaser(serialConnection)
            self.tempJob = self.after(500, self.tempLoop, serialConnection, laserTemp, targetTemp, self.diffTemp)
            tempString = "Current laser temperature "+str(laserTemp)+" C within "+str("%.2f"%self.diffTemp)+" C of "+str(targetTemp)+" C target."
            self.messageBoxText.set(tempString)
        else:
            tempString = "Current laser temperature "+str(laserTempArg)+". LASER READY."
            self.messageBoxText.set(tempString)
            if self.tempJob is not None:
                self.after_cancel(self.tempJob)
                self.tempJob = None
        return self.diffTemp

    def confirmWelding(self, serialConnection, event=None):
        if self.portNumber.get() != "Select..." and serialConnection.is_open:
            messageString = "WAIT WHILE LASER REACHES TARGET TEMPERATURE..."
            self.messageBoxText.set(messageString)

            #This turns on temp control module on laser
            self.setTempControl(serialConnection)
            #Find actual temp, target temp and difference between the two
            laserTemp, targetTemp, self.diffTemp = self.getTempLaser(serialConnection)
            if self.diffTemp > 0.5:
                self.tempLoop(serialConnection, laserTemp, targetTemp, self.diffTemp)
                msg.showwarning("Please wait for laser to reach safe temperature.","Proceed when the laser temperature is within 0.5 C of the 25.00 C target temperature")
                return

            laserTemp, targetTemp, self.diffTemp = self.getTempLaser(serialConnection)
            tempString = "Current laser temperature "+str(laserTemp)+". LASER READY."
            self.messageBoxText.set(tempString)
            checkStatus = self.getStatus(serialConnection,1)
            if checkStatus==1 and self.diffTemp < 0.5:
                if self.laserFlag.get() == 1:
                    self.realLaser = 1
                    if msg.askokcancel("Proceed?","Confirm initiation of welding procedure.\n\n  Program name: "+self.programNameShort+"\n  Weld speed: "+str(self.weldSpeed.get())+" mm/s \n  Laser current: "+str(self.laserCurrentText.get())+" mA \n\nUSING CLASS 4 LASER."):
                        self.startWelding(serialConnection)
                    else:
                        self.realLaser = 0
                        self.stopTempControl(serialConnection)
                        self.messageBoxText.set("Click: START WELDING PROCESS when ready.")
                else:
                    self.realLaser = 0
                    if msg.askokcancel("Proceed?","Confirm initiation of welding procedure.\n\n  Program name: "+self.programNameShort+"\n  Weld speed: "+str(self.weldSpeed.get())+" mm/s \n  Laser current: "+str(self.laserCurrentText.get())+" mA \n\nUSING PILOT LASER."):
                        self.startWelding(serialConnection)
                    else:
                        self.realLaser = 0
                        self.stopTempControl(serialConnection)
                        self.messageBoxText.set("Click: START WELDING PROCESS when ready.")
            else:
                msg.showerror("Check status and temperature of laser.","Ensure all connections and settings of the laser are correct.")                     
        else:
            msg.showerror("Set appropriate values for Settings 1, 2, 3, 4 and 5", "Make sure:\n  - A .txt file describing welding path is selected\n  - The COM port of the laser is correct\n  - The IP address of the robot is correct\n  - The weld speed is less than 1000 mm/s\n  - An appropriate value for laser target current has been input.")


################################################################################
#   Function to Send Program to Robot and Begin Welding Process
################################################################################

    def startWelding(self, serialConnection, event=None):

        # CHECK ALL INPUTS FROM INTERFACE
      
        # Set laser current target at value previously set by user and
        # enable/disable pilot laser.
        if self.realLaser == 1:
            #Use real laser and set current
            self.setLaserCurrent(serialConnection)
            laserOnMessage = "LR"
            laserOffMessage = "LS"
        else:
            #Use pilot laser
            laserOnMessage = "PLR"
            laserOffMessage = "PLS"

        #Show that welding has begun.
        self.messageBoxText.set("Welding in progress...")
        
        # ROBOT CONNECTION AND SETUP
        # Connect to UR5 robot via Ethernet on port 30003, 125 Hz data stream.
        HOST = self.ipAddressText.get()     # The remote host: the robot
        PORT = 30003                        # The same port as used by the server: TCP port on robot
        if self.weldFlag == 0:
            # Connect to the robot if connection hasn't already been made
            self.robot = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.robot.connect((HOST, PORT))
        else:
            # If connection already made, redefine socket connection.
            self.robot.shutdown(socket.SHUT_RDWR)
            self.robot.close()
            self.robot = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.robot.connect((HOST, PORT))           
            
        #Indicate welding has begun and initialise values.
        self.weldFlag = 1
        self.weldStop = 0
        timeUR5Prev = "flag"
        programStatePrev = 1
        #Set initial state of laser as Off.
        laserCommandFlag = False
        
        # Sends program to robot and starts it immediately.
        with open(self.programName,'r+b') as self.program:
            self.robot.sendall(self.program.read())       
        self.weldLoop(programStatePrev, timeUR5Prev, laserCommandFlag, laserOnMessage, laserOffMessage)
            
    #Use "after" instead of while loop to avoid freezing GUI.      
    def weldLoop(self, programStatePrevious, timeUR5Previous, laserCommand, laserOn, laserOff, event=None):
        try:
            if self.weldStop == 0:
                messageLength = self.robot.recv(4)
                #messageLength = struct.unpack('!i', messageLength)[0]
                timeUR5 = self.robot.recv(8)
                unused_0 = self.robot.recv(576)
                toolPoseX = self.robot.recv(8)
                toolPoseY = self.robot.recv(8)
                toolPoseZ = self.robot.recv(8)
                toolPoseRX = self.robot.recv(8)
                toolPoseRY = self.robot.recv(8)
                toolPoseRZ = self.robot.recv(8)
                unused_1 = self.robot.recv(120)
                robotMode = self.robot.recv(8)
                unused_2 = self.robot.recv(280)
                digiOutputs = self.robot.recv(8)
                programMode = self.robot.recv(8)

                timeUR5 = struct.unpack('!d', timeUR5)[0]

                toolPoseZ = struct.unpack('!d', toolPoseZ)[0]
                toolPoseZ = toolPoseZ*1000

                robotMode = struct.unpack('!d', robotMode)[0]
                if robotMode != 7:
                    #print(robotMode)
                    ##msg.showwarning("Robot Stopping", "Robot Stopping - Emergency Stop")
                    self.stopWelding(self.robot, self.laser)
                
                # Program Mode tells us if the program is running or not (see "Client Interface.xls" for more information).
                # 1 means idle and 2 means program running.
                # 1's will be received briefly at start, so we are interested in
                # transition from 2 to 1.
                programState = struct.unpack('!d', programMode)[0]
                # If state changes, see if it changes to 1 and, if so, stop.
                #If not, update programStatePrev
                if programState != programStatePrevious:
                    if programState == 1:
                        #msg.showwarning("Robot Stopping", "Robot reached 'Idle' state.")
                        self.stopWelding(self.robot, self.laser)
                programStatePrevious = programState
                
                # Turn on (pilot) laser if the tool's Z coordinate wrt base is
                # at desired value, i.e. laser is focused on workpiece.
                if toolPoseZ <= -16:
                    if laserCommand == False:
                        laserCommand = True
                        # Send command to laser then read and print response.
                        self.laser.write(laserOn.encode('utf-8') + b'\r')
                        self.laserReplyText.set("LASER ON")
                        self.displayNames["self.statusDisplay_0"]['bg']="green"
                        #self.laserReplyText.set(self.laserResponse(serialConnection))
                    else:
                        laserCommand = True
                        
                # Turn off laser if the laser is not focusing on workpiece.
                else:
                    if laserCommand == True:
                        laserCommand = False
                        # Send command to laser then read and print response.
                        self.laser.write(laserOff.encode('utf-8') + b'\r')
                        self.laserReplyText.set("LASER OFF")
                        self.displayNames["self.statusDisplay_0"]['bg']="red"
                        #self.laserReplyText.set(self.laserResponse(serialConnection))
                    else:
                        laserCommand = False

                # Time the program takes to run.
                if timeUR5Previous == "flag":
                    self.time = 0
                    timeIncrement = 0
                else:
                    timeIncrement = timeUR5 - timeUR5Previous
                self.time = self.time + timeIncrement
                self.time = self.time
                timeUR5Previous = timeUR5
                timeString = "Time: " + str("%.2f"%self.time) + " seconds"
                self.timeLabelName.set(timeString)
                toolString = "Target Z Coord: " + str("%.2f"%(toolPoseZ+17))
                self.ZCoordLabelName.set(toolString)

                #Use "after" instead of while loop to avoid freezing GUI.
                self.weldJob = self.after(1, self.weldLoop, programStatePrevious, timeUR5Previous, laserCommand, laserOn, laserOff)
            else:
                return
        except Exception as error:
            self.stopWelding(self.robot, self.laser)
            msg.showerror("An error was encountered.", "Exception is: %s"%(error))
                    
####### End Function: Disconnect Safely From Laser and Robot    ##############################                                 
    def stopWelding(self, socketConnection, serialConnection, event=None):
        #Main and Pilot lasers turning off, target current being set to zero.
        #Turning off Temperature Controller.
        #Stop weldLoop from running
        self.weldStop = 1
        self.messageBoxText.set("Deactivating laser and stopping robot...")
        try:
            if self.weldJob is not None:
                self.after_cancel(self.weldJob)
                self.weldJob = None
        except AttributeError:
            pass
            
        ## Check status and print.
        self.laser.reset_input_buffer()
        self.getStatus(serialConnection,1)

        # Initialise flag indicating whether pilot, main laser, current and temp control are off.
        safetyCounter = 0
        responses = ["Laser Stop", "Laser Current Target:      0 mA", "Pilot Laser Stop"]

        # The following section requires the response from Laser to be
        # exactly as expected in order to confirm the desired settings
        # are in place.
        while safetyCounter < 3:
            for message in ["PLS", "LCT0", "LS"]:
                laserMessage = message
                laserWeld.laser.write(laserMessage.encode('utf-8') + b'\r')
                time.sleep(0.1)
                reply = laserWeld.laserResponse(laserWeld.laser)
                reply = reply.strip()
                laserWeld.laserReplyText.set(reply)
                if reply in responses:
                    safetyCounter += 1
                else:
                    KeyboardInterrupt
        
        # Make sure the robot is stopped. 
        #print("Stopping robot.")
        with open('stopRobot.txt','r+b') as self.stopCommand:
            self.robot.sendall(self.stopCommand.read())
        
        self.laserReplyText.set("Laser Turned Off")
        self.weldSpeedButton['bg'] = "azure3"
    
#################################################################################
#   Launch the GUI
#################################################################################

if __name__ == "__main__":

#Function to turn off laser if window is closed and laser serial connection is still active.
    def on_closing():
        try:
            responses = ["Laser Stop", "Laser Current Target:      0 mA", "Pilot Laser Stop", "Laser Temp. Ctrl. Stop"]
            if laserWeld.laser.is_open:
                #Check that correct responses are received after sending OFF commands to laser.
                for message in ["LS", "LCT0", "PLS", "TCS"]:
                    laserMessage = message
                    laserWeld.laser.write(laserMessage.encode('utf-8') + b'\r')
                    time.sleep(0.1)
                    reply = laserWeld.laserResponse(laserWeld.laser)
                    reply = reply.strip()
                    laserWeld.laserReplyText.set(reply)
                    if reply in responses:
                        pass
                    else:
                        KeyboardInterrupt

                #Check if socket to robot was made and, if so, close socket.
                if laserWeld.weldFlag:
                    if laserWeld.weldJob is not None:
                        laserWeld.after_cancel(laserWeld.weldJob)
                        laserWeld.weldJob = None
                    with open('stopRobot.txt','r+b') as stopRobot:
                        laserWeld.robot.sendall(stopRobot.read())
                    laserWeld.robot.shutdown(socket.SHUT_RDWR)
                    laserWeld.robot.close()
                    laserWeld.messageBoxText.set("Connection to Robot Closed")
                       
                if msg.askokcancel("Quit?", "Do you want to quit? \nLaser connection detected and closed. \nCheck that laser and robot are safely disconnected."):
                    # Delete files that were created.
                    if laserWeld.fileFlag == 1:
                        if laserWeld.programName != laserWeld.programNameOriginal:
                            laserWeld.program.close()
                            [os.remove(fileNames) for fileNames in laserWeld.graveyardList]
                    laserWeld.laser.close()
                    laserWeld.laserReplyText.set("Connection to Laser Closed")
                    #Unless never created, delete stopRobot file
                    if os.path.isfile('stopRobot.txt'):
                        os.remove('stopRobot.txt')
                    laserWeld.destroy()
        
            else:
                laserPort = laserWeld.portNumber.get()
                if laserPort != "" and laserPort != "Select...":
                    laser = serial.Serial()
                    laser.port = laserPort
                    laser.baudrate = 9600
                    laser.bytesize = serial.EIGHTBITS
                    laser.parity = serial.PARITY_NONE
                    laser.stopbits = serial.STOPBITS_ONE
                    laser.timeout = 0
                    laser.open()
                    #Check that correct responses are received after sending OFF commands to laser.
                    for message in ["LS", "LCT0", "PLS", "TCS"]:
                        laserMessage = message
                        laserWeld.laser.write(laserMessage.encode('utf-8') + b'\r')
                        time.sleep(0.1)
                        reply = laserWeld.laserResponse(laserWeld.laser)
                        reply = reply.strip()
                        laserWeld.laserReplyText.set(reply)
                        if reply in responses:
                            pass
                        else:
                            KeyboardInterrupt
                
                if msg.askokcancel("Quit?", "Do you want to quit? \nNo laser connection detected. \nCheck that laser and robot are safely disconnected."):
                    if laserWeld.fileFlag == 1:
                        if laserWeld.programName != laserWeld.programNameOriginal:
                            laserWeld.program.close()
                            [os.remove(fileNames) for fileNames in laserWeld.graveyardList]
                    #Unless never created, delete stopRobot file
                    if os.path.isfile('stopRobot.txt'):
                        os.remove('stopRobot.txt')
                    laserWeld.destroy()

        except Exception as shutdownError:
            msg.showerror("Error", "Ensure that the laser and pilot laser are off, target current is set to 0 mA and the temperature controller is off.\nException is: %s"%(shutdownError))

    laserWeld = LaserWeld()
    laserWeld.protocol("WM_DELETE_WINDOW", on_closing)
    laserWeld.mainloop()

