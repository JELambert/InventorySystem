#!/usr/bin/env python3
"""
Script to set up PostgreSQL database for the Home Inventory System.
"""

import asyncio
import sys
import os

# Add the parent directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg
from app.database.config import DatabaseConfig

async def create_database_if_not_exists():
    """Create the inventory_system database if it doesn't exist."""
    
    # Connection parameters
    host = os.getenv("POSTGRES_HOST", "192.168.68.88")
    port = int(os.getenv("POSTGRES_PORT", "5432"))
    username = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "vaultlock1")
    database = os.getenv("POSTGRES_DB", "inventory_system")
    
    print(f"🔧 Setting up PostgreSQL database: {database}")
    print(f"📍 Host: {host}:{port}")
    print(f"👤 User: {username}")
    
    try:
        # Connect to PostgreSQL server (to default postgres database)
        print("\n⏳ Connecting to PostgreSQL server...")
        conn = await asyncpg.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database="postgres"  # Connect to default database first
        )
        
        print("✅ Connected to PostgreSQL server")
        
        # Check if database exists
        result = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1", database
        )
        
        if result:
            print(f"✅ Database '{database}' already exists")
        else:
            print(f"⏳ Creating database '{database}'...")
            await conn.execute(f'CREATE DATABASE "{database}"')
            print(f"✅ Database '{database}' created successfully")
        
        await conn.close()
        
        # Test connection to the target database
        print(f"\n⏳ Testing connection to '{database}' database...")
        test_conn = await asyncpg.connect(
            host=host,
            port=port,
            user=username,
            password=password,
            database=database
        )
        
        # Test basic query
        version = await test_conn.fetchval("SELECT version()")
        print(f"✅ Connected to '{database}' database successfully")
        print(f"📊 PostgreSQL version: {version[:50]}...")
        
        await test_conn.close()
        
        return True
        
    except asyncpg.InvalidCatalogNameError:
        print(f"❌ Database '{database}' does not exist and could not be created")
        return False
    except asyncpg.InvalidPasswordError:
        print(f"❌ Authentication failed for user '{username}'")
        return False
    except asyncpg.CannotConnectNowError:
        print(f"❌ Cannot connect to PostgreSQL server at {host}:{port}")
        return False
    except Exception as e:
        print(f"❌ Error setting up database: {e}")
        return False

async def test_sqlalchemy_connection():
    """Test SQLAlchemy connection to PostgreSQL."""
    print("\n🔧 Testing SQLAlchemy connection...")
    
    try:
        from app.database.base import engine, async_session
        from sqlalchemy import text
        
        # Test engine connection
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            print(f"✅ SQLAlchemy engine connection successful (test query: {test_value})")
        
        # Test session creation
        async with async_session() as session:
            result = await session.execute(text("SELECT current_database()"))
            db_name = result.scalar()
            print(f"✅ SQLAlchemy session creation successful (database: {db_name})")
        
        return True
        
    except Exception as e:
        print(f"❌ SQLAlchemy connection failed: {e}")
        return False

async def main():
    """Main setup execution."""
    print("🐘 PostgreSQL Database Setup - Home Inventory System")
    print("=" * 60)
    
    # Step 1: Create database if needed
    db_success = await create_database_if_not_exists()
    if not db_success:
        print("\n❌ Database setup failed")
        sys.exit(1)
    
    # Step 2: Test SQLAlchemy connection
    sqlalchemy_success = await test_sqlalchemy_connection()
    if not sqlalchemy_success:
        print("\n❌ SQLAlchemy connection test failed")
        sys.exit(1)
    
    print("\n🎉 PostgreSQL database setup completed successfully!")
    print("\nNext steps:")
    print("1. Run Alembic migrations: python scripts/manage_migrations.py apply")
    print("2. Verify with: python scripts/verify_alembic_migrations.py")

if __name__ == "__main__":
    asyncio.run(main())