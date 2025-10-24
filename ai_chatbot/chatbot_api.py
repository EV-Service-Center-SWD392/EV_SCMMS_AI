"""
EV SCMMS AI Chatbot API
Interactive chat interface with MCP function calling capabilities.
Users can chat naturally and AI will call appropriate MCP functions.
"""
import os
import sys
import json
import asyncio
import uuid
from datetime import datetime
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

from mcp_interface import GeminiMCPChatbot

app = Flask(__name__)
app.config['SECRET_KEY'] = 'ev_scmms_chatbot_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global chatbot instance
chatbot = None

def init_chatbot():
    """Initialize the chatbot instance."""
    global chatbot
    if chatbot is None:
        chatbot = GeminiMCPChatbot()
        chatbot.start_mcp_server()
    return chatbot

@app.route('/health')
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "EV SCMMS AI Chatbot",
        "timestamp": datetime.now().isoformat()
    })

@app.route('/api/ai/chat', methods=['POST'])
def api_chat():
    """
    Main chat endpoint for AI conversation with MCP function calling.
    
    Request:
    {
        "message": "Tôi cần xem inventory của center Hà Nội",
        "conversation_id": "uuid-optional",
        "user_id": "admin123",
        "context": {}
    }
    
    Response:
    {
        "response": "AI response text",
        "function_calls": ["get_inventory"],
        "data": {},
        "conversation_id": "uuid",
        "timestamp": "2024-10-24T10:30:00"
    }
    """
    try:
        data = request.get_json()
        if not data or 'message' not in data:
            return jsonify({
                "error": "Message is required",
                "success": False
            }), 400
        
        # Extract parameters
        message = data['message']
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        user_id = data.get('user_id', 'anonymous')
        context = data.get('context', {})
        
        # Initialize chatbot
        bot = init_chatbot()
        
        # Process chat message with MCP function calling
        result = asyncio.run(bot.process_chat_message(
            message=message,
            conversation_id=conversation_id,
            user_id=user_id,
            context=context
        ))
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            "error": f"Chat processing error: {str(e)}",
            "success": False,
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/api/ai/conversations/<conversation_id>', methods=['GET'])
def get_conversation_history(conversation_id):
    """Get conversation history for a specific conversation ID."""
    try:
        bot = init_chatbot()
        history = bot.get_conversation_history(conversation_id)
        
        return jsonify({
            "conversation_id": conversation_id,
            "history": history,
            "success": True
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Failed to get conversation: {str(e)}",
            "success": False
        }), 500

# WebSocket events for real-time chat
@socketio.on('connect')
def handle_connect():
    """Handle client connection."""
    print(f"🔗 Client connected: {request.sid}")
    emit('status', {'message': 'Connected to EV SCMMS AI Chatbot'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection."""
    print(f"❌ Client disconnected: {request.sid}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle real-time chat messages via WebSocket."""
    try:
        message = data.get('message')
        conversation_id = data.get('conversation_id', str(uuid.uuid4()))
        user_id = data.get('user_id', 'anonymous')
        
        if not message:
            emit('error', {'message': 'Message is required'})
            return
        
        # Process message
        bot = init_chatbot()
        result = asyncio.run(bot.process_chat_message(
            message=message,
            conversation_id=conversation_id,
            user_id=user_id
        ))
        
        # Emit response to client
        emit('chat_response', result)
        
    except Exception as e:
        emit('error', {'message': f'Chat error: {str(e)}'})

if __name__ == '__main__':
    print("🤖 Starting EV SCMMS AI Chatbot...")
    print("🌐 REST API: http://127.0.0.1:8469/api/ai/chat")
    print("🔗 WebSocket: ws://127.0.0.1:8469")
    print("📊 Health: http://127.0.0.1:8469/health")
    
    # Run with SocketIO support
    socketio.run(app, host='0.0.0.0', port=8469, debug=True)