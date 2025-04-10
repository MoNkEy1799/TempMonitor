#include <esp_now.h>
#include <WiFi.h>
#include "PubSubClient.h"

#define WIFI_SSID "" //enter wifi credentials
#define WIFI_PW ""
WiFiClient wifiClient;
bool restart = true;

#define MQTT_IP "" // set mqtt credentials
#define MQTT_USER ""
#define MQTT_PW ""
#define MQTT_CLIENT "esp_x" // change for esps
#define MQTT_TOPIC "esp"
PubSubClient client(MQTT_IP, 1883, wifiClient);

struct Message
{
  int id;
  float temperature;
  float pressure;
  float humidity;
  float light;
};
Message message;

void dataReceive(const esp_now_recv_info_t* info, const uint8_t* data, int len)
{
  memcpy(&message, data, sizeof(message));
  if (message.id == 0)
  {
    return;
  }
  connectWiFiMQTT();
  char msg[100];
  snprintf(msg, 100, "%c,%d,t:%f,p:%f,h:%f,l:%f", MQTT_CLIENT[11], message.id, message.temperature, message.pressure, message.humidity, message.light);
  client.publish(MQTT_TOPIC, msg);
}

void setup()
{
  WiFi.mode(WIFI_AP_STA);
  client.setKeepAlive(300);
  connectWiFiMQTT();

  if (esp_now_init() != ESP_OK) {
    return;
  }
  esp_now_register_recv_cb(dataReceive);
}

void connectWiFiMQTT()
{
  if (WiFi.status() != WL_CONNECTED)
  {
    WiFi.disconnect();
    WiFi.begin(WIFI_SSID, WIFI_PW);
    uint32_t time = millis();
    while (WiFi.status() != WL_CONNECTED)
    {
      if (millis() - time > 5000 && !restart)
      {
        ESP.restart();
      }
      delay(100);
    }
  }
  restart = false;

  if (!client.connected())
  {
    uint32_t time = millis();
    while (!client.connect(MQTT_CLIENT, MQTT_USER, MQTT_PW))
    {
      if (millis() - time > 5000)
      {
        ESP.restart();
      }
      delay(100);
    }
  }
}
 
void loop()
{
}
