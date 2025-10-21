#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <Adafruit_MLX90614.h>
#include <HX711_ADC.h>
#if defined(ESP8266)|| defined(ESP32) || defined(AVR)
#include <EEPROM.h>
#endif
#include <Wire.h>
#include "DFRobot_BloodOxygen_S.h"
#include "spo2_algorithm.h"

// ============================================
// WIFI CONFIGURATION
// ============================================
const char* ssid = "ata";
const char* password = "atata123";
const char* serverURL = "http://10.48.246.44:3000";

// Status variables
bool wifiConnected = false;
bool hasTask = false;
String currentTaskId = "";

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


void setup() {
  Serial.begin(115200);
  delay(1000);
  
  Serial.println();
  Serial.println("🚀 Starting ESP32 Smart Body Metric...");
  Serial.println("======================================");
  
  setupWiFi();
  bodytemp_setup();
  Serial.println("Done body temperature setup.");
  loadcell_setup();
  Serial.println("Done load cell setup.");
  oximeter_setup();
  Serial.println("Done oximeter setup.");

  Serial.println("✅ Setup complete - Starting main loop");
}

void setupWiFi() {
  Serial.print("📡 Connecting to WiFi: ");
  Serial.println(ssid);
  
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(1000);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    wifiConnected = true;
    Serial.println();
    Serial.println("✅ WiFi Connected!");
    Serial.print("📶 IP Address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println();
    Serial.println("❌ WiFi Failed!");
    wifiConnected = false;
  }
}

void loop() {
  // Maintain WiFi connection
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("❌ WiFi disconnected!");
    wifiConnected = false;
    setupWiFi();
    delay(5000);
    return;
  }
  
  // Only poll if WiFi is connected and no current task
  if (wifiConnected && !hasTask) {
    checkForTasks();
  }
  
  delay(1000); // Poll every 2 seconds
}

void checkForTasks() {
  Serial.println("🔍 Checking for tasks...");
  
  HTTPClient http;
  String url = String(serverURL) + "/api/esp32/poll";
  
  http.begin(url);
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    Serial.print("📥 Received: ");
    Serial.println(payload);
    
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, payload);
    
    if (doc["success"] && doc["task"] != nullptr) {
      // We have a task!
      currentTaskId = doc["task"]["id"].as<String>();
      String sensorType = doc["task"]["sensorType"].as<String>();
      String userName = doc["task"]["userName"].as<String>();
      
      Serial.println();
      Serial.println("🎯 NEW TASK FOUND!");
      Serial.print("   User: ");
      Serial.println(userName);
      Serial.print("   Sensor: ");
      Serial.println(sensorType);
      Serial.print("   Task ID: ");
      Serial.println(currentTaskId);
      
      hasTask = true;
      processTask(sensorType);
    } else {
      Serial.println("💤 No tasks available");
    }
  } else {
    Serial.print("❌ Poll failed: ");
    Serial.println(httpCode);
  }
  
  http.end();
}

void processTask(String sensorType) {
  Serial.print("🔨 Processing task: ");
  Serial.println(sensorType);
  
  // Simulate sensor reading (2-3 seconds)
  Serial.println("⏳ Measuring...");
  delay(2500);
  
  // Generate realistic measurement
  String result = generateMeasurement(sensorType);
  
  Serial.print("📊 Result: ");
  Serial.println(result);
  
  // Send result to server
  sendResult(result);
  
  // Reset task state
  hasTask = false;
  currentTaskId = "";
  
  Serial.println("✅ Task completed!");
  Serial.println();
}

String generateMeasurement(String sensorType) {
  if (sensorType == "spo2") {
    oximeter_read_average();
    return "SpO2: " + String(average_SPO2, 1) + "%, HR: " + String(average_HR) + " bpm";
  } 
  else if (sensorType == "temperature") {
    bodytemp_read_average();
    return String(average_temperature, 1) + "°C";
  } 
  else if (sensorType == "weight") {
    loadcell_read_average();
    return String(average_weight, 1) + " kg";
  }
  
  return "Unknown sensor";
}

void sendResult(String result) {
  Serial.print("📤 Sending result to server... ");
  
  HTTPClient http;
  String url = String(serverURL) + "/api/esp32/result";
  
  http.begin(url);
  http.addHeader("Content-Type", "application/json");
  
  DynamicJsonDocument doc(512);
  doc["taskId"] = currentTaskId;
  doc["result"] = result;
  
  String jsonString;
  serializeJson(doc, jsonString);
  
  int httpCode = http.POST(jsonString);
  
  if (httpCode == 200) {
    Serial.println("✅ Success!");
    String response = http.getString();
    Serial.print("📥 Server: ");
    Serial.println(response);
  } else {
    Serial.print("❌ Failed: ");
    Serial.println(httpCode);
  }
  
  http.end();
}