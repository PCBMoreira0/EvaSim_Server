from paho.mqtt import client as mqtt_client

client = mqtt_client.Client()
client.connect("0.0.0.0", 1883, 60)

def on_message(client, userdata, message):
    if message.topic.startswith("WEBSOCKET/BROKER"):
        client.publish("BROKER/EVA/" + message.topic[len("WEBSOCKET/BROKER/"):], message.payload)
    elif message.topic.startswith("EVA/BROKER"):
        client.publish("BROKER/WEBSOCKET/" + message.topic[len("EVA/BROKER/"):], message.payload)
    
    print(f"Forwarded message: {message.payload.decode()} on topic {message.topic}")

client.on_message = on_message
client.subscribe("WEBSOCKET/BROKER/#")
client.subscribe("EVA/BROKER/#")

try:
    print("MQTT Broker is running...")
    client.loop_forever()
except KeyboardInterrupt:
    print("\nFinishing...")
    client.disconnect()