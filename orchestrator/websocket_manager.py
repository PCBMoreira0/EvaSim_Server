from typing import Dict
from fastapi import WebSocket
import asyncio

class WebSocketManager:
    def __init__(self):
        self.active_connections : Dict[str, WebSocket] = {}
        self.queue = asyncio.Queue()
        self.queue_task = None

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket

    def disconnect(self, websocket: WebSocket):
        for client_id, connection in self.active_connections.items():
            if connection == websocket:
                del self.active_connections[client_id]
                break

    def get_websocket(self, user_id: str) -> WebSocket:
        return self.active_connections.get(user_id)
    
    def get_user_ids(self, websocket: WebSocket) -> str:
        for client_id, connection in self.active_connections.items():
            if connection == websocket:
                return client_id
        return None
    
    def send_message(self, message: str, user_id: str):
        websocket = self.get_websocket(user_id)
        if websocket:
            self.queue.put_nowait((websocket, message))

    async def __process_queue(self, queue):
        try:
            while True:
                message = await queue.get()
                websocket, payload = message
                await websocket.send_text(payload)
                queue.task_done()
        except asyncio.CancelledError:
            pass
    
    def start_queue_loop(self):
        if not self.queue_task:
            self.queue_task = asyncio.create_task(self.__process_queue(self.queue))

    def stop_queue_loop(self):
        if self.queue_task:
            self.queue_task.cancel()

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_text(message)