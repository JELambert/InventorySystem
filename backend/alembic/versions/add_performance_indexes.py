"""Add performance indexes for optimized queries

Revision ID: add_performance_indexes
Revises: ad4445d5f714
Create Date: 2025-07-03 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_performance_indexes'
down_revision: Union[str, None] = 'ad4445d5f714'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes for frequently queried columns."""
    
    # Items table indexes
    op.create_index('ix_items_name', 'items', ['name'])
    op.create_index('ix_items_created_at', 'items', ['created_at'])
    op.create_index('ix_items_item_type', 'items', ['item_type'])
    op.create_index('ix_items_status', 'items', ['status'])
    op.create_index('ix_items_brand', 'items', ['brand'])
    op.create_index('ix_items_barcode', 'items', ['barcode'])
    
    # Inventory table composite index
    op.create_index('ix_inventory_item_location', 'inventory', ['item_id', 'location_id'])
    
    # Item movement history indexes
    op.create_index('ix_item_movement_history_timestamp', 'item_movement_history', ['created_at'])
    op.create_index('ix_item_movement_history_item_timestamp', 'item_movement_history', ['item_id', 'created_at'])
    
    # Category indexes
    op.create_index('ix_categories_name', 'categories', ['name'])
    op.create_index('ix_categories_is_active', 'categories', ['is_active'])


def downgrade() -> None:
    """Remove performance indexes."""
    
    # Remove category indexes
    op.drop_index('ix_categories_is_active', 'categories')
    op.drop_index('ix_categories_name', 'categories')
    
    # Remove item movement history indexes
    op.drop_index('ix_item_movement_history_item_timestamp', 'item_movement_history')
    op.drop_index('ix_item_movement_history_timestamp', 'item_movement_history')
    
    # Remove inventory composite index
    op.drop_index('ix_inventory_item_location', 'inventory')
    
    # Remove items table indexes
    op.drop_index('ix_items_barcode', 'items')
    op.drop_index('ix_items_brand', 'items')
    op.drop_index('ix_items_status', 'items')
    op.drop_index('ix_items_item_type', 'items')
    op.drop_index('ix_items_created_at', 'items')
    op.drop_index('ix_items_name', 'items')