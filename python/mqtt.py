import paho.mqtt.client as mqtt
from sql import SQLDatabase, ESP_DEVICES
from datetime import datetime
import math
import logging

MQTT_USERNAME = ""
MQTT_PASSWORD = ""
RPI_IP_ADDRESS = ""
        
class MQTTServer:
    def __init__(self) -> None:
        logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

        self.database = SQLDatabase(mode="rwc")
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self._connect
        self.client.on_message = self._message
        self.client.connect(RPI_IP_ADDRESS, 1883)
        self.lastValues = {
            "t": [20 for _ in range(len(ESP_DEVICES))],
            "p": [960 for _ in range(len(ESP_DEVICES))],
            "h": [50 for _ in range(len(ESP_DEVICES))],
            "l": [5 for _ in range(len(ESP_DEVICES))],
        }

    def start(self):
        self.client.loop_forever()

    def _connect(self, client, userdata, flags, rcode) -> None:
        self.client.subscribe(("esp", 0))
        logging.info(f"Connected to mqtt server with result code {rcode}")
        
    def _message(self, client, userdata, message) -> None:
        try:
            message = message.payload.decode('utf-8')
            receiver, sender = message.split(",")[:2]
            dev = f"esp{sender}"
        except Exception as e:
            logging.error(f"Message was not decoded correctly. Original message: {message.payload}")
            logging.error(f"The following python error was produced: {e}")
        
        devId = ESP_DEVICES.index(dev)
        values = [float(data[2:]) for data in message.split(",")[2:]]
        for i, typ in enumerate(["t", "p", "h", "l"]):
            if math.isnan(values[i]):
                logging.warning(f"Values: {values} contained nan. Inserting from last values: {self.lastValues[typ][devId]}. Full message: {message}")
                values[i] = self.lastValues[typ][devId]
        date = str(datetime.now()).split(".")[0]

        try:
            self.database.insertData(dev, date, *values)
        except Exception as e:
            logging.error(f"SQL.insertData threw an error. Device: {dev}, date: {date}, values: {values}.")
            logging.error(f"The following python error was produced: {e}")
            return
        self.lastValues["t"][devId], self.lastValues["p"][devId], self.lastValues["h"][devId], self.lastValues["l"][devId] = values

if __name__ == "__main__":
    mqtt = MQTTServer()
    mqtt.start()
