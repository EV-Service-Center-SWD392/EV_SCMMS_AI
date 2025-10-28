"""
MCP Interface for EV SCMMS AI Chatbot
Handles Gemini function calling for conversational AI interactions.
"""
import os
import json
import asyncio
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment from shared config
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'shared', 'config.env'))

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class ConversationManager:
    """Manages conversation history and context."""
    
    def __init__(self):
        self.conversations: Dict[str, List[Dict]] = {}
    
    def add_message(self, conversation_id: str, role: str, content: str, function_calls: List = None):
        """Add a message to conversation history."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = []
        
        message = {
            "timestamp": datetime.now().isoformat(),
            "role": role,
            "content": content,
            "function_calls": function_calls or []
        }
        
        self.conversations[conversation_id].append(message)
    
    def get_conversation(self, conversation_id: str) -> List[Dict]:
        """Get conversation history."""
        return self.conversations.get(conversation_id, [])
    
    def get_context_summary(self, conversation_id: str) -> str:
        """Get minimal context to reduce tokens."""
        history = self.get_conversation(conversation_id)
        if not history or len(history) == 0:
            return ""
        
        # Only get last user message for minimal context
        last_msg = history[-1]
        if last_msg["role"] == "user":
            return f"Last: {last_msg['content'][:50]}"
        
        return ""

class GeminiMCPChatbot:
    """Gemini-powered chatbot with MCP function calling for EV SCMMS."""
    
    def __init__(self):
        # Function declarations for MCP tools
        self.function_declarations = [
            genai.protos.FunctionDeclaration(
                name="get_spare_parts",
                description=(
                    "Tìm kiếm phụ tùng xe điện theo tên, nhà sản xuất, hoặc loại phụ tùng. "
                    "Tự động tìm kiếm đa trường với độ chính xác cao. "
                    "Kết quả bao gồm: tên, loại phụ tùng, giá hiện tại, số lượng tồn kho, và các thông tin liên quan khác. "
                    "Sử dụng hàm này khi người dùng hỏi về thông tin, tình trạng, hoặc giá của phụ tùng."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "part_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Từ khóa tìm kiếm (tên, nhà sản xuất, hoặc loại phụ tùng)"
                        )
                    }
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_inventory",
                description=(
                    "Xem tình trạng tồn kho hiện tại của các trung tâm bảo dưỡng. "
                    "Dùng khi người dùng muốn biết số lượng phụ tùng có sẵn."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "center_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="ID trung tâm cụ thể (tùy chọn)"
                        )
                    }
                )
            ),
            genai.protos.FunctionDeclaration(
                name="get_usage_history",
                description=(
                    "Lấy lịch sử sử dụng phụ tùng để phân tích xu hướng và dự báo nhu cầu. "
                    "Có thể lọc theo tên phụ tùng, ID phụ tùng và trung tâm, trong khoảng 1-24 tháng."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "months": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Số tháng lịch sử cần xem (1-24)"
                        ),
                        "part_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Tên phụ tùng để tìm kiếm (tùy chọn)"
                        ),
                        "spare_part_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="ID phụ tùng cụ thể (tùy chọn)"
                        ),
                        "center_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="ID trung tâm cụ thể (tùy chọn)"
                        )
                    }
                )
            ),
            genai.protos.FunctionDeclaration(
                name="forecast_demand",
                description=(
                    "Dự báo nhu cầu phụ tùng trong tương lai (1-12 tháng) bằng AI. "
                    "Có thể dự báo cho từng phụ tùng theo tên hoặc ID và từng trung tâm."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "months": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="Số tháng cần dự báo (1-12)"
                        ),
                        "part_name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Tên phụ tùng để dự báo (tùy chọn)"
                        ),
                        "spare_part_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="ID phụ tùng cụ thể (tùy chọn)"
                        ),
                        "center_id": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="ID trung tâm cụ thể (tùy chọn)"
                        )
                    }
                )
            ),
            genai.protos.FunctionDeclaration(
                name="create_sparepart",
                description=(
                    "Hỗ trợ tạo phụ tùng mới. Phân tích thông tin người dùng cung cấp và trả về "
                    "danh sách các trường cần thiết để tạo phụ tùng. AI không tự động tạo vào database."
                ),
                parameters=genai.protos.Schema(
                    type=genai.protos.Type.OBJECT,
                    properties={
                        "name": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Tên phụ tùng (tùy chọn)"
                        ),
                        "unitPrice": genai.protos.Schema(
                            type=genai.protos.Type.NUMBER,
                            description="Giá đơn vị (tùy chọn)"
                        ),
                        "manufacturer": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Nhà sản xuất (tùy chọn)"
                        ),
                        "typeName": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Loại phụ tùng (tùy chọn)"
                        ),
                        "vehicleModelId": genai.protos.Schema(
                            type=genai.protos.Type.INTEGER,
                            description="ID mẫu xe (tùy chọn)"
                        ),
                        "centerName": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Tên trung tâm (tùy chọn)"
                        ),
                        "description": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Mô tả phụ tùng (tùy chọn)"
                        ),
                        "partNumber": genai.protos.Schema(
                            type=genai.protos.Type.STRING,
                            description="Mã phụ tùng (tùy chọn)"
                        )
                    }
                )
            )
        ]
        
        # Gemini model with function calling
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            tools=[genai.protos.Tool(function_declarations=self.function_declarations)],
            tool_config=genai.protos.ToolConfig(
                function_calling_config=genai.protos.FunctionCallingConfig(
                    mode=genai.protos.FunctionCallingConfig.Mode.AUTO
                )
            ),
            system_instruction="AI trợ lý phụ tùng xe điện EV Service Center. Khi người dùng hỏi về phụ tùng→gọi get_spare_parts MỘT LẦN, tồn kho→get_inventory, lịch sử→get_usage_history, dự báo→forecast_demand. Chỉ gọi function 1 lần cho mỗi yêu cầu. Khi dự báo phụ tùng cụ thể, hãy đề cập tên phụ tùng và kết quả dự báo chi tiết.",
            generation_config={
                "temperature": 0.3,
                "top_p": 0.8,
                "max_output_tokens": 512  # Reduce output tokens
            }
        )
        
        # Fallback model without function calling
        self.fallback_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash",
            system_instruction="AI trợ lý thân thiện cho hệ thống quản lý phụ tùng xe điện EV Service Center. Trả lời các câu hỏi chung về xe điện, bảo dưỡng, và hỗ trợ khách hàng.",
            generation_config={
                "temperature": 0.7,
                "top_p": 0.9,
                "max_output_tokens": 512
            }
        )
        
        # Conversation manager
        self.conversation_manager = ConversationManager()
        
        # MCP server process
        self.mcp_process = None
    
    def start_mcp_server(self):
        """Start the shared MCP server."""
        if self.mcp_process is None:
            print("🚀 Starting shared MCP server...")
            shared_dir = os.path.join(os.path.dirname(__file__), '..', 'shared')
            self.mcp_process = subprocess.Popen(
                ["python", "true_mcp_server.py"],
                cwd=shared_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            import time
            time.sleep(2)
            print("✅ Shared MCP server started")
    
    def stop_mcp_server(self):
        """Stop the MCP server."""
        if self.mcp_process:
            self.mcp_process.terminate()
            self.mcp_process.wait()
            self.mcp_process = None
            print("🔒 MCP server stopped")
    
    async def call_mcp_function(self, function_name: str, arguments: dict):
        """Call MCP server function."""
        # Import shared database functions
        import sys
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
        from db_connection import fetch
        
        if function_name == "get_spare_parts":
            part_name = arguments.get("part_name")
            
            # Filter out None values and "None" strings
            if part_name in [None, "None", ""]:
                part_name = None
            
            sql = """
            SELECT s.sparepartid, s.name, s.unitprice, s.manufacture, s.status,
                   i.centerid, i.quantity, i.minimumstocklevel, 
                   t.name as type_name, v.name as vehicle_model_name
            FROM sparepart_tuht s
            LEFT JOIN inventory_tuht i ON s.inventoryid = i.inventoryid
            LEFT JOIN spareparttype_tuht t ON s.typeid = t.typeid
            LEFT JOIN vehiclemodel v ON s.vehiclemodelid = v.modelid
            WHERE s.isactive = true
            """
            params = []
            
            if part_name:
                # Multi-field search: name, manufacture, type
                sql += " AND (s.name ILIKE %s OR s.manufacture ILIKE %s OR t.name ILIKE %s)"
                search_term = f"%{part_name}%"
                params.extend([search_term, search_term, search_term])
                sql += " ORDER BY CASE WHEN s.name ILIKE %s THEN 1 WHEN s.manufacture ILIKE %s THEN 2 ELSE 3 END, s.name"
                params.extend([search_term, search_term])
            else:
                sql += " ORDER BY s.name"
            
            sql += " LIMIT 20"
            rows = await fetch(sql, *params) if params else await fetch(sql)
            # Return comprehensive data from real Supabase database
            result_data = []
            for row in rows[:15]:  # Show up to 15 items
                result_data.append({
                    "id": row.get("sparepartid", ""),
                    "name": row.get("name", ""),
                    "price": row.get("unitprice", 0),
                    "manufacture": row.get("manufacture", ""),
                    "qty": row.get("quantity", 0),
                    "min_stock": row.get("minimumstocklevel", 0),
                    "center_id": row.get("centerid", ""),
                    "status": row.get("status", ""),
                    "type": row.get("type_name", ""),
                    "vehicle_model": row.get("vehicle_model_name", "")
                })
            return {"data": result_data, "count": len(result_data), "source": "supabase_real_data"}
        
        elif function_name == "get_inventory":
            center_id = arguments.get("center_id")
            
            # Filter out None values
            if center_id in [None, "None", ""]:
                center_id = None
            
            sql = """
            SELECT i.inventoryid, i.centerid, i.quantity, i.minimumstocklevel, i.status,
                   s.sparepartid, s.name as spare_part_name, s.unitprice, s.manufacture
            FROM inventory_tuht i
            LEFT JOIN sparepart_tuht s ON i.inventoryid = s.inventoryid
            WHERE i.isactive = true
            """
            params = []
            
            if center_id:
                sql += " AND i.centerid = %s"
                params.append(center_id)
            
            sql += " LIMIT 10"
            rows = await fetch(sql, *params) if params else await fetch(sql)
            # Real inventory data from Supabase
            inventory_data = []
            for row in rows[:8]:
                inventory_data.append({
                    "inventory_id": row.get("inventoryid", ""),
                    "center_id": row.get("centerid", ""),
                    "spare_part_id": row.get("sparepartid", ""),
                    "part_name": row.get("spare_part_name", ""),
                    "quantity": row.get("quantity", 0),
                    "min_stock": row.get("minimumstocklevel", 0),
                    "price": row.get("unitprice", 0),
                    "manufacture": row.get("manufacture", ""),
                    "status": row.get("status", "")
                })
            return {"data": inventory_data, "count": len(inventory_data), "source": "supabase_real_data"}
        
        elif function_name == "get_usage_history":
            months = arguments.get("months", 6)
            part_name = arguments.get("part_name")
            spare_part_id = arguments.get("spare_part_id")
            center_id = arguments.get("center_id")
            
            # Filter out None values
            if part_name in [None, "None", ""]:
                part_name = None
            if spare_part_id in [None, "None", ""]:
                spare_part_id = None
            if center_id in [None, "None", ""]:
                center_id = None
            
            months = max(1, min(24, months))
            
            sql = """
            SELECT h.usageid, h.sparepartid, h.centerid, h.quantityused, h.useddate, h.status,
                   s.name as spare_part_name, s.unitprice, c.name as center_name
            FROM sparepartusagehistory_tuht h
            LEFT JOIN sparepart_tuht s ON h.sparepartid = s.sparepartid
            LEFT JOIN centertuantm c ON h.centerid = c.centerid
            WHERE h.useddate >= (now() - (%s::int * interval '1 month')) AND h.isactive = true
            """
            params = [months]
            
            if part_name:
                sql += " AND s.name ILIKE %s"
                params.append(f"%{part_name}%")
            if spare_part_id:
                sql += " AND h.sparepartid = %s"
                params.append(spare_part_id)
            if center_id:
                sql += " AND h.centerid = %s"
                params.append(center_id)
                
            sql += " ORDER BY h.useddate DESC LIMIT 15"
            rows = await fetch(sql, *params)
            # Real usage history from Supabase
            usage_data = []
            for row in rows[:10]:
                usage_data.append({
                    "usage_id": row.get("usageid", ""),
                    "date": str(row.get("useddate", "")),
                    "spare_part_id": row.get("sparepartid", ""),
                    "part_name": row.get("spare_part_name", ""),
                    "center_id": row.get("centerid", ""),
                    "center_name": row.get("center_name", ""),
                    "quantity_used": row.get("quantityused", 0),
                    "price": row.get("unitprice", 0),
                    "status": row.get("status", "")
                })
            return {"data": usage_data, "count": len(usage_data), "months": months, "source": "supabase_real_data"}
        
        elif function_name == "forecast_demand":
            months = arguments.get("months", 6)
            part_name = arguments.get("part_name")
            spare_part_id = arguments.get("spare_part_id")
            center_id = arguments.get("center_id")
            
            # Filter out None values
            if part_name in [None, "None", ""]:
                part_name = None
            if spare_part_id in [None, "None", ""]:
                spare_part_id = None
            if center_id in [None, "None", ""]:
                center_id = None
            
            # If part_name is provided, find spare_part_id first
            if part_name and not spare_part_id:
                find_sql = "SELECT sparepartid, name, unitprice, manufacture FROM sparepart_tuht WHERE name ILIKE %s AND isactive = true LIMIT 1"
                find_rows = await fetch(find_sql, f"%{part_name}%")
                if find_rows:
                    spare_part_id = find_rows[0].get("sparepartid")
                    part_info = find_rows[0]
                else:
                    return {
                        "error": "part_not_found",
                        "message": f"Không tìm thấy phụ tùng '{part_name}' trong hệ thống",
                        "searched_part_name": part_name
                    }
            else:
                part_info = None
            
            # Only proceed if we have spare_part_id
            if not spare_part_id:
                return {
                    "error": "no_part_specified",
                    "message": "Cần chỉ định phụ tùng cụ thể để dự báo"
                }
            
            try:
                # Use integrated forecast engine
                from ai_chatbot.forecast_engine import run_forecast_async
                
                forecast_result = await run_forecast_async(
                    spare_part_id=spare_part_id,
                    center_id=center_id, 
                    forecast_months=max(1, min(12, months))
                )
                
                # Get spare part info if not already retrieved
                if not part_info and spare_part_id:
                    part_sql = "SELECT name, unitprice, manufacture FROM sparepart_tuht WHERE sparepartid = %s"
                    part_rows = await fetch(part_sql, spare_part_id)
                    if part_rows:
                        part_info = part_rows[0]
                
                return {
                    "forecast_months": months,
                    "forecast_result": forecast_result,
                    "part_info": part_info,
                    "searched_part_name": part_name,
                    "data_source": "integrated_supabase_engine",
                    "message": f"Dự báo cho {months} tháng tới đã hoàn thành"
                }
            except Exception as e:
                return {
                    "error": str(e),
                    "message": f"Dự báo cho {months} tháng tới - Lỗi hệ thống tích hợp"
                }
        
        elif function_name == "create_sparepart":
            # Phân tích thông tin đã có và còn thiếu
            provided_fields = {}
            missing_fields = []
            
            # Các trường bắt buộc theo request body mẫu
            required_fields = {
                "name": "Tên phụ tùng",
                "unitPrice": "Giá đơn vị", 
                "manufacturer": "Nhà sản xuất",
                "typeName": "Loại phụ tùng",
                "vehicleModelId": "ID mẫu xe",
                "centerName": "Tên trung tâm",
                "description": "Mô tả",
                "partNumber": "Mã phụ tùng"
            }
            
            # Kiểm tra thông tin đã cung cấp
            for field, label in required_fields.items():
                value = arguments.get(field)
                if value and value not in [None, "None", ""]:
                    provided_fields[field] = {"label": label, "value": value}
                else:
                    missing_fields.append({"field": field, "label": label})
            
            return {
                "action": "create_sparepart_form",
                "provided_fields": provided_fields,
                "missing_fields": missing_fields,
                "message": "Thông tin tạo phụ tùng mới",
                "note": "AI sẽ không tự động tạo vào database. Frontend cần hiển thị form để người dùng nhập đầy đủ thông tin."
            }
        
        else:
            return {"error": f"Unknown function: {function_name}"}
    
    async def process_chat_message(self, message: str, conversation_id: str, user_id: str = "anonymous", context: dict = None) -> dict:
        """Process a chat message with MCP function calling."""
        try:
            # Start MCP server if needed
            if self.mcp_process is None:
                self.start_mcp_server()
            
            # Get conversation context
            context_summary = self.conversation_manager.get_context_summary(conversation_id)
            
            # Minimal context to reduce tokens
            contextualized_message = f"{context_summary} {message}" if context_summary else message
            
            # Start chat session
            chat = self.model.start_chat()
            response = chat.send_message(contextualized_message)
            
            print(f"🔍 Response candidates: {len(response.candidates)}")
            if response.candidates:
                print(f"🔍 Content parts: {len(response.candidates[0].content.parts)}")
                for i, part in enumerate(response.candidates[0].content.parts):
                    print(f"🔍 Part {i}: has_function_call={hasattr(part, 'function_call')}")
                    if hasattr(part, 'function_call'):
                        print(f"🔍 Function call: {part.function_call}")
            
            # Handle function calls - LIMIT TO 1 CALL ONLY
            function_results = []
            max_calls = 1  # Only allow 1 function call
            call_count = 0
            
            while call_count < max_calls:
                # Check if response has function calls
                has_function_call = False
                
                for part in response.candidates[0].content.parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        function_call = part.function_call
                        function_name = function_call.name
                        function_args = dict(function_call.args) if function_call.args else {}
                        call_count += 1
                        has_function_call = True
                        
                        print(f"🔧 Function call: {function_name}({function_args})")
                        
                        # Call MCP function with error handling
                        try:
                            function_result = await self.call_mcp_function(function_name, function_args)
                            # Check if function returned error
                            if "error" in function_result:
                                print(f"⚠️ Function error: {function_result['error']}")
                                # Fallback to generative chat
                                fallback_response = self.fallback_model.generate_content(message)
                                return {
                                    "success": True,
                                    "response": fallback_response.text,
                                    "mode": "generative_fallback",
                                    "conversation_id": conversation_id,
                                    "timestamp": datetime.now().isoformat()
                                }
                            
                            function_results.append({
                                "function": function_name,
                                "args": function_args,
                                "result": function_result
                            })
                            
                            # Send result back to Gemini
                            response = chat.send_message(
                                genai.protos.Content(
                                    parts=[genai.protos.Part(
                                        function_response=genai.protos.FunctionResponse(
                                            name=function_name,
                                            response={"result": json.dumps(function_result, default=str)}
                                        )
                                    )]
                                )
                            )
                        except Exception as func_error:
                            print(f"⚠️ Function call failed: {func_error}")
                            # Fallback to generative chat
                            fallback_response = self.fallback_model.generate_content(message)
                            return {
                                "success": True,
                                "response": fallback_response.text,
                                "mode": "generative_fallback",
                                "conversation_id": conversation_id,
                                "timestamp": datetime.now().isoformat()
                            }
                        break
                
                if not has_function_call:
                    break
            
            # Get final response or fallback to generative chat
            try:
                ai_response = response.text if response.text else "Đã xử lý yêu cầu thành công."
                
                # If no function was called and response is empty/generic, use fallback
                if not function_results and (not ai_response or len(ai_response.strip()) < 10):
                    fallback_response = self.fallback_model.generate_content(message)
                    ai_response = fallback_response.text
                    
            except Exception as e:
                print(f"⚠️ Error getting response text: {e}")
                # Fallback to generative chat on error
                try:
                    fallback_response = self.fallback_model.generate_content(message)
                    ai_response = fallback_response.text
                except:
                    ai_response = "Đã xử lý yêu cầu thành công."
            
            # Save to conversation history
            self.conversation_manager.add_message(
                conversation_id, "user", message
            )
            self.conversation_manager.add_message(
                conversation_id, "assistant", ai_response, 
                [f["function"] for f in function_results]
            )
            
            return {
                "success": True,
                "response": ai_response,
                "function_calls": [f["function"] for f in function_results],
                "function_results": function_results,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "timestamp": datetime.now().isoformat(),
                "function_call_count": len(function_results)
            }
            
        except Exception as e:
            error_msg = f"Lỗi xử lý tin nhắn: {str(e)}"
            
            # Save error to conversation
            self.conversation_manager.add_message(
                conversation_id, "user", message
            )
            self.conversation_manager.add_message(
                conversation_id, "error", error_msg
            )
            
            return {
                "success": False,
                "error": error_msg,
                "conversation_id": conversation_id,
                "timestamp": datetime.now().isoformat()
            }
    
    def get_conversation_history(self, conversation_id: str) -> List[Dict]:
        """Get conversation history."""
        return self.conversation_manager.get_conversation(conversation_id)
    
    def close(self):
        """Clean up resources."""
        self.stop_mcp_server()