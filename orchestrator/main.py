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
            network="orchestrator_evasim_network",
            environment={"USER_ID": user_id})
        
        while container.status != 'running':
            container.reload()
            await asyncio.sleep(0.1)

        return container.id
    
    except docker.errors.ImageNotFound:
        print("Error: Image not found. Make sure Docker is running and connected.")
        return None
    except Exception as e:
        print(f"An error occurred: {e}")
        return None


@app.get("/init")
async def init():
    global counter
    counter += 1
    sim_id = await create_container("container_sim_" + str(counter), "evasim/sim:dev", str(counter))
    server_id = await create_container("container_server_" + str(counter), "evasim/server:dev", str(counter))
    if sim_id is None or server_id is None:
        return {"message": "Failed to create simulation environment", "user_id": counter}
    
    container = {"sim": sim_id, "server": server_id}
    user_ids[str(counter)] = container

    return {"message": "simulation environment created", "user_id": counter}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    if user_id not in user_ids:
        await websocket.close()
        return
    
    await websocket_manager.connect(websocket, user_id)    

    container = docker_client.containers.get(user_ids[user_id]["server"])
    # container.reload()
    # container_networks = container.attrs['NetworkSettings']['Networks']
    # container_ip = list(container_networks.values())[0]['IPAddress']
    # print("IP: " + container_ip)

    container_websocket = await websockets.connect(f"ws://{container.name}:8000/ws/{user_id}")

    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            send_task = asyncio.create_task(container_websocket.recv())

            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
        
            for task in pending:
                task.cancel()

            finished_task = done.pop()

            if finished_task == receive_task:
                data = finished_task.result()
                await container_websocket.send(data)

            elif finished_task == send_task:
                data = finished_task.result()
                print("enviando mensagem......")
                await websocket.send_text(data)

    except WebSocketDisconnect:
        await container_websocket.close()
        websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)