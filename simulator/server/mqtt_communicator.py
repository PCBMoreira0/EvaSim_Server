from paho.mqtt import client as mqtt_client

class MqttCommunicator:
    def __init__(self, broker_address : str = None, port : int = None, user_id : str = "default_user"):
        if broker_address is None:
            self.broker_address = "localhost"
        else:
            self.broker_address = broker_address

        if port is None:
            self.port = 1883
        else:
            self.port = port

        self.user_id = user_id
        self.client = mqtt_client.Client()

    def set_onmessage(self, on_message):
        self.client.on_message = on_message

    def connect(self):
        self.client.connect(self.broker_address, self.port)
        self.__subscribe_topics()
        self.client.loop_start()

    def publish(self, topic: str, payload: str):
        self.client.publish("WEBSOCKET/BROKER/" + self.user_id + "/" + topic, payload)

    def __subscribe_topics(self):
        self.client.subscribe("BROKER/WEBSOCKET/" + self.user_id + "/#")

    def disconnect(self):
        self.client.disconnect()