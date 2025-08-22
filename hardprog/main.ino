#include <Wire.h>

int nilai1 = 10;
int nilai2 = 25;
float nilai3 = 3.14;

void setup() {
    Serial.begin(9600);
}

void loop() {
  // Buat string kosong
    String data = "";

  // Gabungkan dengan delimiter ";"
    data += String(nilai1);
    data += ";";
    data += String(nilai2);
    data += ";";
    data += String(nilai3, 2);  // angka 2 berarti 2 digit di belakang koma

  // Print hasil gabungan
    Serial.println(data);

    delay(1000);
}
