import logging
import psycopg
from psycopg_pool import ConnectionPool
from config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()

_pool: ConnectionPool | None = None

def get_db_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        conninfo = (
            f"host={settings.db_host} "
            f"port={settings.db_port} "
            f"dbname={settings.db_name} "
            f"user={settings.db_user} "
            f"password={settings.db_password} "
            f"sslmode={settings.db_sslmode}"
        )
        _pool = ConnectionPool(
            conninfo=conninfo,
            min_size=1,
            max_size=10,
            timeout=15.0,
            max_idle=300.0,
            open=False
        )
        _pool.open()
        logger.info("PostgreSQL connection pool initialized.")
    return _pool

def init_vector_table():
    """Ensure vector extension and vector_store table exist matching Spring AI schema."""
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # Create vector_store table if not present (identical to Spring AI schema)
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {settings.vector_table} (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    content TEXT,
                    metadata JSON,
                    embedding VECTOR({settings.vector_dimension})
                );
            """)
            
            # Index creation (optional, Spring AI configured index-type=NONE)
            try:
                cur.execute(f"""
                    CREATE INDEX IF NOT EXISTS idx_{settings.vector_table}_hnsw
                    ON {settings.vector_table} 
                    USING hnsw (embedding vector_cosine_ops);
                """)
            except Exception as e:
                logger.info(f"Index creation note: {e}")
            conn.commit()
            logger.info("Vector database schema verified successfully.")

def check_db_health() -> bool:
    try:
        pool = get_db_pool()
        with pool.connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                return cur.fetchone()[0] == 1
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

def close_db_pool():
    global _pool
    if _pool is not None:
        try:
            _pool.close()
            logger.info("PostgreSQL connection pool closed.")
        except Exception:
            pass
        _pool = None

import atexit
atexit.register(close_db_pool)
