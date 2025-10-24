#!/usr/bin/env python3
"""
Check database schema for EV SCMMS AI
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# Load environment
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'config.env'))

# Add current dir to path
sys.path.append(os.path.dirname(__file__))

async def check_schema():
    """Check actual database schema."""
    try:
        from db_connection import fetch
        
        print("🔍 Checking database schema...")
        
        # Check sparepart_tuht columns
        print("\n📋 sparepart_tuht columns:")
        result = await fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sparepart_tuht' 
            ORDER BY ordinal_position
        """)
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")
        
        # Check inventory_tuht columns
        print("\n📋 inventory_tuht columns:")
        result = await fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'inventory_tuht' 
            ORDER BY ordinal_position
        """)
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")
        
        # Check sparepartusagehistory_tuht columns
        print("\n📋 sparepartusagehistory_tuht columns:")
        result = await fetch("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'sparepartusagehistory_tuht' 
            ORDER BY ordinal_position
        """)
        for row in result:
            print(f"  - {row['column_name']}: {row['data_type']}")
            
    except Exception as e:
        print(f"❌ Schema check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_schema())