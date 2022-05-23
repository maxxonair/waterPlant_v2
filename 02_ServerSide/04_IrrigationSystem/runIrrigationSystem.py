#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  2 08:41:05 2022

@author: x
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqttClient
from datetime import date
from datetime import datetime
import time 
import json
import numpy as np

# Enable logging of voltage levels at each wake up cycle 
flag_enable_voltage_req_system_01 = True
flag_enable_voltage_req_system_02 = False

delimiter = ','
# File path to data file
FILEPATH = './waterPlantCtrl_LOG.csv'

SCHEDULE_INPUT_PATH_01 = '../03_IrrigationSchedules/wateringTimes_system_01.json'
SCHEDULE_INPUT_PATH_02 = '../03_IrrigationSchedules/wateringTimes_system_02.json'

PUNCHCARD_PATH_01 = '../03_IrrigationSchedules/wateringPunchCard_system_01.json'
PUNCHCARD_PATH_02 = '../03_IrrigationSchedules/wateringPunchCard_system_02.json'

VOLTAGE_FILE_PATH_01 = "../01_VoltageLogs/waterPlant_01_Voltage.csv"
VOLTAGE_FILE_PATH_02 = "../01_VoltageLogs/waterPlant_02_Voltage.csv"

# MQTT subscription top
MQTT_TOPIC_TM_SYSTEM_01 = "home/waterPlant/TM"
MQTT_TOPIC_TC_SYSTEM_01 = "home/waterPlant/TC"
MQTT_TOPIC_TM_SYSTEM_02 = "home/waterPlant2/TM"
MQTT_TOPIC_TC_SYSTEM_02 = "home/waterPlant2/TC"
#global variable for the state of the connection
Connected = False
#Broker address
broker_address = "192.168.1.198"
#Broker port
port           = 1883
#Connection username
user           = "box"
#Connection password
password       = "box"

TC_DELIMITER                   = ";"
TC_IDENTIFIER                  = "[TC]"
# Parameter Identifier 
# Parameter changes
TC_PARAM_DEEP_SLEEP_INTERVAL   = "PARAM_DEEP_SLEEP_TIME"
TC_PARAM_MAX_PUMP_INTERVAL     = "PARAM_MAX_PUMP_TIME"
TC_PARAM_AWAKE_INTERVAL        = "PARAM_AWAKE_TIME"
TC_PARAM_SET_DEEP_SLEEP        = "PARAM_SET_DEEP_SLEEP"
TC_PARAM_SET_MODE              = "PARAM_SET_MODE"
# Execution commands
TC_CMD_PUMP01_ON_TIME          = "CMD_PUMP01_ON_TIME"
TC_CMD_PUMP02_ON_TIME          = "CMD_PUMP02_ON_TIME"
# Status requests
TC_REQ_VOLTAGE                 = "REQUEST_VOLTAGE"
TC_REQ_ACKN                    = "REQUEST_ACKN"
TC_REQ_SLEEP                   = "REQUEST_SLEEP";

# System ID's :
SYSTEM_01 = 1
SYSTEM_02 = 2

# Pump ID's : 
PUMP_01 = 1
PUMP_02 = 2

# COMPILED TC's
TC_STAY_AWAKE = (  TC_IDENTIFIER 
                 + TC_DELIMITER 
                 + TC_PARAM_SET_DEEP_SLEEP 
                 + TC_DELIMITER 
                 + "0")

TC_ENABLE_SLEEP = (    TC_IDENTIFIER 
                     + TC_DELIMITER 
                     + TC_REQ_SLEEP 
                     + TC_DELIMITER 
                     + "1")

TC_REQUEST_VOLTAGE  = (    TC_IDENTIFIER 
                         + TC_DELIMITER 
                         + TC_REQ_VOLTAGE 
                         + TC_DELIMITER 
                         + "0")

TC_CMD_PUMP01  = (    TC_IDENTIFIER 
                         + TC_DELIMITER 
                         + TC_CMD_PUMP01_ON_TIME 
                         + TC_DELIMITER 
                         + str( 0 ))

TC_CMD_PUMP02  = (    TC_IDENTIFIER 
                         + TC_DELIMITER 
                         + TC_CMD_PUMP02_ON_TIME 
                         + TC_DELIMITER 
                         + str( 0 ))


# Watering Schedule
# Array where watering times in int (HHMMSS) are stored 
wateringSchedule_system_01  = []
wateringSchedule_system_02  = []

weeklySchedule_system_01 = []
weeklySchedule_system_02 = []
# Watering punch card
# array with boolean value for each watering element 
# true  - watering done for current day 
# false - watering to be done for current day 
wateringPunchCard_system_01 = []
wateringPunchCard_system_02 = []

# Variable to keep track of the current day
# This is used to reset the watering punch card
currentDate = 0

# Full Json file content 
wateringJson_system_01 = []
wateringJson_system_02 = []


# Arrays with pump ON cmd times [ms]
pumpTimes_system_01 = []
pumpTimes_system_02 = []

#create new instance
client = mqttClient.Client("waterPlant")  

def compilePumpCommand(pumpID_TC, onTime):
    TC_CMD_PUMP  = (    TC_IDENTIFIER 
                             + TC_DELIMITER 
                             + pumpID_TC 
                             + TC_DELIMITER 
                             + str( onTime ))
    return TC_CMD_PUMP


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("["+str(getDateString())+"]["+str(getTime())+"] Connected to broker")
        #Use global variable
        global Connected                
        #Signal connection
        Connected = True  
        
        try:
            updateCurrentDate(SYSTEM_01) 
        except:
            print("["+str(getDateString())+"]["+str(getTime())+"] Update System 01 failed. ")
        try:
            updateCurrentDate(SYSTEM_02)     
        except:
            print("["+str(getDateString())+"]["+str(getTime())+"] Update System 02 failed. ")
    else:
        print("[ERR] Connection failed")

def on_message( client, userdata, message):
    sMessage = str( message.payload )
    sTopic = str( message.topic )
    
    print("["+str(getDateString())+"]["+str(getTime())+"] Message received: ")
    print("["+str(getDateString())+"]["+str(getTime())+"] Topic   : "+sTopic)
    print("["+str(getDateString())+"]["+str(getTime())+"] Message : "+sMessage)
    
    # Update date counter
    if isTmSystem01( sTopic ) :
        try:
            updateCurrentDate(SYSTEM_01) 
        except:
            print("["+str(getDateString())+"]["+str(getTime())+"] Update System 01 failed. ")
        
        # Parse any message for info on voltage level
        if flag_enable_voltage_req_system_01 == True:
            try:
                parseVoltageTm(SYSTEM_01, sMessage )
            except:
                print("["+str(getDateString())+"]["+str(getTime())+"] Parsing Voltage System 01 failed. ")
                
            
            
        # [!] Execute System Routine:
        if ( isWakeStatus( sMessage ) ):
            try:
                executeWakeRoutine(SYSTEM_01)
            except:
                print("["+str(getDateString())+"]["+str(getTime())+"] Execute routine System 01 failed. ")
                
            
    if isTmSystem02( sTopic ):
        try:
            updateCurrentDate(SYSTEM_02) 
        except:
            print("["+str(getDateString())+"]["+str(getTime())+"] Update System 02 failed. ")  
        
        # Parse any message for info on voltage level
        if flag_enable_voltage_req_system_02 == True :
            try:
                parseVoltageTm(SYSTEM_02, sMessage )
            except:
                print("["+str(getDateString())+"]["+str(getTime())+"] Parsing Voltage System 02 failed. ")
        
        # [!] Execute System Routine:
        if ( isWakeStatus( sMessage ) ):
            try:
                executeWakeRoutine(SYSTEM_02)
            except:
                print("["+str(getDateString())+"]["+str(getTime())+"] Execute routine System 01 failed. ")
        
def isTmSystem01( sTopic ):
    if MQTT_TOPIC_TM_SYSTEM_01 in sTopic :
        return True 
    else :
        return False
    
def isTmSystem02( sTopic ):
    if MQTT_TOPIC_TM_SYSTEM_02 in sTopic :
        return True 
    else :
        return False
        
def updateCurrentDate(systemID):
    global currentDate
    if ( currentDate < int( getDateString()) ):
        print("["+str(getDateString())+"]["+str(getTime())+"] Update Date. ")
        currentDate = int( getDateString() )
        
        resetPunchCard(systemID)
        readIrrigationSchedules()
    else:
        checkForcedUpdate(systemID)
        
def checkForcedUpdate(systemID):
    wateringJson_system = []
    # Read data from json 
    wateringJson_system = readWateringJson(systemID)
        
    settings = wateringJson_system['Settings']
    if settings['force_update'] == 1 :
        # Acknowledge forced update and write back 0
        settings['force_update'] = 0
        wateringJson_system['Settings'] = settings
        writeWateringJson(systemID, wateringJson_system)
        
        # Update watering times 
        if systemID == SYSTEM_01:
            global wateringSchedule_system_01
            wateringSchedule_system_01 = readWateringJson(SYSTEM_01)
        if systemID == SYSTEM_02:
            global wateringSchedule_system_02
            wateringSchedule_system_02 = readWateringJson(SYSTEM_02)
        
    
def readWateringJson( systemID ):
    if systemID == SYSTEM_01:
        with open(SCHEDULE_INPUT_PATH_01, 'r') as openfile:     
            return json.load(openfile)
    if systemID == SYSTEM_02:
        with open(SCHEDULE_INPUT_PATH_02, 'r') as openfile:     
            return json.load(openfile)
            
def writeWateringJson( systemID, wateringData ):
    if systemID == SYSTEM_01:
        with open(SCHEDULE_INPUT_PATH_01, 'w', encoding='utf-8') as f:
            json.dump(wateringData, f, ensure_ascii=False, indent=4)
    if systemID == SYSTEM_02:
        with open(SCHEDULE_INPUT_PATH_02, 'w', encoding='utf-8') as f:
            json.dump(wateringData, f, ensure_ascii=False, indent=4)
            
def writePunchCardJson( systemID, punchCard ):
    try:
        if systemID == SYSTEM_01:
            with open(PUNCHCARD_PATH_01, 'w', encoding='utf-8') as f:
                json.dump(punchCard, f, ensure_ascii=False, indent=4)
        if systemID == SYSTEM_02:
            with open(PUNCHCARD_PATH_02, 'w', encoding='utf-8') as f:
                json.dump(punchCard, f, ensure_ascii=False, indent=4)
    except:
        print('Writing udpated punch card for system'+str(systemID)+' failed.')
# Function return the current day of the week as int
# e.g. 0 - monday 
#      1 - tuesday 
def getWeekday():
    return datetime.today().weekday()
        
def readIrrigationSchedules():
    global wateringJson_system_01
    global wateringJson_system_02
    global wateringSchedule_system_01
    global wateringSchedule_system_02
    global pumpTimes_system_01
    global pumpTimes_system_02
    global wateringPunchCard_system_01
    global wateringPunchCard_system_02
    global weeklySchedule_system_01
    global weeklySchedule_system_02
    
    # Read data from json 
    wateringJson_system_01 = readWateringJson(SYSTEM_01)
    wateringJson_system_02 = readWateringJson(SYSTEM_02)
    
    wateringSchedule_system_01 = []
    wateringSchedule_system_02 = []
    pumpTimes_system_01 = []
    pumpTimes_system_02 = []
    
    command_set_system_01 = wateringJson_system_01['waterSets']
    command_set_system_02 = wateringJson_system_02['waterSets']
    
    for i, pump in enumerate( command_set_system_01 ):
        wateringSchedule_system_01.append( pump['daily_schedule'] )
        weeklySchedule_system_01.append( pump['weekly_schedule'] )
        pumpTimes_system_01.append( pump['pump_cmd_times'] )
        
    for i, pump in enumerate( command_set_system_02 ):
        wateringSchedule_system_02.append( pump['daily_schedule'] )
        weeklySchedule_system_02.append( pump['weekly_schedule'] )
        pumpTimes_system_02.append( pump['pump_cmd_times'] )
        
    # Reset Watering punch card
    # array with boolean value for each watering element 
    # true  - watering done for current day 
    # false - watering to be done for current day 
    resetPunchCard(SYSTEM_01)
    resetPunchCard(SYSTEM_02)
    # Update punch card and disregard schedule times in the past for current 
    # date
    isTime = int( getTime() )
    for i, pump in enumerate( wateringSchedule_system_01 ):
        for j, timeslot in enumerate( pump ):
            if ( isTime > timeslot ):
                # Update punch card 
                wateringPunchCard_system_01[i][j] == 1
    for i, pump in enumerate( wateringSchedule_system_02 ):
        for j, timeslot in enumerate( pump ):
            if ( isTime > timeslot ):
                # Update punch card 
                wateringPunchCard_system_02[i][j] == 1

def resetPunchCard(systemID):
    if systemID == SYSTEM_01:
        global wateringSchedule_system_01
        global wateringPunchCard_system_01
        wateringPunchCard_system_01 = []
    
        for pump in wateringSchedule_system_01:
            listofzeros = np.full_like(pump, int(0) )
            wateringPunchCard_system_01.append(listofzeros)
            writePunchCardJson(systemID, wateringPunchCard_system_01)
    if systemID == SYSTEM_02:
        global wateringSchedule_system_02
        global wateringPunchCard_system_02
        wateringPunchCard_system_02 = []
    
        for pump in wateringSchedule_system_02:
            listofzeros = np.full_like(pump, int(0) )
            wateringPunchCard_system_02.append(listofzeros)
            writePunchCardJson(systemID, wateringPunchCard_system_02)
    

def createTimeTag():
    today = date.today()
    now = datetime.now()
    dateToday = today.strftime("%Y%m%d")
    timeToday = now.strftime("%H:%M:%S")
    return (dateToday+"_"+timeToday)

def appendLineToCsv(sFilePath, sLine):
    with open(sFilePath,'a+') as f:
        f.write(sLine + "\n")

def getTime():
    now = datetime.now() 
    timeToday = int( now.strftime("%H%M%S") )
    return timeToday

def getDateString():
    today = date.today()
    return str(today.strftime("%Y%m%d"))


def isWakeStatus( sMessage ):
    if 'Awake' in sMessage :
        return True 
    else :
        return False

def parseVoltageTm( systemID, sMessage):
    output_file_path = ""
    if systemID == SYSTEM_01:
        output_file_path = VOLTAGE_FILE_PATH_01
    if systemID == SYSTEM_02: 
        output_file_path = VOLTAGE_FILE_PATH_02
    aElements = sMessage.split("]")
    msgElements = []
    for i, element in enumerate(aElements):
        msgElements.append( element.replace('[','').replace(' ','') )

    if (msgElements[0] == "WaterPlant" and msgElements[1] == "TM") :
        msgBody = msgElements[2]
        bodyParts = msgBody.split(":")
        if ( bodyParts[0] == "BatteryVoltage" and len( bodyParts) > 1 ):
            print("["+str(getDateString())+"]["+str(getTime())+"] Voltage update noted: ")
            sLine = ( str( getDateString()) 
            + delimiter
            + str( getTime() )
            + delimiter
            + str( bodyParts[1] ) )
            appendLineToCsv( output_file_path, sLine )

def executeWakeRoutine(systemID):
    print("["+str(getDateString())+"]["+str(getTime())+"] Execute routine system "+str(systemID))
    tc_topic = ""
    wateringPunchCard = []
    wateringSchedule  = []
    weeklySchedule    = []
    pumpTimes         = []
    global wateringPunchCard_system_01
    global wateringPunchCard_system_02
    if systemID == SYSTEM_01:
        tc_topic          = MQTT_TOPIC_TC_SYSTEM_01
        wateringPunchCard = wateringPunchCard_system_01
        wateringSchedule  = wateringSchedule_system_01
        weeklySchedule    = weeklySchedule_system_01
        pumpTimes         = pumpTimes_system_01
    elif systemID == SYSTEM_02: 
        tc_topic          = MQTT_TOPIC_TC_SYSTEM_02
        wateringPunchCard = wateringPunchCard_system_02
        wateringSchedule  = wateringSchedule_system_02
        weeklySchedule    = weeklySchedule_system_02
        pumpTimes         = pumpTimes_system_02
    # Set sleep mode to false
    # This is to ensure there is enough time to execute all commands
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: Keep awake. ")
    client.publish(tc_topic, TC_STAY_AWAKE) 
    time.sleep(0.8)

    # Request voltage 
    print("["+str(getDateString())+"]["+str(getTime())+"] Request voltage update.")
    client.publish(tc_topic, TC_REQUEST_VOLTAGE) 
    time.sleep(0.8)
    # Check for active pump commands
    isTime = int( float( getTime() ) )
    for i, pump in enumerate( wateringSchedule ):
        weekSc = weeklySchedule[int(i)]
        if int( weekSc[int(getWeekday())] ) == 1:
            for j, timeslot in enumerate( pump ):
                if ( isTime > int( float( timeslot ) ) and int( float(wateringPunchCard[i][j]) ) == 0 ):
                    # execute pump command 
                    if ( int(i) == 0 ):
                        # pump 01
                        cmd = compilePumpCommand(TC_CMD_PUMP01_ON_TIME, pumpTimes[i][j])
                        print("["+str(getDateString())+"]["+str(getTime())+"] Command pump 1")
                        client.publish(tc_topic, cmd) 
                        time.sleep(0.8)
                    elif ( int(i) == 1 ):
                        # pump 02 
                        cmd = compilePumpCommand(TC_CMD_PUMP02_ON_TIME, pumpTimes[i][j])
                        print("["+str(getDateString())+"]["+str(getTime())+"] Command pump 2")
                        client.publish(tc_topic, cmd) 
                        time.sleep(0.8)
                    # update punch card 
                    wateringPunchCard[i][j] = 1
            
    # Set sleep mode to true 
    time.sleep(1.5)
    # Write updated punch card back to global variable 
    if systemID == SYSTEM_01:
        wateringPunchCard_system_01 = wateringPunchCard
    if systemID == SYSTEM_02:
        wateringPunchCard_system_02 = wateringPunchCard
    # Update punch card Json 
    writePunchCardJson(systemID, wateringPunchCard)
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: activate sleep")
    client.publish(tc_topic, TC_ENABLE_SLEEP)  

def setDate():
    global currentDate
    today = date.today()
    dateToday = today.strftime("%Y%m%d")
    currentDate=str(dateToday)


    
#set username and password
client.username_pw_set(user, password=password)
#attach function to callback
client.on_connect= on_connect
#attach function to callback
client.on_message= on_message   
      
client.connect(broker_address,port,60)
client.subscribe(MQTT_TOPIC_TM_SYSTEM_01)
client.subscribe(MQTT_TOPIC_TM_SYSTEM_02)

client.loop_forever()