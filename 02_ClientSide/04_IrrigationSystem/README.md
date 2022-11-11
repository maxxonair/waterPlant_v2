
Second attempt to create a useful plant feeder. This repository contains the code to control a D1 mini based plant feeder from a server script via MQTT. 

# Content and Description

## Basic architecture

TODO

## Folder content 
**01_D1_Firmware** contains the firmware code to be uploaded to the D1, which controls the irrigation pumps for a system. Don't forget to change Wifi & MQTT settings to your liking. 

**02_ClientSide** contains the python script to be run on the server. (use tmux to run it in the background or set it up to be executed automatically at reboot, e.g. sudo nano /etc/rc.local). 

**03_Test_TCs** contains some useful test tele-commands to be run from any device connected to the mqtt broker

**04_Support_Scripts** contains various scripts to support the work with the client.

This obviously requires mqtt to be set up with a running broker on the server side. 

Check out:

http://www.steves-internet-guide.com/into-mqtt-python-client/

http://www.steves-internet-guide.com/mqtt-username-password-example/

https://randomnerdtutorials.com/testing-mosquitto-broker-and-client-on-raspbbery-pi/

or similar tutorials to set it up. 

## Run the client 

Run the client, e.g. on a raspberry pi or similar: 

One way to run it, is to start it manually inside a tmux session. Keep in mind, if you choose this method, you have to start it again every time you reboot the client machine. 

Install tmux:
``$ sudo apt install tmux``

Create and enter a new session:
``$ tmux new -s waterSystem``

Run the client inside the session: 
``$ ./02_ClientSide/runSystem.sh``

Leave the session with: 
``ctrl+b +d``

The session will continue to run in the background. Re-attach to check how it's going with: 
``$ tmux attach-session waterSystem``

## Set irrigation schedules

**02_ServerSide/wateringTimes.json** contains the watering schedule and associated watering times (pump ON times). This setup was created using two independent pumps but this number can be increased or reduced to your liking. 

[watering_schedule] is commanded as integer in the format HHMMSS where the zeros in front are cut, e.g.  08:10:10 a.m. -> 81010

[pump_cmd_times] -> number of milliseconds the pump will be activated at their associated watering_schedule slot.   
