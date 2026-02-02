from paho.mqtt import client as mqtt_client
from fastapi import WebSocket
from websocket_manager import WebSocketManager

class MQTTManager:
    def __init__(self, websocketmanager: WebSocketManager):
        self.clients : dict[mqtt_client.Client, str] = {}
        self.websocket_manager = websocketmanager
        
    def create_client(self, broker_address: str, broker_port: int, user_id : str):
        client = mqtt_client.Client()
        client.connect(broker_address, broker_port)
        client.on_message = self.__message_received
        client.subscribe([("EVA/TALK", 0), ("EVA/LISTEN", 0), ("EVA/TALK_RESPONSE", 0), ("EVA/LISTEN_RESPONSE", 0), ("EVA/AUDIO", 0), ("EVA/AUDIO_RESPONSE", 0), ("EVA/EMOTION", 0)])
        self.clients[client] = user_id
        return client

    def __message_received(self, client, userdata, msg):
        user_id = self.clients[client]
        self.websocket_manager.send_message(msg.payload.decode(), user_id)

    def publish(self, topic: str, payload: str, user_id : str):
        client = self.get_client(user_id)
        if client:
            client.publish(topic, payload) 

    def loop_start(self, client: mqtt_client.Client):
        client.loop_start()

    def get_client(self, user_id : str):
        for client, id in self.clients.items():
            if id == user_id:
                return client
        return None
    
    def loop_stop(self, user_id : str):
        client = self.get_client(user_id)
        if client:
            client.loop_stop()
        del self.clients[client]