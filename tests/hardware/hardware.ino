#include <SoftwareSerial.h>

SoftwareSerial raspi(10, 11); // RX, TX

unsigned long timeStart;
unsigned long heartbeatGap;
int testLength = 180; // minutes
unsigned long heartbeatTimer;
unsigned long lap;
int testRound = 0;
unsigned long timer;
char heartbeatOne = 100;
unsigned long hearbeatMaxInterval = 10000;//ms, i.e. 10sec

bool heartbeatReceived = true;

void setup() {
  // start communication with companion computer
  raspi.begin(57600);

  // start serial monitor
  Serial.begin(57600);

  Serial.println("\n\nStarting test in 3 seconds...");
  for (int i = 2; i > 0; i--){
    delay(1000);
    Serial.print(i);
    Serial.println(" seconds...");
  }
  delay(1000);
}

void loop() {

  // the start of a test run
  timeStart = millis();

  // initialize the heartbeat timer
  heartbeatTimer = millis();
  while (((millis() - timeStart)/60/1000) < (testLength)){
    testRound++;
    lap = millis();
    
    // simulate takeoff and journey to first data station
    Serial.print('\n'); Serial.println(formatMillis(millis()-timeStart));
    Serial.print("Proceding to data station number "); Serial.println(testRound);
    while ((((millis()-lap) < 3*1000)) && heartbeatReceived){
        heartbeatReceived = checkHeartbeat();
        if (!heartbeatReceived)
          endTest(millis() - timeStart, "Heartbeat not received in over one second.");

        if (millis()-timer > 2000){
          timer = millis();
          Serial.print("    Download Status: "); Serial.println(getStatus());
        }
    }
    Serial.print("\nArrived at data station number "); Serial.println(testRound);

    // send data station ID and wait for 5 seconds to aknowloedge
    String strRound = String(testRound);
    for (int i = 0; i < 6; i++){
      if (strRound.charAt(i) != '\x00'){raspi.write(strRound.charAt(i));}
    }
    raspi.write('\n');
    unsigned long downloadTimeStart = millis();

    lap = millis();
    
    while ((((millis()-lap) < 5*1000)) && heartbeatReceived && (getStatus() = "Idle")){
      heartbeatReceived = checkHeartbeat();
      if (!heartbeatReceived)
        endTest(millis() - timeStart, "Heartbeat not received in over one second.");

      if (millis()-timer > 2000){
          timer = millis();
          Serial.print("    Download Status: "); Serial.println(getStatus());
      }
    }

    // expect a downloading hearbeat now
    bool isDownloading = getStatus() == "Active";
    while (isDownloading && heartbeatReceived){
      heartbeatReceived = checkHeartbeat();
      if (!heartbeatReceived)
        endTest(millis() - timeStart, "Heartbeat not received in over one second.");

      if (millis()-timer > 2000){
          timer = millis();
          Serial.print("    Download Status: "); Serial.println(getStatus());
      }
        
      if (heartbeatOne == '\0'){ isDownloading = false; }
    }
    Serial.print("\nDone downloading from data station "); Serial.println(testRound);
    Serial.print("    Download Time: "); Serial.println(formatMillis(millis() - downloadTimeStart));
  }

  endTest(millis() - timeStart, "");

}

bool checkHeartbeat(){
  // check to see if we receved a hearbeat from the companion computer
  if (raspi.available()){
    // reset heartbeat timer
    heartbeatOne = raspi.read();
    heartbeatTimer = millis();
  }

  // check to make sure we are receiveing the heartbeats more than once per second
  heartbeatGap = millis() - heartbeatTimer;
  if (heartbeatGap > hearbeatMaxInterval){
    return false;
  }
  return true;
}

String formatMillis(unsigned long milliseconds){
  int seconds = milliseconds / 1000;
  int minutes = seconds / 60;
  int secRemain = seconds % 60;
  int hours = minutes / 60;
  int minRemain = minutes % 60;
  
  String strSec;
  if (secRemain < 10) {
    strSec = "0" + String(secRemain);
  }
  else{
    strSec = String(secRemain);
  }

  String strMin;
  if (minRemain < 10) {
    strMin = "0" + String(minRemain);
  }
  else{
    strMin = String(secRemain);
  }

  String retVal = "";
  retVal = String(hours) + ":" + strMin + ":" + strSec;
  
  return retVal;
}

void endTest(unsigned long timeEnd, String message){
  Serial.println("\n----------------------------------------");
  Serial.print("Time : "); Serial.println(formatMillis(timeEnd));
  
  if (heartbeatReceived){
    Serial.println("    TEST PASSED");
  }
  else{
    Serial.print("    TEST FAILED: "); Serial.println(message); 
    Serial.print("    Last Hearbeat Gap: "); Serial.println(heartbeatGap);
  }

  while(1){}
}

String getStatus(){
  if (heartbeatOne == '\x00')
    return "Idle";
  else if (heartbeatOne == '\x01')
    return "Active";
  else{
    String failureCause = "Unknown message received: ";
    heartbeatReceived = false;
    failureCause += heartbeatOne;
    endTest(millis() - timeStart, failureCause);
  }
}

