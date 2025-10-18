const uint8_t N_SAMPLES = 15;
const uint8_t TRIM = 2; // drop 2 lowest & 2 highest
float amb[N_SAMPLES];
float obj[N_SAMPLES];

void bodytemp_setup(){
  Serial.println("Body temperature sensor starting...");

  if (!mlx.begin()) {
    Serial.println("Error connecting to MLX sensor. Check wiring.");
    while (1);
  };

  Serial.print("Emissivity = "); Serial.println(mlx.readEmissivity());
  Serial.println("================================================");
}

void bodytemp_read(){
  Serial.print("Ambient = "); Serial.print(mlx.readAmbientTempC());
  Serial.print("*C\tObject = "); Serial.print(mlx.readObjectTempC()); Serial.println("*C");
  Serial.print("Ambient = "); Serial.print(mlx.readAmbientTempF());
  Serial.print("*F\tObject = "); Serial.print(mlx.readObjectTempF()); Serial.println("*F");

  Serial.println();
  delay(500);
}

void bodytemp_read_average(){
  for (uint8_t i = 0; i < N_SAMPLES; i++) {
    amb[i] = mlx.readAmbientTempC();
    obj[i] = mlx.readObjectTempC();
    delay(10); // ~150ms total, keeps it responsive
  }

  // simple insertion sort (N small)
  auto sortAsc = [](float *arr, uint8_t n){
    for (uint8_t i = 1; i < n; i++) {
      float key = arr[i];
      int j = i - 1;
      while (j >= 0 && arr[j] > key) { arr[j+1] = arr[j]; j--; }
      arr[j+1] = key;
    }
  };

  sortAsc(amb, N_SAMPLES);
  sortAsc(obj, N_SAMPLES);

  uint8_t start = TRIM;
  uint8_t end   = N_SAMPLES - TRIM;
  float ambSum = 0, objSum = 0;
  for (uint8_t i = start; i < end; i++) {
    ambSum += amb[i];
    objSum += obj[i];
  }
  float ambC = ambSum / float(end - start);
  float objC = objSum / float(end - start);

  // print once, in C and F
  Serial.print("Ambient = "); Serial.print(ambC);
  Serial.print("*C\tObject = "); Serial.print(objC); Serial.println("*C");

  float ambF = ambC * 9.0 / 5.0 + 32.0;
  float objF = objC * 9.0 / 5.0 + 32.0;
  Serial.print("Ambient = "); Serial.print(ambF);
  Serial.print("*F\tObject = "); Serial.print(objF); Serial.println("*F");

  Serial.println();
  // no extra delay() here; sampling already took ~150ms
}