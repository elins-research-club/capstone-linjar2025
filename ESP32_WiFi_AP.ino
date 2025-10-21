#include <WiFi.h>
#include <Adafruit_MLX90614.h>
#include <HX711_ADC.h>
#if defined(ESP8266)|| defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif
#include <Wire.h>
#include "DFRobot_BloodOxygen_S.h"
#include "spo2_algorithm.h"


//----------------- OXIMETER -----------------
DFRobot_BloodOxygen_S_HardWareUart MAX30102(&Serial2, 9600);
float average_HR = 0;           // moving average
float average_SPO2 = 0;           // moving average
//----------------- OXIMETER -----------------


//----------------- LOAD CELL -----------------
const int HX711_dout = 7; //mcu > HX711 dout pin
const int HX711_sck = 5; //mcu > HX711 sck pin
HX711_ADC LoadCell(HX711_dout, HX711_sck);
const int calVal_eepromAdress = 0;
unsigned long t = 0;
float average_weight = 0;           // moving average_weight
//----------------- LOAD CELL -----------------


//----------------- BODY TEMPERATURE -----------------
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
float average_temperature = 0;           // moving average_temperature
//----------------- BODY TEMPERATURE -----------------


//----------------- WiFi -----------------
const char *ssid = "ESP32_AP";
const char *password = "12345678";
//----------------- WiFi -----------------


void setup(){
  Serial.begin(115200);
  WiFi.softAP(ssid, password);
  IPAddress IP = WiFi.softAPIP();
  Serial.print("Access Point IP: ");
  Serial.println(IP);

  bodytemp_setup();
  Serial.println("Done body temperature setup.");
  loadcell_setup();
  Serial.println("Done load cell setup.");
  oximeter_setup();
  Serial.println("Done oximeter setup.");

  Serial.println("Done body temperature setup.");
}

void loop(){

}
