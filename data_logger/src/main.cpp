#include <Arduino.h>


#define SENS_HORIZONTAL B10000000

unsigned long sampleRate = 0;

int AnalogRead(short channel) {
  // Sets AREF voltage to 5V.
  ADMUX |=  (1 << REFS0);
  // Enables ADC and sets prescaler to 128.
  ADCSRA |= (1 << ADEN) | (1 << ADPS2) | (1 << ADPS1)  | (1 << ADPS0);
  ADCSRB = 0x00;
  // Sets ADC channel.
  channel &= 0b00000111;
  ADMUX = (ADMUX & 0xF8) | channel;

  // Starts conversion.
  ADCSRA |= (1 << ADSC);

  // Waits until conversion finishes.
  while(ADCSRA & (1 << ADSC));

  // Returns measured value.
  return ADC;
}

void setup() {
  Serial.begin(1000000);

  // Configure pins.
  PORTC |= SENS_HORIZONTAL;

  // Wait for the PC to send start message.
  char serialBuffer[20];
  while (!Serial.available());

  // Read start message.
  for (int i = 0; Serial.available() && i < 20; i++) {
    serialBuffer[i] = Serial.read();
    delay(1);
  }

  // Get sample rate.
  sampleRate = strtol(serialBuffer, NULL, 10);
}

void loop() {
  unsigned long startTime = micros();

  // Read values of horizontal and vertical sensor.
  int valY = AnalogRead(1);
  int valX = AnalogRead(0);

  // Message buffer.
  char message[20];

  // Add measured value to message.
  sprintf(message, "%d,%d\n", valX, valY);

  // Send message via serial port.
  Serial.print(message);

  delay(1);
}
