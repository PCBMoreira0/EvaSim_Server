import docker
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from mqtt_manager import MQTTManager
from websocket_manager import WebSocketManager

app = FastAPI()

websocket_manager = WebSocketManager()
mqtt_manager = MQTTManager(websocket_manager)

user_ids : dict[str, str] = {}

counter = 0


async def create_container(name: str, imge: str):
    client = docker.from_env()
    try:
        container = client.containers.run(
            "container_m1",
            detach=True,
            name="m1",
            auto_remove=True)
        
        while container.status != 'running':
            container.reload()
            await asyncio.sleep(0.1)

        return container
    
    except docker.errors.ImageNotFound:
        print("Error: Image not found. Make sure Docker is running and connected.")
    except Exception as e:
        print(f"An error occurred: {e}")

def create_mqtt_client(broker_address: str, broker_port: int, websocket: str):
    client = mqtt_manager.create_client(broker_address, broker_port, websocket)
    mqtt_manager.loop_start(client)
    return client

@app.post("/init")
async def init():
    global counter
    counter += 1
    user_ids[str(counter)] = "Sim_" + str(counter)
    create_mqtt_client("localhost", 1883, str(counter))
    return {"message": "Initialization started", "instance_id": counter}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    if user_id not in user_ids:
        await websocket.close()
        return
    
    await websocket_manager.connect(websocket, user_id)    
    websocket_manager.start_queue_loop()
    try:
        while True:
            message = await websocket.receive_text()
            mqtt_manager.publish("EVA/TALK", message, user_id=user_id)
            print(message)

    except WebSocketDisconnect:
        mqtt_manager.loop_stop(user_id)
        websocket_manager.stop_queue_loop()
        websocket_manager.disconnect(websocket)
        del user_ids[user_id]

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)