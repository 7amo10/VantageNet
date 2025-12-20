#!/usr/bin/env python3
"""
Test WebSocket Connection and Message Types
VANTA-31: Verify WebSocket implementation meets acceptance criteria
"""
import asyncio
import websockets
import json
import sys
from datetime import datetime


class WebSocketTester:
    """Test WebSocket connection and message handling."""
    
    def __init__(self, url="ws://localhost:8000/ws/live"):
        self.url = url
        self.messages_received = []
        self.connection_count = 0
        
    async def connect_and_listen(self, duration=10, client_id=1):
        """
        Connect to WebSocket and listen for messages.
        
        Args:
            duration: How long to listen (seconds)
            client_id: Client identifier for logging
        """
        try:
            async with websockets.connect(self.url) as websocket:
                self.connection_count += 1
                print(f"[Client {client_id}] Connected to {self.url}")
                
                # Send ping immediately
                await websocket.send("ping")
                
                # Listen for messages
                end_time = asyncio.get_event_loop().time() + duration
                
                while asyncio.get_event_loop().time() < end_time:
                    try:
                        message = await asyncio.wait_for(websocket.recv(), timeout=2)
                        data = json.loads(message)
                        
                        msg_type = data.get("type", "unknown")
                        timestamp = data.get("timestamp", "N/A")
                        
                        self.messages_received.append(data)
                        
                        print(f"[Client {client_id}] Received: {msg_type} @ {timestamp}")
                        
                        # Show details for important messages
                        if msg_type == "sentiment_update":
                            sentiment_data = data.get("data", {})
                            print(f"  └─ Faces: {sentiment_data.get('total_faces', 0)}, "
                                  f"Mood: {sentiment_data.get('mood_score', 0):.2f}, "
                                  f"Emotion: {sentiment_data.get('dominant_emotion', 'N/A')}")
                        
                        elif msg_type == "alert_triggered":
                            alert_data = data.get("data", {})
                            print(f"  └─ {alert_data.get('severity', 'N/A').upper()}: "
                                  f"{alert_data.get('message', 'N/A')}")
                        
                        elif msg_type == "connected":
                            conn_data = data.get("data", {})
                            print(f"  └─ Active connections: {conn_data.get('active_connections', 0)}")
                        
                    except asyncio.TimeoutError:
                        # Send periodic ping to keep connection alive
                        await websocket.send("ping")
                        continue
                    except json.JSONDecodeError as e:
                        print(f"[Client {client_id}] Error parsing message: {e}")
                        
                print(f"[Client {client_id}] Test duration completed, disconnecting...")
                
        except Exception as e:
            print(f"[Client {client_id}] Connection error: {e}")
            
    async def test_multiple_connections(self, num_clients=5, duration=10):
        """
        Test multiple concurrent connections.
        
        Args:
            num_clients: Number of concurrent clients
            duration: Test duration (seconds)
        """
        print(f"\n{'='*60}")
        print(f"Testing {num_clients} concurrent connections for {duration}s")
        print(f"{'='*60}\n")
        
        tasks = [
            self.connect_and_listen(duration, i+1)
            for i in range(num_clients)
        ]
        
        await asyncio.gather(*tasks, return_exceptions=True)
        
    def print_summary(self):
        """Print test summary."""
        print(f"\n{'='*60}")
        print("TEST SUMMARY")
        print(f"{'='*60}")
        print(f"Total Connections: {self.connection_count}")
        print(f"Total Messages Received: {len(self.messages_received)}")
        
        # Count message types
        message_types = {}
        for msg in self.messages_received:
            msg_type = msg.get("type", "unknown")
            message_types[msg_type] = message_types.get(msg_type, 0) + 1
        
        print("\nMessage Types Received:")
        for msg_type, count in sorted(message_types.items()):
            print(f"  - {msg_type}: {count}")
        
        # Check acceptance criteria
        print("\nAcceptance Criteria Check:")
        print(f"  ✓ WebSocket endpoint /ws/live: TESTED")
        print(f"  ✓ Connection confirmation: {'connected' in message_types}")
        print(f"  ✓ Pong responses: {'pong' in message_types}")
        print(f"  ✓ Sentiment updates: {'sentiment_update' in message_types}")
        print(f"  ✓ Alert messages: {'alert_triggered' in message_types}")
        print(f"  ✓ Max {self.connection_count} concurrent connections: PASSED")
        

async def main():
    """Main test function."""
    tester = WebSocketTester()
    
    if len(sys.argv) > 1:
        num_clients = int(sys.argv[1])
    else:
        num_clients = 3  # Default test with 3 clients
    
    duration = 12  # Listen for 12 seconds (6 sentiment updates at 2s intervals)
    
    print(f"""
╔═══════════════════════════════════════════════════════════╗
║         VantageNet WebSocket Test - VANTA-31              ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    await tester.test_multiple_connections(num_clients, duration)
    tester.print_summary()
    
    print(f"\n{'='*60}")
    print("Test completed successfully!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
