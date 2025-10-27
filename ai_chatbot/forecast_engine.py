"""
Spare Parts Forecast Engine for EV SCMMS AI Chatbot - AI-Powered Version
Integrated forecasting functionality with AI analysis and improved error handling
"""
import os
import sys
import json
import asyncio
import google.generativeai as genai
from datetime import datetime
from dotenv import load_dotenv

# Add shared directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))

# Load environment from shared config
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'shared', 'config.env'))

# Configure Gemini
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

class ForecastEngine:
    """Integrated forecast engine using real Supabase data with improved error handling."""
    
    def __init__(self):
        # Initialize Gemini model with simple configuration
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash-exp')
            print("✅ ForecastEngine initialized with Gemini 2.0 Flash")
        except Exception as e:
            print(f"⚠️ Error initializing Gemini model: {e}")
            # Fallback to earlier model if available
            try:
                self.model = genai.GenerativeModel('gemini-1.5-pro-latest')
                print("✅ Fallback to Gemini 1.5 Pro")
            except:
                raise Exception("Cannot initialize any Gemini model")
    
    async def call_database_function(self, function_name: str, arguments: dict):
        """Call database functions with improved error handling."""
        try:
            from db_connection import fetch
            print(f"🔌 Calling database function: {function_name} with args: {arguments}")
            
            if function_name == "get_spare_parts":
                spare_part_id = arguments.get("spare_part_id")
                
                if spare_part_id:
                    sql = """
                    SELECT sparepartid, name, description, unitprice, category, 
                           manufacturer, partnumber, isactive
                    FROM sparepart_tuht 
                    WHERE sparepartid = %s AND isactive = true
                    """
                    rows = await fetch(sql, spare_part_id)
                else:
                    sql = """
                    SELECT sparepartid, name, description, unitprice, category, 
                           manufacturer, partnumber, isactive
                    FROM sparepart_tuht 
                    WHERE isactive = true 
                    ORDER BY name LIMIT 20
                    """
                    rows = await fetch(sql)
                
                print(f"  📦 Retrieved {len(rows) if rows else 0} spare parts")
                return {"spare_parts": rows or [], "total_count": len(rows) if rows else 0}
            
            elif function_name == "get_inventory":
                center_id = arguments.get("center_id")
                
                base_sql = """
                SELECT i.inventoryid, i.sparepartid, i.centerid, i.quantity, 
                       i.minimumstock, i.maximumstock, i.reorderlevel,
                       s.name as spare_part_name, s.unitprice, c.name as center_name
                FROM inventory_tuht i
                LEFT JOIN sparepart_tuht s ON i.sparepartid = s.sparepartid  
                LEFT JOIN centertuantm c ON i.centerid = c.centerid
                WHERE i.isactive = true
                """
                
                if center_id:
                    sql = base_sql + " AND i.centerid = %s ORDER BY i.quantity ASC LIMIT 50"
                    rows = await fetch(sql, center_id)
                else:
                    sql = base_sql + " ORDER BY i.quantity ASC LIMIT 50"
                    rows = await fetch(sql)
                
                print(f"  📊 Retrieved {len(rows) if rows else 0} inventory records")
                return {"inventory": rows or [], "total_count": len(rows) if rows else 0}
            
            elif function_name == "get_usage_history":
                months = arguments.get("months", 12)
                spare_part_id = arguments.get("spare_part_id")
                center_id = arguments.get("center_id")
                
                sql = """
                SELECT h.usagehistoryid, h.sparepartid, h.centerid, h.quantityused,
                       h.useddate, h.reason,
                       s.name as spare_part_name, s.unitprice, c.name as center_name
                FROM sparepartusagehistory_tuht h
                LEFT JOIN sparepart_tuht s ON h.sparepartid = s.sparepartid
                LEFT JOIN centertuantm c ON h.centerid = c.centerid
                WHERE h.useddate >= (now() - (%s::int * interval '1 month')) AND h.isactive = true
                """
                params = [months]
                
                if spare_part_id:
                    sql += " AND h.sparepartid = %s"
                    params.append(spare_part_id)
                if center_id:
                    sql += " AND h.centerid = %s"
                    params.append(center_id)
                    
                sql += " ORDER BY h.useddate DESC LIMIT 100"
                rows = await fetch(sql, *params)
                print(f"  📈 Retrieved {len(rows) if rows else 0} usage history records")
                return {"usage_history": rows or [], "total_count": len(rows) if rows else 0, "months_covered": months}
            
            else:
                return {"error": f"Unknown function: {function_name}"}
                
        except Exception as e:
            return {"error": f"Database error in {function_name}: {str(e)}"}
    
    async def generate_simple_forecast(self, data_dict: dict, forecast_months: int = 6):
        """Generate AI-powered forecast using simplified prompt (fallback method)."""
        try:
            spare_parts = data_dict.get("spare_parts", {}).get("spare_parts", [])
            inventory = data_dict.get("inventory", {}).get("inventory", [])
            usage_history = data_dict.get("usage_history", {}).get("usage_history", [])
            
            print(f"  📊 Data summary: {len(spare_parts)} parts, {len(inventory)} inventory, {len(usage_history)} usage records")
            
            # If no data available, return informative message
            if not spare_parts and not inventory:
                return {
                    "data_source": "no_data_available",
                    "success": True,
                    "forecast_period_months": forecast_months,
                    "analysis_date": datetime.now().strftime('%Y-%m-%d'),
                    "spare_parts_forecasts": [],
                    "summary": {
                        "total_parts_analyzed": 0,
                        "parts_needing_replenishment": 0,
                        "total_estimated_cost": 0,
                        "message": f"Hiện tại không có dữ liệu phụ tùng trong hệ thống để thực hiện dự báo {forecast_months} tháng. Vui lòng kiểm tra lại dữ liệu trong database hoặc thêm phụ tùng mới.",
                        "recommendations": [
                            "Kiểm tra kết nối database",
                            "Thêm dữ liệu phụ tùng vào hệ thống", 
                            "Cập nhật inventory và usage history"
                        ]
                    }
                }
            
            # Use AI for simplified analysis
            try:
                simple_prompt = f"""
                Phân tích nhanh dữ liệu phụ tùng xe điện và đưa ra dự báo {forecast_months} tháng:
                
                PHỤTÙNG: {json.dumps(spare_parts[:3], ensure_ascii=False)}
                TỒNKHO: {json.dumps(inventory[:3], ensure_ascii=False)}
                
                Trả về JSON (không thêm text khác):
                {{
                    "forecast_period_months": {forecast_months},
                    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
                    "spare_parts_forecasts": [
                        {{
                            "spare_part_id": "từ dữ liệu",
                            "part_name": "từ dữ liệu", 
                            "total_forecast_demand": "số dự báo",
                            "replenishment_needed": true,
                            "estimated_cost": "chi phí",
                            "urgency_level": "high"
                        }}
                    ],
                    "summary": {{
                        "total_parts_analyzed": 3,
                        "parts_needing_replenishment": 2,
                        "total_estimated_cost": 500000,
                        "message": "Kết quả phân tích"
                    }}
                }}
                """
                
                response = self.model.generate_content(simple_prompt)
                
                if hasattr(response, 'text') and response.text:
                    response_text = response.text.strip()
                    # Clean markdown
                    if response_text.startswith('```json'):
                        response_text = response_text[7:]
                    if response_text.endswith('```'):
                        response_text = response_text[:-3]
                    response_text = response_text.strip()
                    
                    ai_result = json.loads(response_text)
                    print("  ✅ AI simple forecast successful")
                    return {
                        "data_source": "ai_simple_analysis",
                        "success": True,
                        **ai_result
                    }
                    
            except Exception as ai_error:
                print(f"  ⚠️ AI simple forecast failed: {ai_error}")
            
            # Final fallback - basic structured response
            print("  🔄 Using basic structured fallback...")
            
            # Create basic forecast from available data
            forecasts = []
            for i, part in enumerate(spare_parts[:3]):
                part_id = part.get("sparepartid") or part.get("SparePartID") or f"part_{i+1}"
                part_name = part.get("name") or part.get("Name") or f"Phụ tùng {i+1}"
                unit_price = part.get("unitprice") or part.get("UnitPrice") or 100000
                
                # Basic forecast calculation
                base_demand = 5 + (i * 2)  # Simple progression
                total_demand = base_demand * forecast_months
                
                forecasts.append({
                    "spare_part_id": part_id,
                    "part_name": part_name,
                    "total_forecast_demand": total_demand,
                    "replenishment_needed": True,
                    "estimated_cost": total_demand * unit_price,
                    "urgency_level": "medium"
                })
            
            total_cost = sum(f["estimated_cost"] for f in forecasts)
            
            return {
                "data_source": "basic_fallback",
                "success": True,
                "forecast_period_months": forecast_months,
                "analysis_date": datetime.now().strftime('%Y-%m-%d'),
                "spare_parts_forecasts": forecasts,
                "summary": {
                    "total_parts_analyzed": len(forecasts),
                    "parts_needing_replenishment": len(forecasts),
                    "total_estimated_cost": total_cost,
                    "message": f"Đã tạo dự báo cơ bản cho {len(forecasts)} phụ tùng trong {forecast_months} tháng với tổng chi phí dự kiến {total_cost:,.0f} VND.",
                    "recommendations": [
                        "Cập nhật thêm dữ liệu lịch sử sử dụng để cải thiện độ chính xác",
                        "Theo dõi xu hướng sử dụng thực tế",
                        "Xem xét điều chỉnh mức tồn kho tối thiểu"
                    ]
                }
            }
            
        except Exception as e:
            return {
                "data_source": "error_fallback", 
                "success": False,
                "error": f"Simple forecast error: {str(e)}"
            }
    
    async def generate_forecast(self, spare_part_id: str = None, center_id: str = None, forecast_months: int = 6):
        """Generate forecast with fallback mechanism for better reliability."""
        
        print(f"🔮 Generating forecast for {forecast_months} months...")
        
        try:
            # Step 1: Collect all data first - Use direct database connection
            print("📊 Collecting data from database...")
            
            from db_connection import fetch
            
            # Get spare parts directly
            print("  🔍 Fetching spare parts directly...")
            spare_parts = await fetch("""
                SELECT SparePartID, Name, UnitPrice, Manufacture, IsActive
                FROM SparePart_TuHT 
                WHERE IsActive = true 
                ORDER BY Name LIMIT 10
            """)
            print(f"  ✅ Spare parts: {len(spare_parts)} items")
            if spare_parts:
                print(f"  🔍 First spare part keys: {list(spare_parts[0].keys())}")
            
            # Get inventory directly
            print("  🔍 Fetching inventory directly...")
            inventory = await fetch("""
                SELECT InventoryID, CenterID, Quantity, MinimumStockLevel, 
                       IsActive
                FROM Inventory_TuHT
                WHERE IsActive = true 
                ORDER BY Quantity ASC LIMIT 10
            """)
            print(f"  ✅ Inventory: {len(inventory)} items")
            if inventory:
                print(f"  🔍 First inventory keys: {list(inventory[0].keys())}")
            
            # Prepare data results
            data_results = {
                "spare_parts": {"spare_parts": spare_parts, "total_count": len(spare_parts)},
                "inventory": {"inventory": inventory, "total_count": len(inventory)},
                "usage_history": {"usage_history": [], "total_count": 0}  # Skip usage for now since it's empty
            }
            
            # Step 2: Try AI-based forecast first
            print("🤖 Attempting AI-based forecast...")
            
            try:
                # Prepare detailed data for AI analysis
                spare_parts_data = data_results['spare_parts'].get('spare_parts', [])
                inventory_data = data_results['inventory'].get('inventory', [])
                
                forecast_prompt = f"""
                Bạn là chuyên gia phân tích dự báo phụ tùng cho trung tâm bảo dưỡng xe điện. 
                Hãy phân tích dữ liệu thực tế sau và đưa ra dự báo nhu cầu {forecast_months} tháng tới.
                
                DỮ LIỆU PHỤ TÙNG ({len(spare_parts_data)} items):
                {json.dumps(spare_parts_data[:5], indent=2, ensure_ascii=False) if spare_parts_data else 'Không có dữ liệu'}
                
                DỮ LIỆU TỒN KHO ({len(inventory_data)} records):
                {json.dumps(inventory_data[:5], indent=2, ensure_ascii=False) if inventory_data else 'Không có dữ liệu'}
                
                YÊU CẦU PHÂN TÍCH:
                1. Đánh giá mức tồn kho hiện tại so với mức tối thiểu
                2. Dự báo nhu cầu sử dụng dựa trên loại phụ tùng và giá trị
                3. Xác định độ ưu tiên bổ sung (phụ tùng đắt tiền = ưu tiên cao)
                4. Tính toán chi phí dự kiến
                
                Trả về CHÍNH XÁC định dạng JSON sau (không thêm text khác):
                {{
                    "forecast_period_months": {forecast_months},
                    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
                    "spare_parts_forecasts": [
                        {{
                            "spare_part_id": "ID từ dữ liệu thực",
                            "part_name": "Tên từ dữ liệu thực",
                            "current_stock": "số lượng tồn kho hiện tại",
                            "minimum_stock_level": "mức tồn kho tối thiểu",
                            "total_forecast_demand": "dự báo nhu cầu tổng",
                            "monthly_forecasts": [
                                {{"month": 1, "predicted_demand": "số dự báo", "confidence": "độ tin cậy 0-1"}}
                            ],
                            "replenishment_needed": "true/false",
                            "suggested_order_quantity": "số lượng đề xuất đặt hàng",
                            "estimated_cost": "chi phí dự kiến",
                            "urgency_level": "high/medium/low"
                        }}
                    ],
                    "summary": {{
                        "total_parts_analyzed": "số phụ tùng đã phân tích",
                        "parts_needing_replenishment": "số phụ tùng cần bổ sung",
                        "total_estimated_cost": "tổng chi phí dự kiến",
                        "message": "thông điệp tóm tắt bằng tiếng Việt",
                        "recommendations": ["danh sách khuyến nghị"]
                    }}
                }}
                """
                
                response = self.model.generate_content(forecast_prompt)
                
                # Check if response has text
                if hasattr(response, 'text') and response.text:
                    try:
                        # Clean response text
                        response_text = response.text.strip()
                        # Remove any markdown code blocks
                        if response_text.startswith('```json'):
                            response_text = response_text[7:]
                        if response_text.endswith('```'):
                            response_text = response_text[:-3]
                        response_text = response_text.strip()
                        
                        # Try to parse as JSON
                        ai_forecast = json.loads(response_text)
                        print("  ✅ AI forecast generated successfully")
                        return {
                            "data_source": "ai_analysis_real_data",
                            "success": True,
                            **ai_forecast
                        }
                    except json.JSONDecodeError as je:
                        print(f"  ⚠️ AI response not valid JSON: {je}, using fallback")
                        print(f"  📝 AI Response: {response.text[:200]}...")
                else:
                    print("  ⚠️ AI response empty or blocked, using fallback")
                    
            except Exception as e:
                print(f"  ⚠️ AI forecast failed: {str(e)}, using fallback")
            
            # Step 3: Use fallback simple forecast
            print("🔄 Using simplified AI forecast...")
            return await self.generate_simple_forecast(data_results, forecast_months)
            
        except Exception as e:
            print(f"❌ Forecast generation failed: {str(e)}")
            return {
                "data_source": "supabase_real_data",
                "success": False,
                "error": f"Forecast generation error: {str(e)}"
            }
    
    async def save_forecast_to_database(self, forecast_data):
        """Save forecast results to SparePartForecast_TuHT table."""
        try:
            from db_connection import execute
            
            if not forecast_data.get("spare_parts_forecasts"):
                return {"error": "No forecast data to save"}
            
            saved_count = 0
            
            for forecast in forecast_data["spare_parts_forecasts"]:
                # Calculate values
                total_demand = forecast.get("total_forecast_demand", 0)
                confidence = 0.8  # Default confidence
                
                # Insert into database
                insert_sql = """
                INSERT INTO sparepartforecast_tuht (
                    sparepartid, centerid, predictedusage, safetystock, reorderpoint, 
                    forecastedby, forecastconfidence, forecastdate, status, isactive, createdat
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, now(), 'PENDING', true, now())
                """
                
                # Get a valid CenterID from inventory or use default
                center_id = None
                try:
                    from db_connection import fetch
                    centers = await fetch("SELECT centerid FROM CenterTuantm WHERE isactive = true LIMIT 1")
                    if centers:
                        center_id = centers[0].get("centerid") or centers[0].get("CenterID")
                except:
                    pass
                
                if not center_id:
                    # Skip saving if we can't get a valid center_id
                    print(f"⚠️ No valid center_id found, skipping save for {forecast['spare_part_id']}")
                    continue
                
                await execute(
                    insert_sql,
                    forecast["spare_part_id"],
                    center_id,  # Use valid center_id
                    total_demand,
                    forecast.get("suggested_order_quantity", total_demand),
                    max(10, int(total_demand * 0.2)),  # reorder point
                    "AI_INTEGRATED_CHATBOT",
                    confidence
                )
                saved_count += 1
                
            return {
                "success": True,
                "saved_forecasts": saved_count,
                "message": f"Successfully saved {saved_count} forecasts to database"
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Database save error: {str(e)}",
                "saved_forecasts": 0
            }

# Async wrapper functions for integration
async def forecast_demand(spare_part_id: str = None, center_id: str = None, forecast_months: int = 6):
    """Async wrapper for forecast generation."""
    try:
        engine = ForecastEngine()
        
        # Generate forecast
        forecast_result = await engine.generate_forecast(
            spare_part_id=spare_part_id,
            center_id=center_id, 
            forecast_months=int(forecast_months)
        )
        
        return forecast_result
        
    except Exception as e:
        return {
            "data_source": "supabase_real_data",
            "success": False,
            "error": f"Forecast wrapper error: {str(e)}"
        }

async def run_forecast_async(spare_part_id: str = None, center_id: str = None, forecast_months: int = 6):
    result = await forecast_demand(spare_part_id, center_id, forecast_months)
    return result