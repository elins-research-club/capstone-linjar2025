#include <WiFi.h>
#include <Adafruit_MLX90614.h>
#include <HX711_ADC.h>
#if defined(ESP8266)|| defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif
#include <Wire.h>
#include "MAX30105.h"
#include "spo2_algorithm.h"


//----------------- OXIMETER -----------------
MAX30105 particleSensor;
#define MAX_BRIGHTNESS 255
int32_t bufferLength; //data length
int32_t spo2; //SPO2 value
int8_t validSPO2; //indicator to show if the SPO2 calculation is valid
int32_t heartRate; //heart rate value
int8_t validHeartRate; //indicator to show if the heart rate calculation is valid
byte pulseLED = 11; //Must be on PWM pin
byte readLED = 13; //Blinks with each data read
//----------------- OXIMETER -----------------


//----------------- LOAD CELL -----------------
const int HX711_dout = 4; //mcu > HX711 dout pin
const int HX711_sck = 5; //mcu > HX711 sck pin
HX711_ADC LoadCell(HX711_dout, HX711_sck);
const int calVal_eepromAdress = 0;
unsigned long t = 0;
//----------------- LOAD CELL -----------------


//----------------- BODY TEMPERATURE -----------------
Adafruit_MLX90614 mlx = Adafruit_MLX90614();
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
  loadcell_setup();
  oximeter_setup();
}

void loop(){
  bodytemp_read();
  loadcell_read();
  oximeter_read();
}
