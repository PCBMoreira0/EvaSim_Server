from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mqtt_communicator import MqttCommunicator
from mqtt_json_converter import MqttJsonConverter
import os
import asyncio

app = FastAPI()

# mqtt_communicator = MqttCommunicator(broker_address=os.getenv("MQTT_BROKER_ADDRESS"), port=int(os.getenv("MQTT_BROKER_PORT")))
mqtt_communicator = MqttCommunicator(broker_address="0.0.0.0", port=1883)
mqtt_communicator.connect()

queue = asyncio.Queue()

def on_message(client, userdata, message):
    queue.put_nowait(MqttJsonConverter.mqtt_to_json(message.topic, message.payload.decode()))

mqtt_communicator.set_onmessage(on_message)

@app.websocket("/ws/{user_id}")
async def websocket(websocket: WebSocket, user_id: str):
    # if os.getenv("USER_ID") != user_id:
    #     await websocket.close()
    #     return
    
    await websocket.accept()

    while True:
        try:
            receive_task = asyncio.create_task(websocket.receive_json())
            queue_task = asyncio.create_task(queue.get())

            done, pending = await asyncio.wait(
                [receive_task, queue_task],
                return_when=asyncio.FIRST_COMPLETED
            )
        
            for task in pending:
                task.cancel()

            finished_task = done.pop()

            if finished_task == receive_task:
                data = finished_task.result()
                (topic, payload) = MqttJsonConverter.json_to_mqtt(data)
                mqtt_communicator.publish(topic, payload)

            elif finished_task == queue_task:
                item = finished_task.result()
                await websocket.send_json(item)

        except WebSocketDisconnect:
            for task in pending:
                task.cancel()
            mqtt_communicator.disconnect()
            break
            