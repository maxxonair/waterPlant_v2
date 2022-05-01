#include <ESP8266WiFi.h>
#include "PubSubClient.h" 
#include "StringSplitter.h"
//-------------------------------------------------------------------------
/*
 * @brief: WaterPlant plant feeder firmware v0 
 * 
 * @detail:
 * 
 * Pump on time [ms] vs delivered volume [ml]
 * Initial correlation tests:
 *  Power: 5V via USB on separate line
 *  Pump height: ~ 10 cm above the water line 
 * 10000 ms - 125 ml 
 *  5000 ms -  60 ml
 *  2500 ms -  20 ml
 * 
 * For the voltage measurement a connection with a 2kOhm resitor between 
 * the 5V pin and the A0 pin has to be arranged.
 * 
 * Dont forget to change in this code:
 * (1) Wifi credentials 
 * (2) MQTT settings (server IP, user a.o.)
 * 
 * The switch from Remote Controlled mode to survival is currently only 
 * partly implemented. This requires the use of persistent mememory to 
 * be working correctly, which is work TBD. 
 * 
 * @dependencies:
 * - StringSplitter
 * - Pubsubclient
 * 
 */
//-------------------------------------------------------------------------
//    >> Mode settings
//-------------------------------------------------------------------------
/*  Operational Modes: */

// Idle mode for debugging
const int MODE_IDLE            = 0;

// Water control is triggered via MQTT command
const int MODE_REMOTE_CONTROLLED  = 1;

// Survival mode: wifi - off , mqtt off , timer-triggered watering
// This mode is entered after several failed attempts to connect
// to the broker
const int MODE_SURVIVAL        = 2;

/* 
 *  Enable automatic reboot after WIFI_TIMEOUT_MS when wifi connection can't be
 *  established
 *  
 *  Type : Setting
 */ 
boolean isEnableWifiFailureReboot = true;

/*
 * Enable automatic reboot after BROKER_CONNECT_FAILS when mqtt broker connection
 * can't be established
 * 
 * Type : Setting
 * 
 */
boolean isEnableMqttFailureReboot = true;

/* 
 *  Enable entering survival mode when conditios are met
 *  
 *  [!] Note: This will automatically disable isEnableWifiFailureReboot
 *  
 *  Type : Setting
 *  
 *  TODO this needs to be reworked or removed
 */
boolean isEnableEnteringSurvivalMode = false;

/* 
* [!] Set operational mode: 
* 
* Type : Setting
* 
*/
int opsMode = MODE_REMOTE_CONTROLLED;

/* Enable deep sleep between listening periods
 *  [!] for deep sleep to work D0 has to be connected to RESET
 *  
 *  Type : Setting
 *  
 */
boolean isEnableDeepSleep    = true;

/* 
 *  Maximum allowable on time [ms]
 *  
 *  Type : Setting
 *  
 */
int Max_Pump_Interval_ms  = 5000;

/* 
 *  [!] Deep sleep interval [s]
 *  
 *  Type : Setting
 *  
 */
int Deep_Sleep_Interval_s =   900;

/* 
 * [!] Time spent awake [ms] 
 * 
 * Type : Setting
 * 
 */
int Wake_Interval_ms      = 25000;

/* 
 *  Wifi timeout to trigger reset
 *  If Wifi is not connected succesfully after threshold value 
 *  -> trigger reset 
 *  
 *  Type : Setting
 */
const int WIFI_TIMEOUT_MS = 5000;

/*
 * Threshold: Broker connection failures to trigger reboot
 * 
 * Type : Setting
 * 
 */
const int BROKER_CONNECT_FAILS = 5;

/* 
 *  Time spent in deep-sleep interval during survival mode [s]
 *  
 *  Type : Setting
 */
const int SURVIVAL_DEEP_SLEEP_INTERVAL = 12 * 3600 ;

/*
 * Threshold: Connection failures in remote controlled operating mode 
 *            to enter survival mode 
 * 
 * Type :  Setting
 * 
 */
const int FAILURES_TO_ENTER_SURVIVAL = 200;

/*
 * Pump01 opening cycle in survival mode [ms]
 * 
 * Type :  Setting
 * 
 */
const int PUMP_01_CYCLE_SURVIVAL_MS = 1500;

/*
 * Pump02 opening cycle in survival mode [ms]
 * 
 * Type :  Setting
 * 
 */
const int PUMP_02_CYCLE_SURVIVAL_MS = 1500;
//-------------------------------------------------------------------------
//    >> Pins and pump limits
//-------------------------------------------------------------------------
// GPIO pin control pump 1
const int PIN_CTRL_PUMP_01      = 5;
// GPIO pin control pump 2
const int PIN_CTRL_PUMP_02      = 4;
// Photo sensor Pin:
const int PIN_VOLTAGE_SENSOR    = A0;


/*
 * Variable to count connection (wifi & mqtt) failures
 * 
 * Type: Internal
 * 
 */
int connection_failures = 0;

/* 
 *  This is an internal state parameter to keep track if awake from deep 
 *  sleep
 *  
 *  Type: Internal 
 *  
 */
boolean isDeepSleepActive = false; 

/*
 * Variable to count broker connection failures
 */
int broker_connection_failures = 0 ;
//-------------------------------------------------------------------------
//    >> Misc
//-------------------------------------------------------------------------
// Time delay for mode dependent loop step [ms]
int DELAY_IN_MODE_LOOP_MS    = 100;
// Variable to restore command reponse 
int pumpResponse = 0;
// Variable to count time spent awake [ms]
int time_spent_awake_ms      = 0;  
//-------------------------------------------------------------------------
//    >> MQTT Setup
//-------------------------------------------------------------------------
// [!] Wifi credentials
const char* ssid          = "***";
const char* password      = "***";

// Set static IP address
IPAddress local_IP(192, 168, 1, 197); 
// Set Gateway IP address
IPAddress gateway(192, 168, 1, 1);

IPAddress subnet(255, 255, 0, 0);
IPAddress primaryDNS(79, 79, 79, 77);   //optional
IPAddress secondaryDNS(79, 79, 79, 78); //optional

const String thisHostname = "waterPlant";

/* [!] MQTT parameters */
const char* mqtt_server   = "192.168.1.198";
int   mqtt_port           = 1883;
const char* mqtt_user     = "box";
const char* mqtt_password = "box";
const char* clientID      = "client_roomPlant_02";

/* [!] MQTT topics */
// Topic where receive Telecommands
const char* mqtt_topic_TC                = "home/waterPlant/TC";
// Topic where to communicate telemetry 
const char* mqtt_topic_TM                = "home/waterPlant/TM";

// MQTT response messages
// Status message: Awake 
const char* msg_status_awake = "[waterPlant][TM] Awake.";
// Status message: Entering deep sleep phase
const char* msg_status_sleep = "[waterPlant][TM] Enter Deep-Sleep Phase.";
// Status message: Entering survival mode 
const char* msg_status_survival = "[waterPlant][TM] Enter Survival Mode.";
//-------------------------------------------------------------------------
// Constants
//-------------------------------------------------------------------------
String TC_IDENTIFIER = "[TC]";
/* Parameter Identifier */
// Parameter changes
String TC_PARAM_DEEP_SLEEP_INTERVAL   = "PARAM_DEEP_SLEEP_TIME"; 
String TC_PARAM_MAX_PUMP_INTERVAL     = "PARAM_MAX_PUMP_TIME";
String TC_PARAM_AWAKE_INTERVAL        = "PARAM_AWAKE_TIME";
String TC_PARAM_SET_DEEP_SLEEP        = "PARAM_SET_DEEP_SLEEP";
String TC_PARAM_SET_MODE              = "PARAM_SET_MODE";
// Execution commands
String TC_CMD_PUMP01_ON_TIME          = "CMD_PUMP01_ON_TIME";
String TC_CMD_PUMP02_ON_TIME          = "CMD_PUMP02_ON_TIME";
// Status requests
String TC_REQUEST_VOLTAGE             = "REQUEST_VOLTAGE";
String TC_REQUEST_ACKN                = "REQUEST_ACKN";
String TC_REQUEST_SLEEP               = "REQUEST_SLEEP";

// Pump ID's : 
const int PUMP_01 = 1;
const int PUMP_02 = 2;

// Conversion factor nano seconds to seconds (denominator)
int NANOTOSEC = 1000000;
//-------------------------------------------------------------------------
//  Clients
//-------------------------------------------------------------------------
WiFiClient wifiClient;
PubSubClient client(mqtt_server, mqtt_port,wifiClient);
//-------------------------------------------------------------------------
/*
 *  MQTT message callback
 */
void callback(char* topic, byte* message, unsigned int length) {
  
  String messageTemp;
  for (int i = 0; i < length; i++) {
    messageTemp += (char)message[i];
  }
  
  publishData( "[WaterPlant][TM] Message received", mqtt_topic_TM );

  if ( String(topic) == mqtt_topic_TC ) 
  {
      /* Topic: Telecommand */
      parseAndProcessTelecommand(String(messageTemp));
  }
  
}

void setup() 
{
  
  Serial.begin(115200);
  delay(250);
  
  // Set GPIO pump 1
  Serial.print("[SETUP] Pump 01 link GPIO pin: ");
  Serial.println(PIN_CTRL_PUMP_01);
  Serial.print("[SETUP] Pump 02 link GPIO pin: ");
  Serial.println(PIN_CTRL_PUMP_02);
  pinMode(PIN_CTRL_PUMP_01, OUTPUT);
  pinMode(PIN_CTRL_PUMP_02, OUTPUT);
  // Set Pump control pins to HIGH
  digitalWrite(PIN_CTRL_PUMP_01, HIGH); 
  digitalWrite(PIN_CTRL_PUMP_02, HIGH); 
  
  WiFi.mode(WIFI_STA);
  WiFi.hostname(thisHostname.c_str());

  // Configures static IP address
  if (!WiFi.config(local_IP, gateway, subnet, primaryDNS, secondaryDNS)) {
    Serial.println("[WIFI] STA Failed to configure");
  }

  pinMode(PIN_VOLTAGE_SENSOR, INPUT);
  /* Reset time spent awake [ms] */
  time_spent_awake_ms      = 0;

  /* 
   *  Reset connection failures when booting
   * 
   */
  connection_failures = 0;

  /*
   *  Reset broker connection failure counter
   */
  broker_connection_failures = 0 ;

  /* 
   *  Reset deep sleep status flag 
   *  Note: Set to true to trigger publish status in first loop cycle 
   */
  isDeepSleepActive = true;
  
  /* 
   *  Setup Wifi Connection 
   */
  setup_wifi();

  /* Setup MQTT server connection and link callback */
  if ( opsMode == MODE_REMOTE_CONTROLLED ) {
      client.setServer(mqtt_server, 1883);
      client.setCallback(callback);
  }

  if ( isEnableEnteringSurvivalMode ){
    isEnableWifiFailureReboot == false ;
  }

}
//-------------------------------------------------------------------------
void loop() 
{  

if ( opsMode == MODE_IDLE )
{
  // stay idle 
}
else if ( opsMode == MODE_REMOTE_CONTROLLED ) 
{
  
  /* 
   *  If not connected to wifi -> connect
   */
  if ( WiFi.status() != WL_CONNECTED)
  {
      if ( setup_wifi() == 0 ) {
        connection_failures = connection_failures + 1;
      }
  } 
  
  /* 
   *  If not connected to broker -> connect
   */
  if (!client.connected() && WiFi.status() == WL_CONNECTED ) 
  {
    if ( connectMqtt() == 0 ) 
    {
      connection_failures = connection_failures + 1;
      broker_connection_failures = broker_connection_failures + 1;
    }
  } 

  /*
   * If MQTT connection timeout limit reached -> reboot 
   */
   if ( broker_connection_failures > BROKER_CONNECT_FAILS && isEnableMqttFailureReboot)
   {
        Serial.println("[waterPlant] MQTT connection timeout reached. Resetting. ");
        ESP.restart();
   }
  
  /*
   * Check if conditions to enter survival are met
   */
  if ( isEnableEnteringSurvivalMode )
  {
    if ( connection_failures > FAILURES_TO_ENTER_SURVIVAL )
    {
      opsMode = MODE_SURVIVAL;
    }
  }

  /*
   * If connection to wifi and broker successful
   * -> publish wake TM
   */
  if ( client.connected() && WiFi.status() == WL_CONNECTED )
  {
    // Publish status: AWAKE
    if ( isDeepSleepActive == true )
    {
      publishData( msg_status_awake, mqtt_topic_TM );
      time_spent_awake_ms = 0 ;
      isDeepSleepActive = false;
    }
  
  }
  
  /* 
   *  Loop callback
   */
  client.loop();
} 
else if ( opsMode == MODE_SURVIVAL )
{
  Serial.println("[waterPlant][S] Activating pumps.");
  // Activate both pumps and return to sleep
  active_pump_cycle( PUMP_01_CYCLE_SURVIVAL_MS , PUMP_01);
  delay(10);
  active_pump_cycle( PUMP_02_CYCLE_SURVIVAL_MS , PUMP_02);
  delay(500);
  Serial.println("[waterPlant][S] Entering deep sleep.");
  ESP.deepSleep( SURVIVAL_DEEP_SLEEP_INTERVAL * NANOTOSEC); 
}

/* Trigger standard mode loop delay */
delay(DELAY_IN_MODE_LOOP_MS);

if ( isEnableDeepSleep == true && time_spent_awake_ms > Wake_Interval_ms ) 
{  
  /*
   * Enter timer trigger deep sleep phase 
   */
  enterDeepSleepPhase();
}  

/*
 * Update counter: Time spent awake [ms]
 */
time_spent_awake_ms = time_spent_awake_ms + DELAY_IN_MODE_LOOP_MS ;


}
//-------------------------------------------------------------------------
//    >> Service Functions 
//-------------------------------------------------------------------------
/*
 * Function: enter Deep-Sleep phase for Deep_Sleep_Interval_s seconds
 */
void enterDeepSleepPhase(){
    // Enter timer-based deep sleep:
    String message = String(msg_status_sleep) + " Online in " + String(Deep_Sleep_Interval_s) + " seconds." ;
    publishData( message , mqtt_topic_TM );
    client.disconnect(); 
    wifiClient.stop();
    // Timed deep sleep:
    Serial.println("Enter deep sleep.");
    ESP.deepSleep( ( Deep_Sleep_Interval_s * NANOTOSEC) ); 
}
/*
 * Function: Enable pump for on_time_ms [ms]
 */
int active_pump_cycle(int on_time_ms , int pumpID)
{
  if ( pumpID == PUMP_01 ){
    Serial.println("[PUMP01] Set on");
    digitalWrite(PIN_CTRL_PUMP_01, LOW);   
    delay( on_time_ms );                      
    digitalWrite(PIN_CTRL_PUMP_01, HIGH);  
    Serial.println("[PUMP01] Set off"); 
    // Buffer time to ensure time diff between pump cycles
    delay(300);
    return 1;
  } else if ( pumpID == PUMP_02 ) {
    Serial.println("[PUMP02] Set on");
    digitalWrite(PIN_CTRL_PUMP_02, LOW);   
    delay( on_time_ms );                      
    digitalWrite(PIN_CTRL_PUMP_02, HIGH);  
    Serial.println("[PUMP02] Set off"); 
    // Buffer time to ensure time diff between pump cycles
    delay(300);
    return 1;
  } else {
    // Invalid pump ID -> no command executed
    return 0;
  }
}

/*
 * Function: Setup Wifi connection
 */
int  setup_wifi() {
  delay(10);
  // We start by connecting to a WiFi network
  Serial.print("[WIFI] Connecting to ");
  Serial.println(ssid);
  Serial.print("[WIFI] Host name: ");
  Serial.println(thisHostname);
  Serial.print("[WIFI] D1 Mac Address: ");
  Serial.println(WiFi.macAddress());

  WiFi.begin(ssid, password);
  int connectionCounter = 0 ;
  int delayIncrement_ms = 250;
  
  while (WiFi.status() != WL_CONNECTED) {
    connectionCounter = connectionCounter + delayIncrement_ms ;
    if ( connectionCounter > WIFI_TIMEOUT_MS){
      
      if ( isEnableWifiFailureReboot ){
        Serial.println("[waterPlant] Wifi connection timeout reached. Resetting. ");
        ESP.restart();
      } else {
        return 0;
      }
      
    } 
    delay(delayIncrement_ms);
  }

  Serial.print("[WIFI] Connected. IP address: ");
  Serial.println(WiFi.localIP());
  return 1;
}

/* 
 *  Function: Re-connect to MQTT server
 */
int connectMqtt(){
  Serial.println("[MQTT] Connecting to Mqtt broker ... ");
  if (WiFi.status() == WL_CONNECTED) {
      while (!client.connected()) {
      
          if (client.connect(clientID, mqtt_user, mqtt_password)) 
          {
            Serial.println("[MQTT] Connected to MQTT Broker!");
            // Subscribe
            client.subscribe(mqtt_topic_TC);
            
            return 1 ;
          }
          else 
          {
            Serial.println("[MQTT] Connection to MQTT Broker failed!");
            return 0 ;
          }

          delay(1000);
      }
  } else {
    Serial.println("[MQTT] No Wifi connection. Aborting");
    return 0;
  }
}

/*
 * Function: Publish Data (String message) 
 */
void publishData( String data, const char* topic ){
  if (client.publish( topic, data.c_str()) ) {
    Serial.print("Data Package: ");
    Serial.print(data);
    Serial.println(" sent!");
  } else {
    Serial.println("Data package failed to send. Reconnecting to MQTT Broker and trying again");
    client.connect(clientID, mqtt_user, mqtt_password);
    delay(10); // This delay ensures that client.publish doesn't clash with the client.connect call
    client.publish(topic, data.c_str());
  }
}

/* 
* Function: Read power source input voltage 
*/ 
float readInputVoltage(){
  // Get raw analog reading:
  int raw = analogRead(PIN_VOLTAGE_SENSOR);
  // Convert to float voltage level 
  float volt=raw/1023.0;
  return volt * 4.2;
}

/*
 * Function: Parse and process Telecommand 
 */
void parseAndProcessTelecommand(String Telecommand){
  StringSplitter *splitter = new StringSplitter(Telecommand, ';', 3);
  int itemCount = splitter->getItemCount();
  int success_flag      =  0 ;
  String tc_iden        = "" ;
  String parameter_iden = "" ;
  String value_iden     = "" ;

  if ( itemCount != 3 ) {
      /*
       * Add message here 
       */
       publishData( "[WaterPlant][TM] TC parsing failed. Rejecting TC.", mqtt_topic_TM );
  } else {
      /*
       * Parse TC 
       */
      for(int i = 0; i < itemCount; i++){
        if ( i == 0 ){
          tc_iden = splitter->getItemAtIndex(i);
        } else if ( i == 1 ) {
          parameter_iden = splitter->getItemAtIndex(i);
        } else if ( i == 2 ) {
          value_iden = splitter->getItemAtIndex(i);
        }
      }
    
      /*
       * Process TC 
       */
      if ( tc_iden != TC_IDENTIFIER ){
        publishData( "[WaterPlant][TM] Wrong TC identifier. Rejecting TC.", mqtt_topic_TM );
      } else {
        processTelecommand(parameter_iden, value_iden);
      }
  } 
}

/*
 * Function: Process Telecommand -> Set Parameter to Value 
 */
void processTelecommand( String Parameter, String Value ){
  if ( Parameter == TC_PARAM_DEEP_SLEEP_INTERVAL ){
    Deep_Sleep_Interval_s = Value.toInt();
    /* Acknowledge parameter change on TM channel */
    publishParameterChange( Parameter, Value );
  }
  else if ( Parameter == TC_PARAM_MAX_PUMP_INTERVAL )
  {
    Max_Pump_Interval_ms = Value.toInt();
    /* Acknowledge parameter change on TM channel */
    publishParameterChange( Parameter, Value );
  }
  else if ( Parameter == TC_CMD_PUMP01_ON_TIME )
  {
    processPumpCommand( Value,  "Pump_01",  PUMP_01);
  }
  else if ( Parameter == TC_CMD_PUMP02_ON_TIME )
  {
    processPumpCommand( Value,  "Pump_02",  PUMP_02);
  }
  else if ( Parameter == TC_PARAM_SET_DEEP_SLEEP )
  {
    int cmd_setting = Value.toInt();
    if ( cmd_setting == 1){
      isEnableDeepSleep = true;
      /* Acknowledge parameter change on TM channel */
      publishParameterChange( Parameter, Value );
    } else if ( cmd_setting == 0 ){
      isEnableDeepSleep = false;
      /* Acknowledge parameter change on TM channel */
      publishParameterChange( Parameter, Value );
    } else {
      publishData( String("[WaterPlant][TM] Value "+Value+" not valid. Rejecting TC."), mqtt_topic_TM );
    }
  }
  else if ( Parameter == TC_PARAM_AWAKE_INTERVAL )
  {
    Wake_Interval_ms = Value.toInt();
    /* Acknowledge parameter change on TM channel */
    publishParameterChange( Parameter, Value );
  }
  else if ( Parameter == TC_REQUEST_VOLTAGE ) 
  {
      float voltageReading = readInputVoltage(); 
      String strVoltage = "";
      strVoltage.concat(voltageReading);
      publishData( String("[WaterPlant][TM] Battery Voltage: "+strVoltage), mqtt_topic_TM );
  }
  else if ( Parameter == TC_PARAM_SET_MODE )
  {
    int opsModeInt = Value.toInt();
    if ( opsModeInt == MODE_IDLE || opsModeInt == MODE_REMOTE_CONTROLLED || opsModeInt == MODE_SURVIVAL)
    {
      opsMode = opsModeInt;
      publishData( String("[WaterPlant][TM] Setting Operational Mode: "+Value), mqtt_topic_TM );
    } 
    else
    {
      publishData( String("[WaterPlant][TM] Operational Mode not valid. Rejecting Command. "), mqtt_topic_TM );
    }
  }
  else if ( Parameter == TC_REQUEST_SLEEP )
  {
    if ( Value.toInt() == 1 ){
      enterDeepSleepPhase();
    }
  }
  
}

/*
 * Function: Compile and TC acknowledgement message 
 */
void publishParameterChange( String Parameter, String Value ){
  String ack_message = "[WaterPlant][TM] TC valid. Setting "+Parameter+" = "+Value;
  publishData( ack_message, mqtt_topic_TM );
}

/*
 * Function: Process pump activation command
 */
 void processPumpCommand(String Value, String PumpName, int PumpID){
    int on_time_ms = Value.toInt();
    if ( on_time_ms > Max_Pump_Interval_ms ) 
    {
      Serial.println("[WaterPlant][TM][ERR] Error commanded on time above limit. Rejecting command .. ");
      publishData( "[WaterPlant][TM] Command outside limits -> Rejecting command.", mqtt_topic_TM );
    } else 
    {
      publishData( ("[WaterPlant][TM] Activate " + PumpName + " for "+Value+" ms"), mqtt_topic_TM );
      Serial.print("[WaterPlant][TM] " + PumpName + " command > cycle ON: ");
      Serial.print(on_time_ms);
      Serial.println(" ms.");
      pumpResponse = active_pump_cycle(on_time_ms, PumpID);
      if ( pumpResponse == 0 ) {
        publishData( "[WaterPlant][TM][ERR]" + PumpName + " error. Command exited with 0.", mqtt_topic_TM );
      }
    }
 }
