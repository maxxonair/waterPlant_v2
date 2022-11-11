#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon November  11 15s:41:05 2022
@author: x

@brief: Short function to read/parse irrigation json files
        This can be used to inspect the schedules or check
        that the syntax is correct and the files can be read
        before passing the to the client application
        
"""

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json
import numpy as np

from IrrigationSystem import IrrigationSystem

def readWateringJson( system ):
    with open(system.SCHEDULE_INPUT_PATH, 'r') as openfile:     
        return json.load(openfile)
    
# Functios: Update irrigation schedules for all systems from file 
def readIrrigationSchedules(system):
    
    print("[MSG] READ system: "+str(system.SCHEDULE_INPUT_PATH))
    print("")
    
    system.wateringJson = readWateringJson( system )
    system.wateringSchedule = []
    system.pumpTimes = []
    
    command_set = system.wateringJson['waterSets']
    nrPumps = 0
    
    for i, pump in enumerate( command_set ):
        system.wateringSchedule.append( pump['daily_schedule'] )
        system.weeklySchedule.append( pump['weekly_schedule'] )
        system.pumpTimes.append( pump['pump_cmd_times'] )
        nrPumps = i
        
    system.setNrPumps( nrPumps + 1 )

# Function extent input string with blank space to targetLength
def formatStringLength(strIn, targetLength):
    strOut = strIn
    while len(strOut) < targetLength:
        strOut=strOut+" "
    return strOut

# Function print summary of parsed irrigastion schedule  
def printSystemSummary(system):
    weekArray=['Monday    : ',
               'Tuesday   : ',
               'Wednesday : ',
               'Thursday  : ',
               'Friday    : ',
               'Saturday  : ',
               'Sunday    : ']
    print("----------------------------------------------")
    print("         [ SYSTEM SUMMARY ]")
    print(" System ID       : "+str(system.ID))
    print("")
    print(">> Parsed data   : ")
    print(" Number of Pumps : "+str(system.nr_pumps))
    print(" TM channel      : "+str(system.MQTT_TOPIC_TM))
    print(" TC channel      : "+str(system.MQTT_TOPIC_TC))
    
    for ii in range(system.nr_pumps):
        print("")
        print("----------------------------------------------")
        print(" [ Pump"+str(ii+1)+" ]")
        # Get schedules for each pump
        daily_schedule   = system.wateringSchedule[ii]
        weekly_schedule  = system.weeklySchedule[ii]
        activation_times = system.pumpTimes[ii]
        # check daily matches pump valve open 
        print("")
        print(" Daily Schedule: ")
        if len(daily_schedule) != len(activation_times):
            print("[WARNING] Length of daily schedule does not match length of pump activation commands")
            print("[WARNING] "+str(len(daily_schedule))+" vs "+str(len(activation_times)))
        elif len(daily_schedule) == 0:
            print("[MSG] No daily schedule defined!")
        else:
            print("[Scheduled Time HHMMSS] | [Pump On CMD] [ms]")
            for jj,time in enumerate(daily_schedule):
                print(formatStringLength(str(time), 24)+"| "+str(activation_times[jj]))
        
        print("")
        print(" Weekly Schedule: ")
        for jj,flag in enumerate(weekly_schedule):
            if flag == 1:
                print(str(weekArray[jj])+" ON")
            else:
                print(str(weekArray[jj])+" OFF")
    
    print("")
    print("----------------------------------------------")
    
def main():
    if len(sys.argv) != 2:
        print(" No system selected. Exiting")
        print("")
        print(" Run : $ "+str(sys.argv[0])+" 1")
        print(" Or  : $ "+str(sys.argv[0])+" 2")
        print("")
        sys.exit(0)
        
    system_id=int(sys.argv[1])

    if system_id < 1 or system_id > 2:
        print("")
        print("System ID not valid for this architecture. Choose 1 or 2. ")
        print("Exiting.")
        print("")
        return 1

    print("")
    # Initialize system instance 
    system = IrrigationSystem(system_id)
    
    # Read irrigation schedules
    readIrrigationSchedules(system)
    
    # Print system summary and schedules 
    printSystemSummary(system)
    
if __name__=='__main__':
    main()