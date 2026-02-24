import docker
import asyncio
import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from websocket_manager import WebSocketManager
import websockets

app = FastAPI()
docker_client = docker.from_env()

websocket_manager = WebSocketManager()

user_ids : dict[str, str] = {}

counter = 0


async def create_container(name: str, image: str, user_id: str):
    try:
        container = docker_client.containers.run(
            image,
            detach=True,
            name=name,
            auto_remove=True,
            environment={"USER_ID": user_id})
        
        while container.status != 'running':
            container.reload()
            await asyncio.sleep(0.1)

        return container.id
    
    except docker.errors.ImageNotFound:
        print("Error: Image not found. Make sure Docker is running and connected.")
    except Exception as e:
        print(f"An error occurred: {e}")


@app.get("/init")
async def init():
    global counter
    counter += 1
    user_ids[str(counter)] = await create_container("container_sim_" + str(counter), "m1_container", str(counter))
    return {"message": "simulation environment created", "user_id": counter}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    if user_id not in user_ids:
        await websocket.close()
        return
    
    await websocket_manager.connect(websocket, user_id)    

    container = docker_client.containers.get(user_ids[user_id])
    container.reload()
    container_networks = container.attrs['NetworkSettings']['Networks']
    container_ip = list(container_networks.values())[0]['IPAddress']

    container_websocket = await websockets.connect(f"ws://{container_ip}:8000/ws/{user_id}")

    try:
        while True:
            message = await websocket.receive_text()
            print(message)
            await container_websocket.send(message)

    except WebSocketDisconnect:
        await container_websocket.close()
        websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)