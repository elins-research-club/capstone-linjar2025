#include "bodyheight.h"
#include "Arduino.h"

// Sensor yang digunakan active low
float readAnemo(int pinHall){
    float analog = analogRead(pinAS5600);
    float sudut = map(analog, 0, 4096, 0, 360); // perhitungan buat ke tinggi badan satuan cm

    return sudut;
}
