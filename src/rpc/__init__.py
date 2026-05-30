"""RPC / notification package."""
from src.rpc.base import IRPC, RPCManager
from src.rpc.telegram import TelegramRPC
from src.rpc.websocket import WebSocketRPC, set_shared, get_shared
from src.rpc.ws_pusher import start_data_pusher

__all__ = [
    "IRPC", "RPCManager", "TelegramRPC",
    "WebSocketRPC", "set_shared", "get_shared", "start_data_pusher",
]
