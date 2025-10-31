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
import re
import requests
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
from ai_chatbot.mcp_interface import GeminiMCPChatbot
# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://localhost:5020')
DEFAULT_TECHNICIAN_COUNT = int(os.getenv('DEFAULT_TECHNICIAN_COUNT', '5'))



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

def is_schedule_request(message):
    """Kiểm tra xem tin nhắn có phải yêu cầu đặt lịch không"""
    keywords = ["tự động đặt lịch", "đặt lịch làm", "đặt lịch", "auto schedule", "schedule", "lịch làm"]
    return any(keyword in message.lower() for keyword in keywords)

def extract_date_range(message):
    """Trích xuất khoảng thời gian từ tin nhắn"""
    if "từ giờ" in message and "tuần sau" in message:
        today = datetime.now().date()
        next_week = today + timedelta(days=7)
        return (datetime.combine(today, datetime.min.time()), 
               datetime.combine(next_week, datetime.min.time()))
    
    date_pattern = r'từ ngày\s+(\d{4}-\d{2}-\d{2})\s+tới ngày\s+(\d{4}-\d{2}-\d{2})'
    match = re.search(date_pattern, message)
    if match:
        start_str, end_str = match.groups()
        return (datetime.strptime(start_str, "%Y-%m-%d"), datetime.strptime(end_str, "%Y-%m-%d"))
    
    return None

def extract_shifts(message):
    """Trích xuất ca làm việc từ tin nhắn"""
    if "cả 2 ca" in message or "cả hai ca" in message or "2 ca" in message:
        return ["Morning", "Evening"]
    elif "ca sáng" in message or "sáng" in message:
        return ["Morning"]
    elif "ca chiều" in message or "chiều" in message:
        return ["Evening"]
    elif "ca tối" in message or "tối" in message:
        return ["Night"]
    return ["Morning"]

def extract_center_name(message):
    """Trích xuất tên center từ tin nhắn"""
    pattern = r'ở\s+(.+?)(?:\s*$|\s*,)'
    match = re.search(pattern, message)
    if match:
        return match.group(1).strip()
    return "EV Service - Thủ Đức"  # Default center

async def find_center_from_database(center_name):
    """Tìm center trực tiếp từ database"""
    try:
        from db_connection import fetch
        
        if not center_name:
            center_name = "EV Service - Thủ Đức"
        
        # Tìm chính xác trước
        sql = "SELECT centerid, name FROM centertuantm WHERE name ILIKE %s AND isactive = true LIMIT 1"
        rows = await fetch(sql, center_name)
        
        if rows:
            print(f"✅ Found exact match in DB: '{rows[0]['name']}' - ID: {rows[0]['centerid']}")
            return rows[0]['centerid']
        
        # Tìm fuzzy match
        sql = "SELECT centerid, name FROM centertuantm WHERE name ILIKE %s AND isactive = true LIMIT 5"
        rows = await fetch(sql, f"%{center_name}%")
        
        if rows:
            print(f"✅ Found fuzzy match in DB: '{rows[0]['name']}' - ID: {rows[0]['centerid']}")
            return rows[0]['centerid']
        
        # Tìm theo từ khóa
        keywords = center_name.lower().replace('-', ' ').split()
        for keyword in keywords:
            if len(keyword) > 2:  # Chỉ tìm từ khóa dài hơn 2 ký tự
                sql = "SELECT centerid, name FROM centertuantm WHERE name ILIKE %s AND isactive = true LIMIT 1"
                rows = await fetch(sql, f"%{keyword}%")
                if rows:
                    print(f"✅ Found keyword match in DB: '{rows[0]['name']}' - ID: {rows[0]['centerid']}")
                    return rows[0]['centerid']
        
        # Fallback: lấy center đầu tiên
        sql = "SELECT centerid, name FROM centertuantm WHERE isactive = true LIMIT 1"
        rows = await fetch(sql)
        if rows:
            print(f"⚠️ Using fallback center: '{rows[0]['name']}' - ID: {rows[0]['centerid']}")
            return rows[0]['centerid']
        
        return None
    except Exception as e:
        print(f"❌ Database center search error: {e}")
        return None

def find_center_by_name(center_name):
    """Tìm center ID từ tên center với logic tìm kiếm thông minh"""
    if not center_name:
        center_name = "EV Service - Thủ Đức"
    
    url = f"{API_BASE_URL}/api/Center"
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.get(url, headers=headers)
        print(f"🔍 API Response Status: {response.status_code}")
        
        if response.status_code == 200:
            centers = response.json()
            print(f"🔍 Found {len(centers)} centers")
            
            # Debug: In ra tất cả center names
            for center in centers:
                center_id = center.get('centerId') or center.get('id')
                print(f"🏢 Center: '{center.get('name', 'No name')}' - ID: {center_id}")
            
            # Chuẩn hóa tên để tìm kiếm
            search_name = center_name.lower().strip()
            
            # 1. Tìm chính xác trước
            for center in centers:
                center_db_name = center.get('name', '').lower().strip()
                if search_name == center_db_name:
                    center_id = center.get('centerId') or center.get('id')
                    print(f"✅ Exact match found: {center_id}")
                    return center_id
            
            # 2. Tìm theo từ khóa chính (loại bỏ dấu, khoảng trắng)
            search_keywords = search_name.replace('-', ' ').replace('_', ' ').split()
            print(f"🔍 Search keywords: {search_keywords}")
            
            best_match = None
            best_score = 0
            
            for center in centers:
                center_db_name = center.get('name', '').lower().strip()
                center_keywords = center_db_name.replace('-', ' ').replace('_', ' ').split()
                
                # Tính điểm khớp
                score = 0
                for keyword in search_keywords:
                    if keyword in center_keywords:
                        score += 1
                    elif any(keyword in ck for ck in center_keywords):
                        score += 0.5
                
                print(f"🔍 '{center_db_name}' score: {score}/{len(search_keywords)}")
                
                if score > best_score:
                    best_score = score
                    best_match = center
            
            # 3. Nếu có match tốt (ít nhất 50% từ khóa khớp)
            if best_match and best_score >= len(search_keywords) * 0.5:
                center_id = best_match.get('centerId') or best_match.get('id')
                print(f"✅ Best match found: '{best_match.get('name')}' - ID: {center_id} (score: {best_score})")
                return center_id
            
            # 4. Tìm kiếm mờ (substring)
            for center in centers:
                center_db_name = center.get('name', '').lower()
                if (search_name in center_db_name or 
                    center_db_name in search_name or
                    any(keyword in center_db_name for keyword in search_keywords)):
                    center_id = center.get('centerId') or center.get('id')
                    print(f"✅ Fuzzy match found: '{center.get('name')}' - ID: {center_id}")
                    return center_id
            
            # 5. Nếu không tìm thấy, trả về center đầu tiên (fallback)
            if centers:
                center_id = centers[0].get('centerId') or centers[0].get('id')
                print(f"⚠️ No match found, using first center: '{centers[0].get('name')}' - ID: {center_id}")
                return center_id
                
        else:
            print(f"❌ API call failed with status: {response.status_code}")
            print(f"📝 Response: {response.text}")
            
        return None
    except Exception as e:
        print(f"❌ Error calling API: {e}")
        return None

def call_auto_assign_api(center_id, shift, work_date, required_count=None):
    """Gọi API auto-assign"""
    if required_count is None:
        required_count = DEFAULT_TECHNICIAN_COUNT
        
    url = f"{API_BASE_URL}/api/UserWorkSchedule/auto-assign"
    headers = {'Content-Type': 'application/json'}
    
    payload = {
        "centerId": center_id,
        "shift": shift,
        "workDate": work_date.isoformat(),
        "requiredTechnicianCount": required_count,
        "requiredSkills": None
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        return {"success": response.status_code == 200, "data": response.json() if response.status_code == 200 else None}
    except:
        return {"success": False, "error": "API call failed"}

def process_schedule_request(message, center_id):
    """Xử lý yêu cầu đặt lịch"""
    date_range = extract_date_range(message)
    shifts = extract_shifts(message)
    
    if not date_range:
        return {"success": False, "message": "Không thể xác định khoảng thời gian"}
    
    results = []
    start_date, end_date = date_range
    current_date = start_date
    
    while current_date <= end_date:
        for shift in shifts:
            result = call_auto_assign_api(center_id, shift, current_date)
            results.append({"date": current_date.strftime("%Y-%m-%d"), "shift": shift, "result": result})
        current_date += timedelta(days=1)
    
    successful = [r for r in results if r["result"]["success"]]
    failed = [r for r in results if not r["result"]["success"]]
    
    shift_names = {"Morning": "Ca sáng", "Evening": "Ca chiều", "Night": "Ca tối"}
    
    message_parts = []
    if successful:
        message_parts.append(f"✅ Đã đặt lịch thành công cho {len(successful)} ca:")
        for s in successful[:5]:
            message_parts.append(f"  - {s['date']} ({shift_names.get(s['shift'], s['shift'])})")
    
    if failed:
        message_parts.append(f"❌ Không thể đặt lịch cho {len(failed)} ca")
    
    return {
        "success": len(successful) > 0,
        "message": "\n".join(message_parts),
        "details": {"successful": len(successful), "failed": len(failed)}
    }

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
        center_id = context.get('centerId')
        
        # Check if this is a schedule request
        if is_schedule_request(message):
            # Try to extract center name from message if center_id not provided
            if not center_id:
                center_name = extract_center_name(message)  # Sẽ trả về default nếu không tìm thấy
                
                # Try database first, then API fallback
                try:
                    center_id = asyncio.run(find_center_from_database(center_name))
                except:
                    center_id = find_center_by_name(center_name)
                
                if not center_id:
                    return jsonify({
                        "response": f"Không tìm thấy trung tâm '{center_name}' trong hệ thống.",
                        "success": False,
                        "conversation_id": conversation_id,
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Process schedule request
            schedule_result = process_schedule_request(message, center_id)
            return jsonify({
                "response": schedule_result["message"],
                "success": schedule_result["success"],
                "function_calls": ["auto_assign_schedule"],
                "data": schedule_result.get("details", {}),
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            })
        
        # Initialize chatbot for other requests
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
        
        center_id = data.get('center_id')
        
        # Check if this is a schedule request
        if is_schedule_request(message):
            if not center_id:
                center_name = extract_center_name(message)
                if center_name:
                    center_id = find_center_by_name(center_name)
                
                if not center_id:
                    emit('error', {'message': 'Không thể xác định trung tâm dịch vụ'})
                    return
            
            schedule_result = process_schedule_request(message, center_id)
            emit('chat_response', {
                "response": schedule_result["message"],
                "success": schedule_result["success"],
                "function_calls": ["auto_assign_schedule"],
                "data": schedule_result.get("details", {}),
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            })
            return
        
        # Process message with MCP
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