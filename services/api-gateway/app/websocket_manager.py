"""WebSocket connection manager for real-time updates."""
import logging
import json
from datetime import datetime
from typing import List, Dict, Any
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections and broadcasting."""
    
    MAX_CONNECTIONS = 100  # VANTA-31: Maximum concurrent connections
    
    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: List[WebSocket] = []
        self._connection_count = 0
        
    async def connect(self, websocket: WebSocket) -> bool:
        """
        Accept and register new WebSocket connection.
        
        Args:
            websocket: WebSocket connection to register
            
        Returns:
            True if connected, False if max connections reached
        """
        # VANTA-31: Enforce max connections limit
        if len(self.active_connections) >= self.MAX_CONNECTIONS:
            logger.warning(
                f"WebSocket connection rejected | "
                f"Max connections reached: {self.MAX_CONNECTIONS}"
            )
            await websocket.close(code=1008, reason="Max connections reached")
            return False
            
        await websocket.accept()
        self.active_connections.append(websocket)
        self._connection_count += 1
        
        logger.info(
            f"WebSocket connected | Active: {len(self.active_connections)} | "
            f"Total: {self._connection_count}"
        )
        
        # Send welcome message
        await self._send_to_connection(
            websocket,
            {
                "type": "connected",
                "data": {
                    "message": "Connected to VantageNet API Gateway",
                    "active_connections": len(self.active_connections),
                    "max_connections": self.MAX_CONNECTIONS
                },
                "timestamp": datetime.now().isoformat()
            }
        )
        
        return True
    
    def disconnect(self, websocket: WebSocket) -> None:
        """
        Remove WebSocket connection.
        
        Args:
            websocket: WebSocket connection to remove
        """
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(
                f"WebSocket disconnected | Active: {len(self.active_connections)}"
            )
    
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """
        Broadcast message to all connected clients.
        
        Args:
            message: Message dictionary to broadcast
        """
        if not self.active_connections:
            return
        
        # Add timestamp if not present
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        dead_connections = []
        
        for connection in self.active_connections:
            try:
                await self._send_to_connection(connection, message)
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                dead_connections.append(connection)
        
        # Remove dead connections
        for connection in dead_connections:
            self.disconnect(connection)
    
    async def _send_to_connection(
        self,
        websocket: WebSocket,
        message: Dict[str, Any]
    ) -> None:
        """
        Send message to specific connection.
        
        Args:
            websocket: Target WebSocket connection
            message: Message to send
        """
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            raise
    
    async def send_sentiment_update(self, sentiment_data: Dict[str, Any]) -> None:
        """
        Broadcast sentiment update to all clients.
        
        Args:
            sentiment_data: Sentiment data to broadcast
        """
        message = {
            "type": "sentiment_update",
            "data": sentiment_data
        }
        await self.broadcast(message)
    
    async def send_emotion_event(self, emotion_data: Dict[str, Any]) -> None:
        """
        Broadcast emotion event to all clients.
        
        Args:
            emotion_data: Emotion data to broadcast
        """
        message = {
            "type": "emotion_event",
            "data": emotion_data
        }
        await self.broadcast(message)
    
    async def send_alert(self, alert_data: Dict[str, Any]) -> None:
        """
        Broadcast alert to all clients.
        
        Args:
            alert_data: Alert data to broadcast
        """
        message = {
            "type": "alert_triggered",  # VANTA-31: Use alert_triggered type
            "data": alert_data
        }
        await self.broadcast(message)
        logger.warning(f"Alert broadcasted: {alert_data.get('message', 'N/A')}")
    
    async def send_rule_evaluation(self, rule_data: Dict[str, Any]) -> None:
        """
        Broadcast rule evaluation result to all clients (for debugging).
        
        Args:
            rule_data: Rule evaluation data to broadcast
        """
        message = {
            "type": "rule_evaluation",
            "data": rule_data
        }
        await self.broadcast(message)
    
    async def send_camera_status(self, camera_data: Dict[str, Any]) -> None:
        """
        Broadcast camera status change to all clients.
        
        Args:
            camera_data: Camera status data to broadcast
        """
        message = {
            "type": "camera_status",
            "data": camera_data
        }
        await self.broadcast(message)
        logger.info(f"Camera status broadcasted: {camera_data.get('camera_id', 'N/A')}")
    
    def get_stats(self) -> Dict[str, int]:
        """
        Get connection statistics.
        
        Returns:
            Dict with active and total connection counts
        """
        return {
            "active_connections": len(self.active_connections),
            "total_connections": self._connection_count,
            "max_connections": self.MAX_CONNECTIONS
        }


# Global connection manager instance
manager = ConnectionManager()
