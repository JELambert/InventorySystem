#!/usr/bin/env python3
"""Test Location model operations with PostgreSQL."""

import asyncio
from app.database.base import async_session
from app.models.location import Location, LocationType
from sqlalchemy import select

async def test_location_operations():
    """Test Location model operations with PostgreSQL."""
    print("Testing Location operations with PostgreSQL...")
    
    async with async_session() as session:
        # Create a test location
        house = Location(
            name='Test House',
            description='Test house for PostgreSQL verification',
            location_type=LocationType.HOUSE
        )
        session.add(house)
        await session.commit()
        await session.refresh(house)
        
        print(f'Created location: {house.name} (ID: {house.id})')
        
        # Query it back
        result = await session.execute(select(Location))
        locations = result.scalars().all()
        
        print(f'Total locations in database: {len(locations)}')
        for loc in locations:
            print(f'  - {loc.name} ({loc.location_type.value})')
        
        print('✅ PostgreSQL Location operations working correctly!')
        return True

if __name__ == "__main__":
    success = asyncio.run(test_location_operations())
    if success:
        print('\n✅ PostgreSQL Location test completed successfully!')
    else:
        print('\n❌ PostgreSQL Location test failed!')