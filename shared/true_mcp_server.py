#!/usr/bin/env python3
"""
True MCP (Model Context Protocol) Server for EV SCMMS AI
Provides secure database access tools for Gemini function calling.

This is a proper MCP server using the official MCP SDK from Anthropic.
Gemini can connect to this server and call the defined tools.
"""
import asyncio
import os
from dotenv import load_dotenv
from mcp.server import Server
from mcp.types import Tool, TextContent
import mcp.server.stdio
from db_connection import fetch, init_db_pool

# Load environment
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', 'config.env'))

# Create MCP server
app = Server("ev-scmms-mcp")

@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available tools that Gemini can call."""
    return [
        Tool(
            name="get_spare_parts",
            description="Get all spare parts information with inventory details",
            inputSchema={
                "type": "object",
                "properties": {
                    "spare_part_id": {
                        "type": "string",
                        "description": "Optional: specific spare part ID to filter"
                    }
                }
            }
        ),
        Tool(
            name="get_inventory",
            description="Get current inventory levels for all centers",
            inputSchema={
                "type": "object", 
                "properties": {
                    "center_id": {
                        "type": "string",
                        "description": "Optional: specific center ID to filter"
                    }
                }
            }
        ),
        Tool(
            name="get_usage_history",
            description="Get spare parts usage history for forecasting analysis",
            inputSchema={
                "type": "object",
                "properties": {
                    "months": {
                        "type": "integer",
                        "description": "Number of months of history to retrieve (1-24)",
                        "minimum": 1,
                        "maximum": 24
                    },
                    "spare_part_id": {
                        "type": "string", 
                        "description": "Optional: specific spare part ID to filter"
                    },
                    "center_id": {
                        "type": "string",
                        "description": "Optional: specific center ID to filter" 
                    }
                }
            }
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls from Gemini."""
    
    if name == "get_spare_parts":
        spare_part_id = arguments.get("spare_part_id")
        
        if spare_part_id:
            sql = """
            SELECT s.*, i.centerid, i.quantity, i.minimumstocklevel, 
                   t.name as type_name, v.name as vehicle_model_name
            FROM sparepart_tuht s
            LEFT JOIN inventory_tuht i ON s.inventoryid = i.inventoryid
            LEFT JOIN spareparttype_tuht t ON s.typeid = t.typeid
            LEFT JOIN vehiclemodel v ON s.vehiclemodelid = v.modelid
            WHERE s.sparepartid = %s AND s.isactive = true
            """
            rows = await fetch(sql, spare_part_id)
        else:
            sql = """
            SELECT s.*, i.centerid, i.quantity, i.minimumstocklevel, 
                   t.name as type_name, v.name as vehicle_model_name
            FROM sparepart_tuht s
            LEFT JOIN inventory_tuht i ON s.inventoryid = i.inventoryid
            LEFT JOIN spareparttype_tuht t ON s.typeid = t.typeid
            LEFT JOIN vehiclemodel v ON s.vehiclemodelid = v.modelid
            WHERE s.isactive = true
            """
            rows = await fetch(sql)
        
        return [TextContent(
            type="text", 
            text=f"Found {len(rows)} spare parts:\n" + str(rows)
        )]
    
    elif name == "get_inventory":
        center_id = arguments.get("center_id")
        
        if center_id:
            sql = """
            SELECT i.*, s.sparepartid, s.name as spare_part_name, s.unitprice, s.manufacture
            FROM inventory_tuht i
            LEFT JOIN sparepart_tuht s ON i.inventoryid = s.inventoryid
            WHERE i.centerid = %s AND i.isactive = true
            """
            rows = await fetch(sql, center_id)
        else:
            sql = """
            SELECT i.*, s.sparepartid, s.name as spare_part_name, s.unitprice, s.manufacture
            FROM inventory_tuht i
            LEFT JOIN sparepart_tuht s ON i.inventoryid = s.inventoryid
            WHERE i.isactive = true
            """
            rows = await fetch(sql)
        
        return [TextContent(
            type="text",
            text=f"Found {len(rows)} inventory items:\n" + str(rows)
        )]
    
    elif name == "get_usage_history":
        months = arguments.get("months", 12)
        spare_part_id = arguments.get("spare_part_id")
        center_id = arguments.get("center_id")
        
        # Validate months
        months = max(1, min(24, months))
        
        sql = """
        SELECT h.*, s.name as spare_part_name, s.unitprice, c.name as center_name
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
            
        sql += " ORDER BY h.useddate DESC"
        rows = await fetch(sql, *params)
        
        return [TextContent(
            type="text",
            text=f"Found {len(rows)} usage records for last {months} months:\n" + str(rows)
        )]
    
    else:
        return [TextContent(
            type="text",
            text=f"Unknown tool: {name}"
        )]

async def main():
    """Run the MCP server."""
    # Initialize database pool
    await init_db_pool()
    print("🚀 EV SCMMS MCP Server starting...")
    print("📊 Database connection initialized")
    print("🔧 Available tools: get_spare_parts, get_inventory, get_usage_history")
    
    # Run MCP server via stdio
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream, write_stream, 
            app.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())