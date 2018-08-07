#include <SoftwareSerial.h>

SoftwareSerial raspi(10, 11); // RX, TX

// Timers
unsigned long timeStart;
unsigned long heartbeatGap;
unsigned long heartbeatTimer;
unsigned long logTimer;
unsigned long lap;
unsigned long hearbeatMaxInterval = 10000;//ms, i.e. 10sec

// Test Parameters
int testLength = 180; // minutes
int testRound = 0;
char heartbeatOne = 100;
bool heartbeatReceived = true;

String dataStationID[6] = {"redwood", "redwood", "streetcat", "falcon"};

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

  // begin test
  while (testIsActive()){
    testRound++;
    lap = millis();

    // simulate takeoff and journey to first data station
    Serial.print('\n'); Serial.println(formatMillis(millis()-timeStart));
    Serial.print("Proceding to data station number "); Serial.println(testRound);
    while ((((millis()-lap) < 3*1000)) && heartbeatReceived){
        checkHeartbeat();
        logDownloadStatus();
    }
    Serial.print("Round "); Serial.println(testRound);
    Serial.print("\nArrived at data station "); Serial.println(dataStationID[testRound]);

    // send data station ID
    String strID = dataStationID[testRound%6];
    for (int i = 0; i < strID.length(); i++){
      raspi.write(strID.charAt(i));
    }
    raspi.write('\n');

    // wait for 5 seconds for payload to aknowloedge
    unsigned long downloadTimeStart = millis();
    lap = millis();
    while ((((millis()-lap) < 5*1000)) && heartbeatReceived && (getStatus() = "Idle")){
      checkHeartbeat();
      logDownloadStatus();
    }

    // expect a downloading hearbeat now
    bool isDownloading = getStatus() == "Active";
    while (isDownloading && heartbeatReceived){
      checkHeartbeat();
      logDownloadStatus();
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
  if (heartbeatGap > hearbeatMaxInterval)
    heartbeatReceived = false;
  else
    heartbeatReceived = true;

  // end test if hearbeat was not received in time
  if (!heartbeatReceived)
    endTest(millis() - timeStart, "Heartbeat not received in over one second.");

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

bool testIsActive(){
  return ((millis() - timeStart)/60/1000) < (testLength);
}

void logDownloadStatus(){
  if (millis()-logTimer > 2000){
    logTimer = millis();
    Serial.print("    Download Status: "); Serial.println(getStatus());
  }
}
