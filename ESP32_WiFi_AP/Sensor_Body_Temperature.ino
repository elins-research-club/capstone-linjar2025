#define NUM_SAMPLES_Temperature 100   // number of samples for moving average_temperature
int readings_temperature[NUM_SAMPLES_Temperature];   // array to store readings_temperature
int index_temperature = 0;               // current index_temperature
long total_temperature = 0;              // running total_temperature

void bodytemp_setup(){
  Serial.println("Body temperature sensor starting...");

  if (!mlx.begin()) {
    Serial.println("Error connecting to MLX sensor. Check wiring.");
  };

  // initialize all readings_temperature to zero
  for (int i = 0; i < NUM_SAMPLES_Temperature; i++) {
    readings_temperature[i] = 0;
  }

  // remove the oldest reading
  total_temperature = 0;

  Serial.print("Emissivity = "); Serial.println(mlx.readEmissivity());
  Serial.println("================================================");
}

void bodytemp_read_one(){
  Serial.print("Object = "); Serial.print(mlx.readObjectTempC()); Serial.println("*C");
  delay(500);
}

void bodytemp_read_average() {
  index_temperature = 0;               // current index_temperature
  total_temperature = 0;              // running total_temperature

  while(1){
    // read new value from sensor
    readings_temperature[index_temperature] = mlx.readObjectTempC();

    // add new reading to total_temperature
    total_temperature += readings_temperature[index_temperature];

    // move to next index_temperature
    index_temperature++;

    // wrap around when reaching the end
    if (index_temperature >= NUM_SAMPLES_Temperature) {index_temperature = 0; break;}

    // calculate moving average_temperature
    average_temperature = (float)total_temperature / NUM_SAMPLES_Temperature;

    // print results
    Serial.print("Raw: ");
    Serial.print(readings_temperature[index_temperature]);
    Serial.print("  Average: ");
    Serial.println(average_temperature);
  }

  delay(10);  // adjust sampling rate as needed
}
