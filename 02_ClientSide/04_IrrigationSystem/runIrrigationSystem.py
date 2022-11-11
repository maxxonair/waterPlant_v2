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

from IrrigationSystem import IrrigationSystem
# -----------------------------------------------------------------------------
# Setup Irrigation System 
NR_SYSTEMS = 2

# List of irrigation systems (self standing network of pumps with dedicated 
# MQTT channels/topics )
system = []

for ii in range(NR_SYSTEMS):
    system_id = ii + 1
    system.append( IrrigationSystem(system_id) )
    
system[0].flag_enable_voltage_req = False
system[0].setNrPumps(4)

system[1].flag_enable_voltage_req = False
system[1].setNrPumps(2)
# -----------------------------------------------------------------------------
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

delimiter = ','
# File path to data file
FILEPATH = './waterPlantCtrl_LOG.csv'

TC_DELIMITER                   = ";"
TC_IDENTIFIER                  = "[TC]"
# Parameter Identifier 
# Parameter changes
TC_PARAM_DEEP_SLEEP_INTERVAL   = "PARAM_DEEP_SLEEP_TIME"
TC_PARAM_MAX_PUMP_INTERVAL     = "PARAM_MAX_PUMP_TIME"
TC_PARAM_AWAKE_INTERVAL        = "PARAM_AWAKE_TIME"
TC_PARAM_SET_DEEP_SLEEP        = "PARAM_SET_DEEP_SLEEP"
TC_PARAM_SET_MODE              = "PARAM_SET_MODE"
# Status requests
TC_REQ_VOLTAGE                 = "REQUEST_VOLTAGE"
TC_REQ_ACKN                    = "REQUEST_ACKN"
TC_REQ_SLEEP                   = "REQUEST_SLEEP";

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

# Variable to keep track of the current day
# This is used to reset the watering punch card
currentDate = 0

#create new instance
client = mqttClient.Client("box")  

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
        global system              
        #Signal connection
        Connected = True  
        
        for ii in range(NR_SYSTEMS):
            try:
                updateCurrentDate(ii+1) 
            except:
                print("["+str(getDateString())+"]["+str(getTime())+"] Update System "+str(ii+1)+" failed. ")
    else:
        print("[ERR] Connection failed")

def on_message( client, userdata, message):
    global system
    sMessage = str( message.payload )
    sTopic = str( message.topic )
    
    print("["+str(getDateString())+"]["+str(getTime())+"] Message received: ")
    print("["+str(getDateString())+"]["+str(getTime())+"] Topic   : "+sTopic)
    print("["+str(getDateString())+"]["+str(getTime())+"] Message : "+sMessage)
    
    # Update date counter
    for ii in range(NR_SYSTEMS):
        system_id = ii + 1
        if system[ii].isTmAddressingThisSystem( sTopic ) :
            try:
                updateCurrentDate( system_id ) 
            except:
                print("["+str(getDateString())+"]["+str(getTime())+"] Update System "+str(system_id)+" failed. ")
            
            # Parse any message for info on voltage level
            if system[ii].flag_enable_voltage_req == True:
                try:
                    parseVoltageTm( system_id, sMessage )
                except:
                    print("["+str(getDateString())+"]["+str(getTime())+"] Parsing Voltage System "+str(system_id)+" failed. ")
            
            # [!] Execute System Routine:
            if ( isWakeStatus( sMessage ) ):
                # try:
                executeWakeRoutine( system_id )
                # except:
                #     print("["+str(getDateString())+"]["+str(getTime())+"] Execute routine System "+str(ii+1)+" failed. ")
        
def updateCurrentDate(systemID):
    global currentDate
    global system 
    
    if ( currentDate < int( getDateString()) ):
        print("["+str(getDateString())+"]["+str(getTime())+"] Update Date. ")
        currentDate = int( getDateString() )
    
        # New day -> reset punch cards
        resetPunchCard( systemID )
        # Read irrigation schedule from file 
        readIrrigationSchedules()   
    
def readWateringJson( systemID ):
    global system 
    
    with open(system[(systemID-1)].SCHEDULE_INPUT_PATH, 'r') as openfile:     
        return json.load(openfile)
            
def writeWateringJson( systemID, wateringData ):
    global system 
    with open(system[(systemID-1)].SCHEDULE_INPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(wateringData, f, ensure_ascii=False, indent=4)
           
def writePunchCardJson( systemID ):
    global system 
    try:
        with open(system[(systemID-1)].PUNCHCARD_PATH, 'w', encoding='utf-8') as f:
            json.dump(system[(systemID-1)].wateringPunchCard, f, ensure_ascii=False, indent=4)
    except:
        print('Writing udpated punch card for system'+str(systemID)+' failed.')
        
# Function return the current day of the week as int
# e.g. 0 - monday 
#      1 - tuesday 
def getWeekday():
    return datetime.today().weekday()
        
# Functios: Update irrigation schedules for all systems from file 
# Note: This resets all punch cards 
def readIrrigationSchedules():
    global system
    
    # Read data from json 
    for ii in range(NR_SYSTEMS):
        
        system_id = ii + 1
        
        system[ii].wateringJson = readWateringJson( system_id )
        
        system[ii].wateringSchedule = []

        system[ii].pumpTimes = []
        
        command_set = system[ii].wateringJson['waterSets']
        nrPumps = 0
        
        for i, pump in enumerate( command_set ):
            system[ii].wateringSchedule.append( pump['daily_schedule'] )
            system[ii].weeklySchedule.append( pump['weekly_schedule'] )
            system[ii].pumpTimes.append( pump['pump_cmd_times'] )
            nrPumps = i
            
        system[ii].setNrPumps( nrPumps + 1 )
            
        # Reset Watering punch card
        # array with boolean value for each watering element 
        # true  - watering done for current day 
        # false - watering to be done for current day 
        resetPunchCard( system_id )

        # Update punch card and disregard schedule times in the past for current 
        # date
        isTime = int( getTime() )
        for i, pump in enumerate( system[ii].wateringSchedule ):
            for j, timeslot in enumerate( pump ):
                if ( isTime > timeslot ):
                    # Update punch card 
                    system[ii].wateringPunchCard[i][j] == 1

def resetPunchCard(systemID):
    global system
    
    system[systemID-1].wateringPunchCard = []

    for pump in system[systemID-1].wateringSchedule:
        listofzeros = np.full_like(pump, int(0) )
        system[systemID-1].wateringPunchCard.append(listofzeros)
        writePunchCardJson(systemID)
        
def createTimeTag():
    today = date.today()
    now   = datetime.now()
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
    global system
    
    # Only parse voltage TM if request is enabled for respective system
    if system[systemID-1].flag_enable_voltage_req == True :
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
                appendLineToCsv( system[(systemID-1)].VOLTAGE_FILE_PATH, sLine )

def executeWakeRoutine(systemID):
    global system
    
    systemIndex = systemID - 1
    print("["+str(getDateString())+"]["+str(getTime())+"] Execute routine system "+str(systemID))

    # Set sleep mode to false
    # This is to ensure there is enough time to execute all commands
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: Keep awake. ")
    client.publish(system[systemIndex].MQTT_TOPIC_TC, TC_STAY_AWAKE) 
    time.sleep(0.8)

    # Request voltage 
    if system[systemID-1].flag_enable_voltage_req == True :
        print("["+str(getDateString())+"]["+str(getTime())+"] Request voltage update.")
        client.publish(system[systemIndex].MQTT_TOPIC_TC, TC_REQUEST_VOLTAGE) 
        time.sleep(0.8)
        
    # Check for active pump commands
    isTime = int( float( getTime() ) )
    for i, pump in enumerate( system[systemIndex].wateringSchedule ):
        weekSc = system[systemIndex].weeklySchedule[int(i)]
        if int( weekSc[int(getWeekday())] ) == 1:
            for j, timeslot in enumerate( pump ):
                if ( isTime > int( float( timeslot ) ) and int( float(system[systemIndex].wateringPunchCard[i][j]) ) == 0 ):
                    # execute pump command 
                    cmd = compilePumpCommand(system[systemIndex].TC_CMDS_PUMP_ON_TIME[i], system[systemIndex].pumpTimes[i][j])
                    print("["+str(getDateString())+"]["+str(getTime())+"] Command pump "+str(j+1))
                    client.publish(system[systemIndex].MQTT_TOPIC_TC, cmd) 
                    time.sleep(0.8)
                    # update punch card 
                    system[systemIndex].wateringPunchCard[i][j] = 1
            
    # Set sleep mode to true 
    time.sleep(1.5)
    # Update punch card Json 
    # TODO: this is currently not working and needs to be fixed 
    # writePunchCardJson( systemID )
    print("["+str(getDateString())+"]["+str(getTime())+"] Cmd: activate sleep")
    client.publish(system[systemIndex].MQTT_TOPIC_TC, TC_ENABLE_SLEEP)  

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
for ii in range(NR_SYSTEMS):
    client.subscribe(system[ii].MQTT_TOPIC_TM)

client.loop_forever()