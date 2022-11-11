#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Jun  9 19:58:39 2022

@author: x
"""

class IrrigationSystem:
    
    ID = -1 
    
    # Enable Voltage requests 
    flag_enable_voltage_req = False
    
    # Number of pumps within the irrigation system 
    nr_pumps = 0
    
    # Watering Schedule
    # Array where watering times in int (HHMMSS) are stored 
    wateringSchedule  = []

    weeklySchedule = []
    # Watering punch card
    # array with boolean value for each watering element 
    # true  - watering done for current day 
    # false - watering to be done for current day 
    wateringPunchCard = []
    
    # Full Json file content 
    wateringJson = []

    # Arrays with pump ON cmd times [ms]
    pumpTimes = []
    
    TC_CMDS_PUMP_ON_TIME          = []
    
    def __init__(self, ID):
        
        self.ID = ID
        
        self.SCHEDULE_INPUT_PATH = "../03_IrrigationSchedules/wateringTimes_system_0"+str(ID)+".json"

        self.PUNCHCARD_PATH = "../03_IrrigationSchedules/wateringPunchCard_system_0"+str(ID)+".json"

        self.VOLTAGE_FILE_PATH = "../01_VoltageLogs/waterPlant_0"+str(ID)+"_Voltage.csv"
        
        # MQTT subscription top
        if ID == 1 :
            self.MQTT_TOPIC_TM = "home/waterPlant/TM"
            self.MQTT_TOPIC_TC = "home/waterPlant/TC"
        else:
            self.MQTT_TOPIC_TM = "home/waterPlant"+str(ID)+"/TM"
            self.MQTT_TOPIC_TC = "home/waterPlant"+str(ID)+"/TC"
            
    def setNrPumps(self, numberOfPumps):
        self.nr_pumps = numberOfPumps
        self.TC_CMDS_PUMP_ON_TIME          = []
        for ii in range(self.nr_pumps):
           self.TC_CMDS_PUMP_ON_TIME.append( "CMD_PUMP0"+str(ii+1)+"_ON_TIME")
           
    def isTmAddressingThisSystem(self, sTopic ):
        if self.MQTT_TOPIC_TM in sTopic :
            return True 
        else :
            return False
        