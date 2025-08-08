/*!
 * @file  gainHeartbeatSPO2.ino
 * @n experiment phenomena: get the heart rate and blood oxygenation, during the update the data obtained does not change
 * @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
 * @license     The MIT License (MIT)
 * @author      PengKaixing(kaixing.peng@dfrobot.com)
 * @version     V1.0.0
 * @date        2021-06-21
 * @url         https://github.com/DFRobot/DFRobot_BloodOxygen_S
 */
#include "DFRobot_BloodOxygen_S.h"

HardwareSerial mySerial(1);  // Use UART1 (TX=17, RX=16)
DFRobot_BloodOxygen_S_HardWareUart MAX30102(&mySerial, 9600);

void setup()
{
Serial.begin(115200);
  mySerial.begin(9600, SERIAL_8N1, 16, 17);  // RX=16, TX=17
  while (!MAX30102.begin()) {
    Serial.println("Initialization failed!");
    delay(1000);
  }
  Serial.println("init success!");
  Serial.println("start measuring...");
  MAX30102.sensorStartCollect();
}

void loop()
{
  MAX30102.getHeartbeatSPO2();
  Serial.print("SPO2 is : ");
  Serial.print(MAX30102._sHeartbeatSPO2.SPO2);
  Serial.println("%");
  Serial.print("heart rate is : ");
  Serial.print(MAX30102._sHeartbeatSPO2.Heartbeat);
  Serial.println("Times/min");
  Serial.print("Temperature value of the board is : ");
  Serial.print(MAX30102.getTemperature_C());
  Serial.println(" ℃");
  //The sensor updates the data every 4 seconds
  delay(4000);
  //Serial.println("stop measuring...");
  //MAX30102.sensorEndCollect();
}