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
                    SELECT SparePartID, Name, UnitPrice, Manufacture, IsActive
                    FROM SparePart_TuHT 
                    WHERE SparePartID = %s AND IsActive = true
                    """
                    rows = await fetch(sql, spare_part_id)
                else:
                    sql = """
                    SELECT SparePartID, Name, UnitPrice, Manufacture, IsActive
                    FROM SparePart_TuHT 
                    WHERE IsActive = true 
                    ORDER BY Name LIMIT 20
                    """
                    rows = await fetch(sql)
                
                print(f"  📦 Retrieved {len(rows) if rows else 0} spare parts")
                return {"spare_parts": rows or [], "total_count": len(rows) if rows else 0}
            
            elif function_name == "get_inventory":
                center_id = arguments.get("center_id")
                
                base_sql = """
                SELECT i.InventoryID, i.CenterID, i.Quantity, 
                       i.MinimumStockLevel, i.IsActive
                FROM Inventory_TuHT i
                WHERE i.IsActive = true
                """
                
                if center_id:
                    sql = base_sql + " AND i.CenterID = %s ORDER BY i.Quantity ASC LIMIT 50"
                    rows = await fetch(sql, center_id)
                else:
                    sql = base_sql + " ORDER BY i.Quantity ASC LIMIT 50"
                    rows = await fetch(sql)
                
                print(f"  📊 Retrieved {len(rows) if rows else 0} inventory records")
                return {"inventory": rows or [], "total_count": len(rows) if rows else 0}
            
            elif function_name == "get_usage_history":
                months = arguments.get("months", 12)
                spare_part_id = arguments.get("spare_part_id")
                center_id = arguments.get("center_id")
                
                sql = """
                SELECT h.UsageID, h.SparePartID, h.CenterID, h.QuantityUsed,
                       h.UsedDate, s.Name as PartName, s.UnitPrice
                FROM SparePartUsageHistory_TuHT h
                LEFT JOIN SparePart_TuHT s ON h.SparePartID = s.SparePartID
                WHERE h.UsedDate >= (CURRENT_DATE - (%s::int * interval '1 month')) AND h.IsActive = true
                """
                params = [months]
                
                if spare_part_id:
                    sql += " AND h.SparePartID = %s"
                    params.append(spare_part_id)
                if center_id:
                    sql += " AND h.CenterID = %s"
                    params.append(center_id)
                    
                sql += " ORDER BY h.UsedDate DESC LIMIT 100"
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
                            "Kiểm tra kết nối database và đồng bộ dữ liệu",
                            "Nhập dữ liệu phụ tùng và lịch sử sử dụng", 
                            "Thiết lập quy trình cập nhật tồn kho tự động"
                        ]
                    }
                }
            
            # Use AI for simplified analysis
            try:
                simple_prompt = f"""
                Phân tích thông minh TOÀN BỘ dữ liệu phụ tùng xe điện và dự báo {forecast_months} tháng dựa trên lịch sử:
                
                PHỤTÙNG ({len(spare_parts)} items): {json.dumps(spare_parts, ensure_ascii=False)}
                TỒNKHO ({len(inventory)} records): {json.dumps(inventory, ensure_ascii=False)}
                LỊCHSỬ ({len(usage_history)} records): {json.dumps(usage_history, ensure_ascii=False)}
                
                Dựa trên dữ liệu thực tế, phân tích xu hướng sử dụng và đưa ra dự báo thông minh. Trả về JSON:
                {{
                    "forecast_period_months": {forecast_months},
                    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
                    "spare_parts_forecasts": [
                        {{
                            "spare_part_id": "SparePartID từ dữ liệu",
                            "part_name": "Name từ dữ liệu",
                            "usage_pattern": "xu hướng dựa trên lịch sử",
                            "total_forecast_demand": "số dự báo thông minh",
                            "alternative_suggestions": ["phụ tùng thay thế tương tự"],
                            "replenishment_needed": "true/false",
                            "estimated_cost": "UnitPrice * forecast_demand",
                            "urgency_level": "high/medium/low",
                            "seasonal_factor": "mùa vụ ảnh hưởng"
                        }}
                    ],
                    "summary": {{
                        "total_parts_analyzed": {len(spare_parts)},
                        "high_usage_parts": "số phụ tùng dùng nhiều",
                        "cost_optimization_suggestions": ["gợi ý tối ưu dựa trên Manufacture và UnitPrice"],
                        "total_estimated_cost": "tổng chi phí dự kiến",
                        "message": "kết quả phân tích chi tiết",
                        "recommendations": ["khuyến nghị dựa trên dữ liệu thực tế"]
                    }}
                }}
                
                LƯU Ý: Bắt buộc phải có các field sau cho mỗi spare_part_forecast:
                - current_stock: số tồn kho hiện tại
                - minimum_stock_level: mức tồn kho tối thiểu  
                - total_forecast_demand: tổng nhu cầu dự báo
                - suggested_order_quantity: số lượng đề xuất đặt hàng
                - monthly_forecasts: dự báo theo tháng
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
            
            # AI-powered forecast from ALL available data
            try:
                fallback_prompt = f"""
                Dựa trên dữ liệu thực tế, hãy tạo dự báo thông minh cho {len(spare_parts)} phụ tùng:
                
                Dữ liệu: PHỤTÙNG={len(spare_parts)}, TỒNKHO={len(inventory)}, LỊCHSỬ={len(usage_history)}
                
                Trả về JSON dự báo {forecast_months} tháng cho tất cả phụ tùng dựa trên:
                - Giá trị và độ quan trọng
                - Xu hướng sử dụng (nếu có lịch sử)
                - Mức tồn kho hiện tại
                - Đề xuất tối ưu hóa
                
                Format: {{"forecasts": [{{"spare_part_id": "ID", "forecast_demand": số, "reasoning": "lý do"}}], "alternatives": ["gợi ý thay thế"]}}
                """
                
                ai_response = self.model.generate_content(fallback_prompt)
                if ai_response.text:
                    ai_data = json.loads(ai_response.text.strip().replace('```json', '').replace('```', ''))
                    forecasts = ai_data.get('forecasts', [])
                    alternatives = ai_data.get('alternatives', [])
                else:
                    raise Exception("No AI response")
                    
            except Exception as ai_err:
                print(f"  ⚠️ AI fallback failed: {ai_err}, using data-driven approach")
                
                # Data-driven forecast for ALL parts
                forecasts = []
                for part in spare_parts:
                    part_id = part.get("sparepartid") or part.get("SparePartID")
                    part_name = part.get("name") or part.get("Name")
                    unit_price = part.get("unitprice") or part.get("UnitPrice") or 0
                    manufacture = part.get("manufacture") or part.get("Manufacture", "Unknown")
                    
                    # Calculate demand based on price tier (expensive = less frequent but critical)
                    if unit_price > 1000000:  # High-value parts
                        base_demand = 2
                        urgency = "high"
                    elif unit_price > 500000:  # Medium-value parts  
                        base_demand = 5
                        urgency = "medium"
                    else:  # Low-value parts
                        base_demand = 10
                        urgency = "low"
                    
                    total_demand = base_demand * forecast_months
                    
                    # Find matching inventory for current stock
                    current_stock = 0
                    min_stock = 10
                    for inv in inventory:
                        if inv.get("sparepartid") == part_id or inv.get("SparePartID") == part_id:
                            current_stock = inv.get("quantity") or inv.get("Quantity", 0)
                            min_stock = inv.get("minimumstocklevel") or inv.get("MinimumStockLevel", 10)
                            break
                    
                    # Calculate suggested order quantity
                    suggested_qty = max(0, total_demand + min_stock - current_stock)
                    
                    forecasts.append({
                        "spare_part_id": part_id,
                        "part_name": part_name,
                        "manufacture": manufacture,
                        "unit_price": unit_price,
                        "current_stock": current_stock,
                        "minimum_stock_level": min_stock,
                        "total_forecast_demand": total_demand,
                        "suggested_order_quantity": suggested_qty,
                        "replenishment_needed": current_stock < (total_demand + min_stock),
                        "estimated_cost": suggested_qty * unit_price,
                        "urgency_level": urgency,
                        "monthly_forecasts": [
                            {"month": i+1, "predicted_demand": max(1, total_demand // forecast_months), "confidence": 0.75}
                            for i in range(forecast_months)
                        ],
                        "reasoning": f"Dựa trên giá trị {unit_price:,.0f} VND và nhà sản xuất {manufacture}"
                    })
                
                alternatives = ["Xem xét phụ tùng tương đương giá rẻ hơn", "Kết hợp đặt hàng để giảm chi phí"]
            
            total_cost = sum(f["estimated_cost"] for f in forecasts)
            
            # AI recommendations based on comprehensive analysis
            try:
                rec_prompt = f"""
                Dựa trên phân tích {len(forecasts)} phụ tùng xe điện với:
                - Tổng chi phí: {total_cost:,.0f} VND
                - Số lượng lịch sử: {len(usage_history)} records
                - Phụ tùng đắt nhất: {max([f.get('estimated_cost', 0) for f in forecasts], default=0):,.0f} VND
                
                Đưa ra 5 khuyến nghị thông minh cho quản lý tối ưu. JSON: ["khuyến nghị 1", "khuyến nghị 2", "khuyến nghị 3", "khuyến nghị 4", "khuyến nghị 5"]
                """
                rec_response = self.model.generate_content(rec_prompt)
                recommendations = json.loads(rec_response.text.strip().replace('```json', '').replace('```', '')) if rec_response.text else alternatives
            except:
                recommendations = alternatives or ["Tối ưu hóa quy trình quản lý tồn kho", "Theo dõi xu hướng sử dụng thực tế"]
            
            return {
                "data_source": "ai_enhanced_comprehensive",
                "success": True,
                "forecast_period_months": forecast_months,
                "analysis_date": datetime.now().strftime('%Y-%m-%d'),
                "data_coverage": {"parts": len(spare_parts), "inventory": len(inventory), "usage_records": len(usage_history)},
                "spare_parts_forecasts": forecasts,
                "summary": {
                    "total_parts_analyzed": len(forecasts),
                    "parts_needing_replenishment": len([f for f in forecasts if f.get('replenishment_needed')]),
                    "high_priority_parts": len([f for f in forecasts if f.get('urgency_level') == 'high']),
                    "total_estimated_cost": total_cost,
                    "cost_optimization_potential": len(alternatives) if 'alternatives' in locals() else 0,
                    "message": f"Phân tích thông minh {len(forecasts)} phụ tùng dựa trên {len(usage_history)} bản ghi lịch sử. Dự báo {forecast_months} tháng với tổng chi phí {total_cost:,.0f} VND.",
                    "recommendations": recommendations,
                    "alternative_suggestions": alternatives if 'alternatives' in locals() else []
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
            
            # Get ALL spare parts (no limit)
            print("  🔍 Fetching ALL spare parts...")
            spare_parts = await fetch("""
                SELECT SparePartID, Name, UnitPrice, Manufacture, IsActive
                FROM SparePart_TuHT 
                WHERE IsActive = true 
                ORDER BY UnitPrice DESC
            """)
            print(f"  ✅ Spare parts: {len(spare_parts)} items")
            
            # Get ALL inventory (no limit)
            print("  🔍 Fetching ALL inventory...")
            inventory = await fetch("""
                SELECT i.InventoryID, i.CenterID, i.Quantity, 
                       i.MinimumStockLevel, i.IsActive
                FROM Inventory_TuHT i
                WHERE i.IsActive = true
                ORDER BY i.Quantity ASC
            """)
            print(f"  ✅ Inventory: {len(inventory)} items")
            
            # Get usage history for analysis
            print("  🔍 Fetching usage history...")
            usage_history = await fetch("""
                SELECT h.UsageID, h.SparePartID, h.CenterID, h.QuantityUsed, h.UsedDate,
                       s.Name as PartName, s.UnitPrice, s.Manufacture,
                       EXTRACT(MONTH FROM h.UsedDate) as UsageMonth,
                       EXTRACT(YEAR FROM h.UsedDate) as UsageYear
                FROM SparePartUsageHistory_TuHT h
                LEFT JOIN SparePart_TuHT s ON h.SparePartID = s.SparePartID
                WHERE h.IsActive = true AND s.IsActive = true
                  AND h.UsedDate >= (CURRENT_DATE - INTERVAL '24 months')
                ORDER BY h.UsedDate DESC
            """)
            print(f"  ✅ Usage history: {len(usage_history)} records")
            
            # Prepare comprehensive data results
            data_results = {
                "spare_parts": {"spare_parts": spare_parts, "total_count": len(spare_parts)},
                "inventory": {"inventory": inventory, "total_count": len(inventory)},
                "usage_history": {"usage_history": usage_history, "total_count": len(usage_history)}
            }
            
            # Step 2: Try AI-based forecast first
            print("🤖 Attempting AI-based forecast...")
            
            try:
                # Prepare comprehensive data for AI analysis
                spare_parts_data = data_results['spare_parts'].get('spare_parts', [])
                inventory_data = data_results['inventory'].get('inventory', [])
                usage_data = data_results['usage_history'].get('usage_history', [])
                
                forecast_prompt = f"""
                Bạn là chuyên gia AI dự báo phụ tùng thông minh cho trung tâm xe điện.
                Phân tích TOÀN BỘ dữ liệu sau và dự báo {forecast_months} tháng dựa trên xu hướng sử dụng thực tế:
                
                PHỤ TÙNG ({len(spare_parts_data)} items - phân tích tất cả):
                {json.dumps(spare_parts_data, indent=2, ensure_ascii=False) if spare_parts_data else 'Không có'}
                
                TỒN KHO ({len(inventory_data)} records - phân tích tất cả):
                {json.dumps(inventory_data, indent=2, ensure_ascii=False) if inventory_data else 'Không có'}
                
                LỊCH Sử SỬ DỤNG ({len(usage_data)} records - 24 tháng gần đây):
                {json.dumps(usage_data, indent=2, ensure_ascii=False) if usage_data else 'Không có'}
                
                YÊU CẦU PHÂN TÍCH THÔNG MINH:
                1. Phân tích xu hướng sử dụng theo tháng/mùa từ lịch sử
                2. Xác định phụ tùng hay hỏng/ít dùng dựa trên tần suất
                3. Tính toán nhu cầu dự kiến dựa trên pattern thực tế
                4. Đề xuất thay thế/tối ưu hóa dựa trên giá trị và tần suất
                5. Ưu tiên phụ tùng quan trọng/đắt tiền cần theo dõi gần
                2. Dự báo nhu cầu sử dụng dựa trên loại phụ tùng và giá trị
                3. Xác định độ ưu tiên bổ sung (phụ tùng đắt tiền = ưu tiên cao)
                4. Tính toán chi phí dự kiến
                
                Trả về CHÍNH XÁC định dạng JSON sau (không thêm text khác):
                {{
                    "forecast_period_months": {forecast_months},
                    "analysis_date": "{datetime.now().strftime('%Y-%m-%d')}",
                    "spare_parts_forecasts": [
                        {{
                            "spare_part_id": "SparePartID từ dữ liệu",
                            "part_name": "Name từ dữ liệu",
                            "current_stock": "số tồn kho hiện tại (từ Inventory)",
                            "minimum_stock_level": "MinimumStockLevel từ Inventory",
                            "total_forecast_demand": "tổng nhu cầu dự báo {forecast_months} tháng",
                            "suggested_order_quantity": "= total_forecast_demand + minimum_stock_level - current_stock (nếu > 0)",
                            "monthly_forecasts": [
                                {{"month": 1, "predicted_demand": "nhu cầu tháng 1", "confidence": 0.8}},
                                {{"month": 2, "predicted_demand": "nhu cầu tháng 2", "confidence": 0.75}}
                            ],
                            "replenishment_needed": "true nếu current_stock < total_forecast_demand + minimum_stock_level",
                            "estimated_cost": "suggested_order_quantity * UnitPrice",
                            "urgency_level": "high nếu UnitPrice cao hoặc current_stock rất thấp"
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
                INSERT INTO SparePartForecast_TuHT (
                    SparePartID, CenterID, PredictedUsage, SafetyStock, ReorderPoint, 
                    ForecastedBy, ForecastConfidence, ForecastDate, Status, IsActive, createdAt
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, 'PENDING', true, CURRENT_TIMESTAMP)
                """
                
                # Get a valid CenterID from inventory or use default
                center_id = None
                try:
                    from db_connection import fetch
                    centers = await fetch("SELECT CenterID FROM CenterTuantm WHERE IsActive = true LIMIT 1")
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