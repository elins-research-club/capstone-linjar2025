#define NUM_SAMPLES_HR 100   // number of samples for moving average_HR
int readings_HR[NUM_SAMPLES_HR];   // array to store readings_HR
int index_HR = 0;               // current index_HR
long total_HR = 0;              // running total_HR

#define NUM_SAMPLES_SPO2 100   // number of samples for moving average_SPO2
int readings_SPO2[NUM_SAMPLES_SPO2];   // array to store readings_SPO2
int index_SPO2 = 0;               // current index_SPO2
long total_SPO2 = 0;              // running total_SPO2

void oximeter_setup(){
  if(false == MAX30102.begin()){
    Serial.println("init fail!");
    delay(1000);
  }
  Serial.println("init success!");
  Serial.println("start measuring...");
  MAX30102.sensorStartCollect();
}

void oximeter_read_one()
{
  MAX30102.getHeartbeatSPO2();
  Serial.print("SPO2 is : ");
  Serial.print(MAX30102._sHeartbeatSPO2.SPO2);
  Serial.println("%");
  Serial.print("heart rate is : ");
  Serial.print(MAX30102._sHeartbeatSPO2.Heartbeat);
  Serial.println("Times/min");
  delay(4000);
}

void oximeter_read_average() {
  index_SPO2 = 0;               // current index_SPO2
  total_SPO2 = 0;              // running total_SPO2

  while(1){
    // read new value from sensor
    readings_HR[index_HR] = MAX30102._sHeartbeatSPO2.Heartbeat;
    readings_SPO2[index_SPO2] = MAX30102._sHeartbeatSPO2.SPO2;

    // add new reading to total_HR
    total_HR += readings_HR[index_HR];
    total_SPO2 += readings_SPO2[index_SPO2];

    // move to next index_HR
    index_HR++;
    index_SPO2++;

    // wrap around when reaching the end
    if (index_HR >= NUM_SAMPLES_HR) {index_HR = 0; break;}
    if (index_SPO2 >= NUM_SAMPLES_SPO2) {index_SPO2 = 0;}

    // calculate moving average_HR
    average_HR = (float)total_HR / NUM_SAMPLES_HR;
    average_SPO2 = (float)total_SPO2 / NUM_SAMPLES_SPO2;

    // print results
    Serial.print("Raw: ");
    Serial.print(readings_HR[index_HR]);
    Serial.print("  Average: ");
    Serial.println(average_HR);
    Serial.print("Raw: ");
    Serial.print(readings_SPO2[index_SPO2]);
    Serial.print("  Average: ");
    Serial.println(average_SPO2);

    delay(10);  // adjust sampling rate as needed
  }
}