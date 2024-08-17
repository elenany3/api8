from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from fastapi.websockets import WebSocket
import asyncio

app = FastAPI()

# طوابير مستقلة لكل مستخدم
queues = {
    "user1": [],
    "user2": [],
    "user3": [],
    "user4": [],
    "user5": [],
    "user6": [],
    "user7": [],
    "user8": [],
    "user9": [],
    "user10": []
}

clients = []
current_user_index = 0
user_keys = list(queues.keys())  # عشان نسهل الحركة بين المستخدمين

class Item(BaseModel):
    value: Dict[str, Any]


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
)

@app.post("/enqueue/{username}")
async def enqueue(username: str, item: Item):
    if username not in queues:
        raise HTTPException(status_code=404, detail="User not found")
    
    queues[username].append(item.value)
    await notify_clients()
    return {"message": f"Item added to {username}'s queue", "queue_size": len(queues[username])}


@app.get("/dequeue")
async def dequeue():
    global current_user_index

    for _ in range(len(user_keys)):
        username = user_keys[current_user_index]
        if queues[username]:
            item = queues[username].pop(0)
            await notify_clients()
            current_user_index = (current_user_index + 1) % len(user_keys)  # الانتقال للمستخدم التالي
            return {"message": f"Item removed from {username}'s queue", "item": item, "queue_size": len(queues[username])}

        current_user_index = (current_user_index + 1) % len(user_keys)

    raise HTTPException(status_code=404, detail="All queues are empty")


@app.delete("/clear/{username}")
async def clear(username: str):
    if username not in queues:
        raise HTTPException(status_code=404, detail="User not found")

    queues[username] = []
    await notify_clients()
    return {"message": f"{username}'s queue cleared", "queue_size": len(queues[username])}


@app.get("/print")
async def print_queue():
    return {"queues": queues, "total_queue_size": sum(len(queue) for queue in queues.values())}


@app.websocket("/ws/{username}")
async def websocket_endpoint(websocket: WebSocket, username: str):
    if username not in queues:
        await websocket.close(code=4001, reason="Invalid username")
        return

    await websocket.accept()
    clients.append((websocket, username))
    try:
        while True:
            data = await websocket.receive_text()
            if data == "get_queue_size":
                queue_size = len(queues[username])
                await websocket.send_text(f"Queue size for {username}: {queue_size}")
    except Exception as e:
        clients.remove((websocket, username))


async def notify_clients():
    for websocket, username in clients:
        try:
            queue_size = len(queues[username])
            await websocket.send_text(f"Queue size for {username}: {queue_size}")
        except Exception as e:
            clients.remove((websocket, username))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
