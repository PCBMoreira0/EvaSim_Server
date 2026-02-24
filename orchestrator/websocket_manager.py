from typing import Dict
from fastapi import WebSocket
import asyncio

class WebSocketManager:
    def __init__(self):
        self.active_connections : Dict[str, WebSocket] = {}
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
    
    async def send_message(self, message: str, user_id: str):
        websocket = self.get_websocket(user_id)
        if websocket:
            await websocket.send_json(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections.values():
            await connection.send_json(message)