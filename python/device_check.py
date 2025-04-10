import paho.mqtt.client as mqtt

MQTT_USERNAME = ""
MQTT_PASSWORD = ""
RPI_IP_ADDRESS = ""

class MQTTCheck:
    """Helper class which checks if all ESP devices are still active.
    """
    def __init__(self) -> None:
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self._connect
        self.client.on_message = self._message
        self.client.connect(RPI_IP_ADDRESS, 1883)
        self.devices = dict([(f"esp{i}", 0) for i in range(1, 9)])
        print("Waiting until all devices have sent at least 1 message:\n")
        self._printTable()

    def start(self):
        self.client.loop_forever()

    def clearLines(self, n: int = 0):
        LINE_UP = "\033[1A"
        LINE_CLEAR = "\x1b[2K"
        for _ in range(n):
            print(LINE_UP, end=LINE_CLEAR)

    def rgbText(self, r: int, g: int, b: int, text: str) -> str:
        return f"\x1b[38;2;{r};{g};{b}m{text}\x1b[0m"

    def _connect(self, client, userdata, flags, rcode) -> None:
        for i in range(1, 9):
            self.client.subscribe((f"esp{i}", 0))

    def _printTable(self):
        string = ""
        for dev in self.devices:
            check = self.rgbText(0, 255, 0, "\u2714") if self.devices[dev] else "..."
            string += f"{dev+':':<8} {check}\n"
        print(string[:-1])
        
    def _message(self, client, userdata, message) -> None:
        if message.topic in self.devices:
            if "q" not in message.topic and self.devices[message.topic] > 1:
                print("All active devices have now sent at least one messages. If a device is active, it should have sent a message by now!")
                exit()
            self.devices[message.topic] += 1
        self.clearLines(10)
        self._printTable()

class MQTTDump:
    """Helper/debug class which dumps all sent MQTT messages.
    """
    def __init__(self) -> None:
        self.client = mqtt.Client()
        self.client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
        self.client.on_connect = self._connect
        self.client.on_message = self._message
        self.client.connect(RPI_IP_ADDRESS, 1883)

    def start(self):
        self.client.loop_forever()

    def _connect(self, client, userdata, flags, rcode) -> None:
        self.client.subscribe(("esp", 0))
        for i in range(1, 9):
            self.client.subscribe((f"esp{i}", 0))

    def _message(self, client, userdata, message) -> None:
        print(f"{message.topic}: {message.payload}")

if __name__ == "__main__":
    # mqtt = MQTTCheck()
    mqtt = MQTTDump()
    mqtt.start()
