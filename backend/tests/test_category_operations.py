#!/usr/bin/env python3
"""Test Category model operations with PostgreSQL."""

import asyncio
from app.database.base import async_session
from app.models.category import Category
from sqlalchemy import select

async def test_category_operations():
    """Test Category model operations with PostgreSQL."""
    print("Testing Category operations with PostgreSQL...")
    
    try:
        async with async_session() as session:
            # Create a test category
            category = Category(
                name='Test Category',
                description='Test category for PostgreSQL verification',
                color='#FF5733'
            )
            session.add(category)
            await session.commit()
            await session.refresh(category)
            
            print(f'Created category: {category.name} (ID: {category.id})')
            
            # Query it back
            result = await session.execute(select(Category))
            categories = result.scalars().all()
            
            print(f'Total categories in database: {len(categories)}')
            for cat in categories:
                print(f'  - {cat.name} (Color: {cat.color}, Active: {cat.is_active})')
            
            print('✅ PostgreSQL Category operations working correctly!')
            return True
            
    except Exception as e:
        print(f'❌ Error: {e}')
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_category_operations())
    if success:
        print('\n✅ PostgreSQL Category test completed successfully!')
    else:
        print('\n❌ PostgreSQL Category test failed!')