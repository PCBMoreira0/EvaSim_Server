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

counter = 1


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
    simulator_id = await create_container("container_simulator_" + str(counter), "evasim/simulator:dev", str(counter))
    if simulator_id is None:
        return {"message": "Failed to create simulation environment", "user_id": counter}
    
    user_ids[str(counter)] = simulator_id
    message = {"message": "simulation environment created", "user_id": counter}
    counter += 1

    return message

@app.get("/delete/{user_id}")
async def delete(user_id : str):
    socket = websocket_manager.get_websocket(user_id)
    if socket != None:
        await websocket_manager.disconnect(socket)

    container_id = user_ids[user_id]
    if container_id != None:
        container = docker_client.containers.get(container_id)
        container.remove(force=True)
    
        return {"message": "simulation environment deleted", "user_id": user_id}

    return {"message": "simulator does not exist.", "user_id": user_id}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    if user_id not in user_ids:
        await websocket.close()
        return

    container = docker_client.containers.get(user_ids[user_id])

    while True:
        try:
            container_websocket = await websockets.connect(f"ws://{container.name}:8000/ws/{user_id}", open_timeout=5)
            print("Conectado ao container " + user_id)
            break
        except Exception as e:
            print(f"Aguardando websocket do container subir: {e}")
            await asyncio.sleep(1)

    await websocket_manager.connect(websocket, user_id)   

    try:
        while True:
            receive_task = asyncio.create_task(websocket.receive_text())
            send_task = asyncio.create_task(container_websocket.recv())

            done, pending = await asyncio.wait(
                [receive_task, send_task],
                return_when=asyncio.FIRST_COMPLETED
            )
        
            # Cancela a tarefa que ficou aguardando (pending)
            for task in pending:
                task.cancel()

            finished_task = done.pop()

            try:
                data = finished_task.result()
            except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
                print(f"Conexão encerrada para o usuário {user_id}")
                break  

           
            if finished_task == receive_task:
                await container_websocket.send(data)

            elif finished_task == send_task:
                print("enviando mensagem......")
                await websocket.send_text(data)

    finally:
        if not receive_task.done():
            receive_task.cancel()
        if not send_task.done():
            send_task.cancel()

        await container_websocket.close()
        await websocket_manager.disconnect(websocket)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000)