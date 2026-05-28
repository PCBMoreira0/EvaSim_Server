from contextlib import asynccontextmanager

import docker
from docker.errors import NotFound
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from websocket_manager import WebSocketManager
import websockets
import api
import os

app = FastAPI()

app.include_router(api.router)



docker_client = docker.from_env()

websocket_manager = WebSocketManager()

user_ids : dict[str, str] = {}

counter = 1


async def create_container(name: str, image: str, user_id: str):
    scripts_dir = os.getenv("EVA_SCRIPTS_DIR", "./eva_scripts")
    try:
        container = docker_client.containers.run(
            image,
            detach=True,
            name=name,
            network="orchestrator_evasim_network",
            environment={"USER_ID": user_id},
            volumes={
                scripts_dir: {
                    "bind": "/app/sim/evaml_2025_server/eva_scripts",
                    "mode": "rw"
                }
            })
        
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


@app.post("/init")
async def init():
    global counter
    simulator_id = await create_container("container_simulator_" + str(counter), "evasim/simulator:dev", str(counter))
    if simulator_id is None:
        return {"message": "Failed to create simulation environment", "user_id": counter}
    
    user_ids[str(counter)] = simulator_id
    message = {"message": "simulation environment created", "user_id": counter}
    counter += 1

    return message

@app.delete("/delete/{user_id}")
async def delete(user_id : str):
    socket = websocket_manager.get_websocket(user_id)
    if socket != None:
        await websocket_manager.disconnect(socket)

    container_id = user_ids.get(user_id)
    if container_id is not None:
        try:
            container = docker_client.containers.get(container_id)
            container.remove(force=True)
            return {"message": "simulation environment deleted", "user_id": user_id}
            
        except docker.errors.NotFound:
            raise HTTPException(
                status_code=404,
                detail="Container não encontrado no Docker Engine"
            )
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Erro interno ao remover o container: {str(e)}"
            )

    raise HTTPException(
            status_code=404,
            detail="Container não encontrado"
        )


async def connect_container_ws(user_id):
    MAX_RETRIES = 30
    retries = 0

    while retries < MAX_RETRIES:
        try:
            container_id = user_ids[user_id]

            container = docker_client.containers.get(container_id)

            container.reload()

            if container.status != "running":
                raise RuntimeError(
                    f"Container não está rodando: {container.status}"
                )

            ws = await websockets.connect(
                f"ws://{container.name}:8000/ws/{user_id}",
                open_timeout=5
            )

            print(f"Conectado ao container {user_id}")
            return ws

        except NotFound:
            print(f"Container do usuário {user_id} não existe mais")
            return None

        except RuntimeError as e:
            print(e)
            return None

        except Exception as e:
            print(f"Aguardando websocket do container subir: {e}")

            retries += 1
            await asyncio.sleep(1)

    print("Timeout aguardando websocket")
    return None


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    if user_id not in user_ids:
        await websocket.close()
        return

    container_websocket = await connect_container_ws(user_id)
    
    if container_websocket is None:
        await websocket.close()
        return

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