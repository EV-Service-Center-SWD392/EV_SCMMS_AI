"""
Database connection helper using psycopg2 with threading.
Provides a simple connection pool and helper functions for fetch/execute.
"""
import os
import threading
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool
from typing import Any, List, Optional, Dict
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), 'config.env'))

_pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
_lock = threading.Lock()


def _get_db_config() -> Dict[str, str]:
    config = {
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '5432')),
        'database': os.getenv('DB_NAME', 'postgres'),
        'user': os.getenv('DB_USER', 'postgres'),
        'password': os.getenv('DB_PASS', ''),
        'sslmode': 'require'  # Required for Supabase
    }
    print(f"🔌 Database config: {config['host']}:{config['port']}")
    return config


async def init_db_pool():
    global _pool
    with _lock:
        if _pool is None:
            config = _get_db_config()
            _pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=1,
                maxconn=10,
                **config
            )


async def close_db_pool():
    global _pool
    with _lock:
        if _pool:
            _pool.closeall()
            _pool = None


async def fetch(query: str, *args) -> List[Dict[str, Any]]:
    """Run a SELECT and return rows as list of dicts."""
    global _pool
    if _pool is None:
        await init_db_pool()
    
    conn = None
    try:
        conn = _pool.getconn()
        with conn.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(query, args if args else None)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    finally:
        if conn:
            _pool.putconn(conn)


async def execute(query: str, *args) -> str:
    """Run INSERT/UPDATE/DELETE and return the command status."""
    global _pool
    if _pool is None:
        await init_db_pool()
    
    conn = None
    try:
        conn = _pool.getconn()
        with conn.cursor() as cursor:
            cursor.execute(query, args if args else None)
            conn.commit()
            return cursor.statusmessage
    finally:
        if conn:
            _pool.putconn(conn)


async def insert_forecast_row(spare_part_id: str, center_id: str, predicted_usage: int, safety_stock: int, reorder_point: int, confidence: float, forecasted_by: str = "AI"):
    """Insert a forecast row into SparePartForecast_TuHT.
    Schema: ForecastID, SparePartID, CenterID, PredictedUsage, SafetyStock, ReorderPoint, 
    ForecastedBy, ForecastConfidence, ForecastDate, Status, IsActive, createdAt, updatedAt
    """
    sql = """
    INSERT INTO sparepartforecast_tuht (
        sparepartid, centerid, predictedusage, safetystock, reorderpoint, 
        forecastedby, forecastconfidence, forecastdate, status, isactive, createdat
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, now(), 'PENDING', true, now())
    """
    return await execute(
        sql, spare_part_id, center_id, predicted_usage, safety_stock, reorder_point, 
        forecasted_by, confidence
    )
