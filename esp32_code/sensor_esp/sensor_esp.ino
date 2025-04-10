#include <esp_now.h>
#include <esp_wifi.h>
#include "WiFi.h"
#include "Adafruit_Sensor.h"
#include "Adafruit_BME280.h"

#define WIFI_SSID ""

#define ESP_ID 1 // change for esps

#define MAX_TRIES 5
#define TRY_DELAY 1000
#define SEND_DELAY 60000
#define SAMPLES 3

#define R1 { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 } // insert MAC addresses from receiver esp boards here
#define R2 { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }
#define R3 { 0x00, 0x00, 0x00, 0x00, 0x00, 0x00 }

uint8_t broadcastAddress1[] = R1;
uint8_t broadcastAddress2[] = R2;
uint8_t broadcastAddress3[] = R3;
uint8_t mainAddress[6] = {0};

esp_now_peer_info_t peerInfo;
struct Message
{
  int id = ESP_ID;
  float temperature;
  float pressure;
  float humidity;
  float light;
};
Message message;
uint32_t lastSent = 0;
int tries = 0;
bool notSuccessful = false;
bool addressSearch = false;

Adafruit_BME280 bme;
uint32_t prevTime = 0;
uint8_t measureIndex = 0;
struct ReadData
{
  float temperature[3];
  float pressure[3];
  float humidity[3];
  float light[3];
};
ReadData measurements;

void dataSent(const uint8_t* mac_addr, esp_now_send_status_t status)
{
  if (addressSearch)
  {
    if (!mainAddress[0] && status == ESP_NOW_SEND_SUCCESS)
    {
      memcpy(mainAddress, mac_addr, 6);
    }
    return;
  }
  if (status != ESP_NOW_SEND_SUCCESS)
  {
    notSuccessful = true;
    tries++;
  }
  else
  {
    notSuccessful = false;
    tries = 0;
  }
}

void setup()
{
  esp_wifi_set_ps(WIFI_PS_NONE);
  WiFi.mode(WIFI_STA);
  int channel = -1;
  if (int n = WiFi.scanNetworks())
  {
    for (int i = 0; i < n; i++)
    {
      if (!strcmp(WIFI_SSID, WiFi.SSID(i).c_str()))
      {
        channel = WiFi.channel(i);
      }
    }
  }
  if (channel == -1)
  {
    ESP.restart();
  }
  esp_wifi_set_promiscuous(true);
  esp_wifi_set_channel(channel, WIFI_SECOND_CHAN_NONE);
  esp_wifi_set_promiscuous(false);

  bme.begin(0x76);
  bme.setSampling(Adafruit_BME280::MODE_FORCED, Adafruit_BME280::SAMPLING_X1, Adafruit_BME280::SAMPLING_X1, Adafruit_BME280::SAMPLING_X1);

  if (esp_now_init() != ESP_OK)
  {
    return;
  }

  peerInfo.encrypt = false;
  memcpy(peerInfo.peer_addr, broadcastAddress1, 6);
  if (esp_now_add_peer(&peerInfo) != ESP_OK)
  {
    return;
  }
  memcpy(peerInfo.peer_addr, broadcastAddress2, 6);
  if (esp_now_add_peer(&peerInfo) != ESP_OK)
  {
    return;
  }
  memcpy(peerInfo.peer_addr, broadcastAddress3, 6);
  if (esp_now_add_peer(&peerInfo) != ESP_OK)
  {
    return;
  }

  esp_now_register_send_cb(dataSent);
  findMainAddress();
}

void findMainAddress()
{
  memset(mainAddress, 0, 6);
  while (!mainAddress[0])
  {
    Message test;
    test.id = 0;
    test.temperature = 0.0f;
    test.pressure = 0.0f;
    test.humidity = 0.0f;
    test.light = 0.0f;
    addressSearch = true;

    while (esp_now_send(broadcastAddress1, (uint8_t*)&test, sizeof(test)) != ESP_OK)
    {
      delay(100);
    }
    delay(500);
    while (esp_now_send(broadcastAddress2, (uint8_t*)&test, sizeof(test)) != ESP_OK)
    {
      delay(100);
    }
    delay(500);
    while (esp_now_send(broadcastAddress3, (uint8_t*)&test, sizeof(test)) != ESP_OK)
    {
      delay(100);
    }
    delay(500);
  }
  addressSearch = false;
}

void loop()
{
  if (notSuccessful && millis() - lastSent > TRY_DELAY)
  {
    if (tries < MAX_TRIES)
    {
      while (esp_now_send(mainAddress, (uint8_t*)&message, sizeof(message)) != ESP_OK)
      {
        delay(100);
      }
    }
    else
    {
      findMainAddress();
    }
  }
  if (millis() - prevTime > SEND_DELAY / (double)SAMPLES)
  {
    prevTime = millis();
    readData();
  }
  if (measureIndex == SAMPLES)
  {
    sendData();
  }
  delay(100);
}

void readData()
{
  bme.takeForcedMeasurement();
  measurements.temperature[measureIndex] = bme.readTemperature();
  measurements.pressure[measureIndex] = bme.readPressure() / 100.0f;
  measurements.humidity[measureIndex] = bme.readHumidity();
  measurements.light[measureIndex] = analogRead(34) / 40.95f; // read / 4095 * 100 (results in %)
  measureIndex++;
}

void sendData()
{
  message.temperature = average(measurements.temperature);
  message.pressure = average(measurements.pressure);
  message.humidity = average(measurements.humidity);
  message.light = average(measurements.light);
  
  while (esp_now_send(mainAddress, (uint8_t*)&message, sizeof(message)) != ESP_OK)
  {
    delay(100);
  }
  lastSent = millis();
  measureIndex = 0;
}

float average(float* array)
{
  float sum = 0;
  for (int i = 0; i < 3; i++)
  {
    sum += array[i];
  }
  return sum / 3;
}
