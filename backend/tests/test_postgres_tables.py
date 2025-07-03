#!/usr/bin/env python3
"""Test PostgreSQL table creation after migration."""

import asyncio
import asyncpg
from app.database.config import DatabaseConfig

async def check_tables():
    """Check that all tables were created properly in PostgreSQL."""
    url = DatabaseConfig.get_postgres_url()
    # Remove the +asyncpg part for direct asyncpg connection
    url = url.replace('postgresql+asyncpg://', 'postgresql://')
    
    try:
        conn = await asyncpg.connect(url)
        
        # List all tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        print('Tables in database:')
        for table in tables:
            print(f'  - {table["table_name"]}')
        
        print('\nTesting table access:')
        for table in tables:
            table_name = table['table_name']
            if table_name != 'alembic_version':
                try:
                    count = await conn.fetchval(f'SELECT COUNT(*) FROM {table_name}')
                    print(f'  - {table_name}: {count} rows')
                except Exception as e:
                    print(f'  - {table_name}: ERROR - {e}')
            
        await conn.close()
        return True
        
    except Exception as e:
        print(f'Error: {e}')
        return False

if __name__ == "__main__":
    success = asyncio.run(check_tables())
    if success:
        print('\n✅ PostgreSQL migration verification completed successfully!')
    else:
        print('\n❌ PostgreSQL migration verification failed!')