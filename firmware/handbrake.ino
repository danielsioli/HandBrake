/**
 * Firmware Handbrake Sim Racing - Versão Final
 *
 * Recursos:
 * - Nome configurável via boards.txt (Handbrake)
 * - Eixo Brake (compatível com jogos e Windows)
 * - Auto-calibração no boot
 * - EEPROM persistente
 * - Filtro de ruído (média móvel)
 * - Curva exponencial ajustável
 * - Deadzone
 *
 * Comentários técnicos em português (nível profissional)
 */

#include <Joystick.h>
#include <EEPROM.h>
#include <math.h>

// ================= CONFIG =================

#define AXIS_RESOLUTION 4096
#define PIN_HALL_SENSOR A2
#define PIN_BUTTON_0    2
#define PIN_BUTTON_1    3

#define DEADZONE 15
#define FILTER_SAMPLES 8
#define CALIBRATION_TIME 3000  // ms

#define EEPROM_ADDR_MIN 0
#define EEPROM_ADDR_MAX 4

#define CURVE_EXPONENTIAL 1.6f

#define MIN_VALID 200
#define MAX_VALID 900

// =========================================

// Estrutura de calibração
struct CalibrationData {
    int minValue;
    int maxValue;
};

CalibrationData calib;

// Buffer para filtro
int samples[FILTER_SAMPLES];
int sampleIndex = 0;

// ================= JOYSTICK =================

// Configurado como JOYSTICK sem eixo BRAKE
Joystick_ joystick(JOYSTICK_DEFAULT_REPORT_ID, JOYSTICK_TYPE_JOYSTICK,
  0,                    // Button count
  0,                    // Hat Switch Count
  false, false, false,     // X Y Z
  false, false, false,  // Rx Ry Rz
  false, false,         // Rudder Throttle
  false, true, false); // Accelerator Brake Sterring

// ================= FUNÇÕES =================

/**
 * Realiza leitura suavizada usando média móvel.
 */
int smoothAnalogRead(int pin) {
    samples[sampleIndex] = analogRead(pin);
    sampleIndex = (sampleIndex + 1) % FILTER_SAMPLES;

    long sum = 0;
    for (int i = 0; i < FILTER_SAMPLES; i++) {
        sum += samples[i];
    }

    return sum / FILTER_SAMPLES;
}

/**
 * Salva calibração na EEPROM.
 */
void saveCalibration() {
    EEPROM.put(EEPROM_ADDR_MIN, calib.minValue);
    EEPROM.put(EEPROM_ADDR_MAX, calib.maxValue);
}

/**
 * Carrega calibração da EEPROM.
 */
void loadCalibration() {
    EEPROM.get(EEPROM_ADDR_MIN, calib.minValue);
    EEPROM.get(EEPROM_ADDR_MAX, calib.maxValue);

    // validação de segurança
    if (calib.minValue <= 0 || calib.maxValue <= 0 || calib.minValue >= calib.maxValue) {
        calib.minValue = 550;
        calib.maxValue = 500;
    }
}

/**
 * Converte leitura bruta em valor de eixo com curva.
 */
float computeAxis(int rawValue) {

    if (calib.maxValue == calib.minValue) return 0;

    float normalized = (rawValue - calib.minValue) /
                       float(calib.maxValue - calib.minValue);

    // clamp
    if (normalized < 0) normalized = 0;
    if (normalized > 1) normalized = 1;

    // curva exponencial
    float curved = pow(normalized, CURVE_EXPONENTIAL);

    float axis = curved * AXIS_RESOLUTION;

    // deadzone
    if (axis < DEADZONE) axis = 0;

    if (axis > AXIS_RESOLUTION) axis = AXIS_RESOLUTION;

    return axis;
}

/**
 * Calibração automática no boot.
 */
void bootCalibration() {

    unsigned long startTime = millis();

    calib.minValue = 550;
    calib.maxValue = 500;

    while (millis() - startTime < CALIBRATION_TIME) {
        int val = smoothAnalogRead(PIN_HALL_SENSOR);
        if (val > 500 && val < 700) {
            if (val < calib.minValue) calib.minValue = val;
            if (val > calib.maxValue) calib.maxValue = val;
        }
        delay(5);
    }
    saveCalibration();
}

// ================= SETUP =================

void setup() {
    pinMode(PIN_HALL_SENSOR, INPUT);
    // pinMode(PIN_BUTTON_0, INPUT_PULLUP);
    // pinMode(PIN_BUTTON_1, INPUT_PULLUP);

    loadCalibration();

    // Executa calibração ao ligar
    bootCalibration();

    joystick.begin();
    
    joystick.setXAxisRange(0, AXIS_RESOLUTION);
    joystick.setYAxisRange(0, AXIS_RESOLUTION);
    joystick.setZAxisRange(0, AXIS_RESOLUTION);

    joystick.setRxAxisRange(0, AXIS_RESOLUTION);
    joystick.setRyAxisRange(0, AXIS_RESOLUTION);
    joystick.setRzAxisRange(0, AXIS_RESOLUTION);
    
    joystick.setRudderRange(0, AXIS_RESOLUTION);
    joystick.setThrottleRange(0, AXIS_RESOLUTION);

    joystick.setAcceleratorRange(0, AXIS_RESOLUTION);
    joystick.setBrakeRange(0, AXIS_RESOLUTION);
    joystick.setSteeringRange(0, AXIS_RESOLUTION);
}

// ================= LOOP =================

void loop() {

    joystick.setButton(0, digitalRead(PIN_BUTTON_0)==LOW);
    joystick.setButton(1, digitalRead(PIN_BUTTON_1)==LOW);

    int hallValue = smoothAnalogRead(PIN_HALL_SENSOR);

    // ajuste dinâmico leve (anti-drift)
    if (hallValue < calib.minValue) calib.minValue = hallValue;
    if (hallValue > calib.maxValue) calib.maxValue = hallValue;

    float axisValue = computeAxis(hallValue);

    //joystick.setXAxis(axisValue);
    //joystick.setYAxis(axisValue);
    //joystick.setZAxis(axisValue);

    //joystick.setRxAxis(axisValue);
    //joystick.setRyAxis(axisValue);
    joystick.setRzAxis(axisValue);

    //joystick.setRudder(axisValue);
    //joystick.setThrottle(axisValue);

    //joystick.setAccelerator(axisValue);
    joystick.setBrake(axisValue);
    //joystick.setSteering(axisValue);
    //Serial.println(axisValue);
    delay(5);
}
