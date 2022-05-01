#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Apr 30 09:25:16 2022

@author: x
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqttClient
from datetime import date
from datetime import datetime
import time 
import numpy as np


delimiter = ','
# File path to data file
FILEPATH = './waterPlantCtrl_LOG.csv'

VOLTAGE_FILE_PATH = "./waterPlant_Voltage.csv"
# MQTT subscription top
MQTT_TOPIC_TM = "home/waterPlant/TM"
MQTT_TOPIC_TC = "home/waterPlant/TC"
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

# Pump on commands per scheduled watering [ pump01, pump02 ]
on_time_pumps_ms = [500,500]

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
                         + str( on_time_pumps_ms[0]))

TC_CMD_PUMP02  = (    TC_IDENTIFIER 
                         + TC_DELIMITER 
                         + TC_CMD_PUMP02_ON_TIME 
                         + TC_DELIMITER 
                         + str( on_time_pumps_ms[1]))


# Watering Schedule
# Array where watering times in int (HHMMSS) are stored 
wateringSchedule  = [[ 81000, 201000],[ 82000, 201000]]
# Watering punch card
# array with boolean value for each watering element 
# true  - watering done for current day 
# false - watering to be done for current day 
wateringPunchCard = np.full_like(wateringSchedule, False)

# Variable to keep track of the current day
# This is used to reset the watering punch card
currentDate = 0

#create new instance
client = mqttClient.Client("waterPlant")   


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("["+str(getDateString())+"]["+str(getTime())+"] Connected to broker")
        #Use global variable
        global Connected                
        #Signal connection
        Connected = True                
    else:
        print("[ERR] Connection failed")

def on_message( client, userdata, message):
    sMessage = str( message.payload )
    print("["+str(getDateString())+"]["+str(getTime())+"] Message received: "+str(message.payload))
    # Update date counter
    # updateCurrentDate()  
    
    # Parse any message for info on voltage level
    # parseVoltageTm( sMessage )
    
    if ( isWakeStatus( sMessage ) ):
        keepAwake()
        
def updateCurrentDate():
    global currentDate
    global wateringPunchCard
    if ( currentDate < int( getDateString()) ):
        print("["+str(getDateString())+"]["+str(getTime())+"] Update Date. ")
        currentDate = int( getDateString() )
        wateringPunchCard = np.full_like(wateringSchedule, False)

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
    aElements = sMessage.split("]")
    for element in aElements:
        msg = element.replace('[','').replace(' ','').replace('.','')
        if msg == 'Awake':
            return True
    return False

def parseVoltageTm( sMessage):
    aElements = sMessage.split("]")
    msgElements = []
    for i, element in enumerate(aElements):
        msgElements.append( element.replace('[','').replace(' ','') )

    if (msgElements[0] == "WaterPlant" and msgElements[1] == "TM") :
        msgBody = msgElements[2]
        bodyParts = msgBody.split(":")
        if ( bodyParts[0] == "BatteryVoltage" and len( bodyParts) > 1 ):
            print("["+str(getDateString())+"]["+str(getTime())+"] Volatage update noted: ")
            sLine = ( str( getDateString()) 
            + delimiter
            + str( getTime() )
            + delimiter
            + str( bodyParts[1] ) )
            appendLineToCsv( VOLTAGE_FILE_PATH, sLine )

def executeWakeRoutine():
    # Set sleep mode to false
    # This is to ensure there is enough time to execute all commands
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: Keep awake. ")
    client.publish(MQTT_TOPIC_TC, TC_STAY_AWAKE) 
    time.sleep(0.8)

    # Request voltage 
    print("["+str(getDateString())+"]["+str(getTime())+"] Request voltage update.")
    client.publish(MQTT_TOPIC_TC, TC_REQUEST_VOLTAGE) 
    time.sleep(0.8)
    # Check for active pump commands
    isTime = int( getTime() )
    for i, pump in enumerate( wateringSchedule ):
        for j, timeslot in enumerate( pump ):
            if ( isTime > timeslot and wateringPunchCard[i][j] == 0 ):
                # execute pump command 
                if ( i == 0 ):
                    # pump 01
                    print("["+str(getDateString())+"]["+str(getTime())+"] Command pump 1")
                    client.publish(MQTT_TOPIC_TC, TC_CMD_PUMP01) 
                    time.sleep(0.8)
                elif ( i == 1 ):
                    # pump 02 
                    print("["+str(getDateString())+"]["+str(getTime())+"] Command pump 2")
                    client.publish(MQTT_TOPIC_TC, TC_CMD_PUMP02) 
                    time.sleep(0.8)
                # update punch card 
                wateringPunchCard[i][j] = 1
            
    # Set sleep mode to true 
    time.sleep(1.5)
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: activate sleep")
    client.publish(MQTT_TOPIC_TC, TC_ENABLE_SLEEP)  
    
def keepAwake():
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: Keep awake. ")
    client.publish(MQTT_TOPIC_TC, TC_STAY_AWAKE) 
    

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
client.subscribe(MQTT_TOPIC_TM) 

client.loop_forever() 
