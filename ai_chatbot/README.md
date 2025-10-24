# EV SCMMS AI Chatbot

## 🤖 Overview
Interactive AI chatbot for EV Service Center Maintenance Management System with **MCP function calling** capabilities. Users can chat naturally and AI will automatically call appropriate functions to retrieve data.

## 🏗️ Architecture

### Core Components
- **`chatbot_api.py`** - Flask API with WebSocket support for real-time chat
- **`mcp_interface.py`** - Gemini function calling client with conversation management
- **Shared Resources** - Uses MCP server and DB connection from `../shared/`

### Technology Stack
- **AI Model**: Google Gemini 2.0 Flash Experimental
- **Real-time**: WebSocket support with Flask-SocketIO
- **Protocol**: Model Context Protocol (MCP) for secure data access
- **Database**: PostgreSQL (Supabase) via shared connection
- **Language**: Python 3.13

## 💬 Chat Capabilities

### Natural Language Commands
Users can chat naturally in Vietnamese:

- **"Tôi cần xem inventory của center Hà Nội"** → `get_inventory(center_id)`
- **"Brake pad nào sắp hết hàng?"** → `get_spare_parts()` + `get_inventory()`
- **"Cho tôi xem lịch sử sử dụng 6 tháng qua"** → `get_usage_history(months=6)`
- **"Dự báo nhu cầu 3 tháng tới"** → `forecast_demand(months=3)` (integrated engine)
- **"Tìm phụ tùng tên 'oil filter'"** → `get_spare_parts(part_name="oil filter")`

### Available MCP Functions
1. **`get_spare_parts`** - Tìm kiếm thông tin phụ tùng
2. **`get_inventory`** - Xem tình trạng tồn kho  
3. **`get_usage_history`** - Xem lịch sử sử dụng
4. **`forecast_demand`** - Dự báo nhu cầu (integrated forecast engine)

## 🚀 API Endpoints

### REST API

#### POST `/api/ai/chat`
**Request:**
```json
{
  "message": "Tôi cần xem inventory của center Hà Nội",
  "conversation_id": "uuid-optional",
  "user_id": "admin123",
  "context": {}
}
```

**Response:**
```json
{
  "success": true,
  "response": "Đây là thông tin inventory của center Hà Nội...",
  "function_calls": ["get_inventory"],
  "function_results": [{"function": "get_inventory", "result": {...}}],
  "conversation_id": "uuid",
  "timestamp": "2024-10-24T10:30:00",
  "function_call_count": 1
}
```

#### GET `/api/ai/conversations/<conversation_id>`
Get conversation history for a specific conversation.

#### GET `/health`
Health check endpoint.

### WebSocket API

#### Real-time Chat
```javascript
// Connect
const socket = io('ws://127.0.0.1:8469');

// Send message
socket.emit('chat_message', {
  message: "Tôi cần xem inventory",
  conversation_id: "uuid",
  user_id: "admin123"
});

// Receive response
socket.on('chat_response', (data) => {
  console.log(data.response);
  console.log(data.function_calls);
});
```

## 🧠 Conversation Management

### Features
- **Conversation History** - Maintains context across messages
- **Context Awareness** - Uses previous messages for better understanding
- **Function Call Logging** - Tracks all MCP function calls per conversation
- **Error Handling** - Graceful error responses with context preservation

### Context Example
```
User: "Tôi cần xem inventory"
AI: *calls get_inventory()* "Đây là thông tin inventory hiện tại..."

User: "Center nào có brake pad nhiều nhất?"
AI: *uses previous inventory data* "Dựa trên dữ liệu vừa lấy, center XYZ có brake pad nhiều nhất..."
```

## 🔧 Function Calling Flow

```
1. User sends message → "Tôi cần xem inventory center HN"
2. Gemini analyzes → Determines need for get_inventory function
3. AI calls get_inventory(center_id="hanoi") → MCP server → Database
4. AI receives data → Analyzes and formats response
5. AI responds → "Center Hà Nội hiện có 45 phụ tùng trong kho..."
6. Conversation saved → Ready for follow-up questions
```

## 🏃‍♂️ Running the Chatbot

### Prerequisites
```bash
cd ai_chatbot
pip install -r requirements.txt
```

### Start Chatbot Service
```bash
python chatbot_api.py
# REST API: http://127.0.0.1:8469/api/ai/chat
# WebSocket: ws://127.0.0.1:8469
# Health: http://127.0.0.1:8469/health
```

### Test Chat
```bash
curl -X POST http://127.0.0.1:8469/api/ai/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Tôi cần xem inventory"}'
```

## 🔄 Integration with Frontend

### Web Chat Interface
```javascript
// REST API example
fetch('/api/ai/chat', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    message: userInput,
    conversation_id: currentConversationId,
    user_id: currentUserId
  })
})
.then(response => response.json())
.then(data => {
  displayMessage(data.response);
  showFunctionCalls(data.function_calls);
});
```

### Mobile App Integration
- RESTful API compatible with any mobile framework
- Real-time WebSocket support for instant responses
- Structured JSON responses for easy parsing

## 🎯 Business Use Cases

### Support Staff
- **"Có phụ tùng nào sắp hết không?"** → Urgent inventory alerts
- **"Center nào có oil filter?"** → Multi-center inventory search
- **"Dự báo brake pad 3 tháng"** → Demand forecasting

### Managers  
- **"Báo cáo tình hình tồn kho"** → Comprehensive inventory report
- **"Phân tích xu hướng sử dụng"** → Usage trend analysis
- **"Đề xuất đặt hàng"** → Purchase recommendations

### Technicians
- **"Tìm phụ tùng cho xe VinFast VF8"** → Vehicle-specific parts
- **"Lịch sử thay brake pad"** → Maintenance history
- **"Có phụ tùng thay thế không?"** → Alternative parts search

## 🔐 Security & Performance

### Security Features
- MCP protocol security (no raw data in prompts)
- Conversation isolation per user
- Input validation and sanitization
- Function call authorization

### Performance
- Shared MCP server (multiple services)
- Connection pooling for database
- Async processing for scalability
- WebSocket for real-time responsiveness

---

## ✨ Key Features

🤖 **Natural Language Processing** - Chat in Vietnamese, AI understands intent
🔧 **Automatic Function Calling** - AI decides which MCP functions to call
💬 **Conversation Memory** - Maintains context across messages  
⚡ **Real-time Chat** - WebSocket support for instant responses
📊 **Structured Data** - Function results with business insights
🔗 **Integrated Forecasting** - Built-in forecast engine with database persistence

**Status: ✅ READY FOR INTEGRATION**