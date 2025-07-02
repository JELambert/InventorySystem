"""
Semantic search API endpoints for the Home Inventory System.

Provides advanced search capabilities using Weaviate vector database
for natural language queries and similarity-based item discovery.
"""

import time
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload

from app.database.base import get_session
from app.models import Item, Location, Category, Inventory
from app.services.weaviate_service import get_weaviate_service, WeaviateService
from app.schemas import (
    SemanticSearchRequest, HybridSearchRequest, SemanticSearchResult,
    SemanticSearchResponse, SimilarItemsRequest, SimilarItemsResponse,
    WeaviateHealthResponse, EmbeddingBatchRequest, EmbeddingBatchResponse,
    ItemResponse, ItemSearch
)
from app.core.logging import get_logger

logger = get_logger("search_api")

router = APIRouter(prefix="/search", tags=["semantic_search"])


def _convert_item_to_response(item: Item) -> ItemResponse:
    """Convert Item model to ItemResponse schema."""
    # Get location names from inventory entries
    location_names = []
    if hasattr(item, 'inventory_entries') and item.inventory_entries:
        location_names = [entry.location.name for entry in item.inventory_entries if entry.location]
    
    # Get category name
    category_name = item.category.name if item.category else None
    
    return ItemResponse(
        id=item.id,
        name=item.name,
        description=item.description,
        item_type=item.item_type,
        condition=item.condition,
        status=item.status,
        brand=item.brand,
        model=item.model,
        serial_number=item.serial_number,
        barcode=item.barcode,
        purchase_price=item.purchase_price,
        current_value=item.current_value,
        purchase_date=item.purchase_date,
        warranty_expiry=item.warranty_expiry,
        weight=item.weight,
        dimensions=item.dimensions,
        color=item.color,
        category_id=item.category_id,
        notes=item.notes,
        tags=item.tags,
        is_active=item.is_active,
        version=item.version,
        created_at=item.created_at,
        updated_at=item.updated_at,
        category={"id": item.category.id, "name": item.category.name} if item.category else None,
        inventory_entries=[
            {
                "id": entry.id,
                "location_id": entry.location_id,
                "quantity": entry.quantity,
                "updated_at": entry.updated_at,
                "location": {"id": entry.location.id, "name": entry.location.name} if entry.location else None
            }
            for entry in (item.inventory_entries or [])
        ]
    )


@router.get("/health", response_model=WeaviateHealthResponse)
async def get_search_health(
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Get health status of semantic search services."""
    try:
        stats = await weaviate_service.get_stats()
        
        return WeaviateHealthResponse(
            status=stats.get("status", "unknown"),
            item_count=stats.get("item_count", 0),
            embedding_model=stats.get("embedding_model", ""),
            weaviate_url=stats.get("weaviate_url", ""),
            last_sync=None  # TODO: Implement sync tracking
        )
        
    except Exception as e:
        logger.error(f"Failed to get search health: {e}")
        raise HTTPException(status_code=500, detail="Failed to get search health status")


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(
    request: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Perform semantic search using natural language queries."""
    start_time = time.time()
    
    try:
        # Perform semantic search in Weaviate
        weaviate_results = await weaviate_service.semantic_search(
            query=request.query,
            limit=request.limit,
            certainty=request.certainty
        )
        
        if not weaviate_results:
            # Return empty results if no semantic matches
            return SemanticSearchResponse(
                query=request.query,
                results=[],
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                semantic_enabled=True,
                fallback_used=False
            )
        
        # Get PostgreSQL items for the results
        item_ids = [result.postgres_id for result in weaviate_results]
        
        query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.inventory_entries).selectinload(Inventory.location)
        ).where(
            and_(
                Item.id.in_(item_ids),
                Item.is_active == True
            )
        )
        
        result = await session.execute(query)
        items = result.scalars().all()
        
        # Create item lookup for ordering
        item_lookup = {item.id: item for item in items}
        
        # Build response results maintaining order from Weaviate
        search_results = []
        for weaviate_result in weaviate_results:
            if weaviate_result.postgres_id in item_lookup:
                item = item_lookup[weaviate_result.postgres_id]
                item_response = _convert_item_to_response(item)
                
                search_results.append(SemanticSearchResult(
                    item=item_response,
                    score=weaviate_result.score if request.include_scores else 0.0,
                    match_type="semantic"
                ))
        
        search_time = (time.time() - start_time) * 1000
        
        logger.info(f"Semantic search for '{request.query}' returned {len(search_results)} results in {search_time:.1f}ms")
        
        return SemanticSearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=search_time,
            semantic_enabled=True,
            fallback_used=False
        )
        
    except Exception as e:
        logger.error(f"Semantic search failed for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail="Semantic search failed")


@router.post("/hybrid", response_model=SemanticSearchResponse)  
async def hybrid_search(
    request: HybridSearchRequest,
    session: AsyncSession = Depends(get_session),
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Perform hybrid search combining semantic and traditional search."""
    start_time = time.time()
    fallback_used = False
    
    try:
        # Try semantic search first
        semantic_results = []
        if await weaviate_service.health_check():
            weaviate_results = await weaviate_service.semantic_search(
                query=request.query,
                limit=min(request.limit * 2, 100),  # Get more candidates for filtering
                certainty=request.certainty
            )
            semantic_results = [result.postgres_id for result in weaviate_results]
        else:
            fallback_used = True
            logger.warning("Weaviate unavailable, using traditional search fallback")
        
        # Build PostgreSQL query
        query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.inventory_entries).selectinload(Inventory.location)
        ).where(Item.is_active == True)
        
        # Apply semantic filtering if available
        if semantic_results:
            query = query.where(Item.id.in_(semantic_results))
        elif not fallback_used:
            # No semantic results, but Weaviate was available
            return SemanticSearchResponse(
                query=request.query,
                results=[],
                total_results=0,
                search_time_ms=(time.time() - start_time) * 1000,
                semantic_enabled=True,
                fallback_used=False
            )
        
        # Apply traditional filters if provided
        if request.filters:
            filters = request.filters
            
            # Text search fallback
            if fallback_used and request.query:
                search_term = f"%{request.query}%"
                query = query.where(
                    or_(
                        Item.name.ilike(search_term),
                        Item.description.ilike(search_term),
                        Item.notes.ilike(search_term),
                        Item.brand.ilike(search_term),
                        Item.model.ilike(search_term),
                        Item.tags.ilike(search_term)
                    )
                )
            
            # Apply other filters
            if filters.item_type:
                query = query.where(Item.item_type == filters.item_type)
            if filters.condition:
                query = query.where(Item.condition == filters.condition)
            if filters.status:
                query = query.where(Item.status == filters.status)
            if filters.category_id:
                query = query.where(Item.category_id == filters.category_id)
            if filters.brand:
                query = query.where(Item.brand.ilike(f"%{filters.brand}%"))
            if filters.min_value is not None:
                query = query.where(Item.current_value >= filters.min_value)
            if filters.max_value is not None:
                query = query.where(Item.current_value <= filters.max_value)
        
        # Execute query with limit
        query = query.limit(request.limit)
        result = await session.execute(query)
        items = result.scalars().all()
        
        # Build response results
        search_results = []
        for item in items:
            item_response = _convert_item_to_response(item)
            
            # Calculate score based on semantic results if available
            score = 0.0
            if semantic_results:
                try:
                    # Find the score from Weaviate results
                    weaviate_result = next(
                        (r for r in weaviate_results if r.postgres_id == item.id), 
                        None
                    )
                    score = weaviate_result.score if weaviate_result else 0.0
                except:
                    score = 0.0
            
            search_results.append(SemanticSearchResult(
                item=item_response,
                score=score,
                match_type="hybrid" if semantic_results else "traditional"
            ))
        
        search_time = (time.time() - start_time) * 1000
        
        logger.info(f"Hybrid search for '{request.query}' returned {len(search_results)} results in {search_time:.1f}ms")
        
        return SemanticSearchResponse(
            query=request.query,
            results=search_results,
            total_results=len(search_results),
            search_time_ms=search_time,
            semantic_enabled=not fallback_used,
            fallback_used=fallback_used
        )
        
    except Exception as e:
        logger.error(f"Hybrid search failed for query '{request.query}': {e}")
        raise HTTPException(status_code=500, detail="Hybrid search failed")


@router.get("/similar/{item_id}", response_model=SimilarItemsResponse)
async def get_similar_items(
    item_id: int,
    limit: int = Query(5, ge=1, le=20, description="Maximum number of similar items"),
    session: AsyncSession = Depends(get_session),
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Find items similar to the specified item."""
    try:
        # Get the source item
        query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.inventory_entries).selectinload(Inventory.location)
        ).where(
            and_(Item.id == item_id, Item.is_active == True)
        )
        
        result = await session.execute(query)
        source_item = result.scalar_one_or_none()
        
        if not source_item:
            raise HTTPException(status_code=404, detail=f"Item {item_id} not found")
        
        # Find similar items using Weaviate
        similar_results = []
        if await weaviate_service.health_check():
            weaviate_results = await weaviate_service.get_similar_items(item_id, limit)
            
            if weaviate_results:
                # Get the similar items from PostgreSQL
                similar_ids = [result.postgres_id for result in weaviate_results]
                
                similar_query = select(Item).options(
                    selectinload(Item.category),
                    selectinload(Item.inventory_entries).selectinload(Inventory.location)
                ).where(
                    and_(
                        Item.id.in_(similar_ids),
                        Item.is_active == True
                    )
                )
                
                similar_result = await session.execute(similar_query)
                similar_items = similar_result.scalars().all()
                
                # Create lookup and maintain order
                item_lookup = {item.id: item for item in similar_items}
                
                for weaviate_result in weaviate_results:
                    if weaviate_result.postgres_id in item_lookup:
                        item = item_lookup[weaviate_result.postgres_id]
                        item_response = _convert_item_to_response(item)
                        
                        similar_results.append(SemanticSearchResult(
                            item=item_response,
                            score=weaviate_result.score,
                            match_type="similarity"
                        ))
        
        source_item_response = _convert_item_to_response(source_item)
        
        logger.info(f"Found {len(similar_results)} similar items for item {item_id}")
        
        return SimilarItemsResponse(
            source_item=source_item_response,
            similar_items=similar_results,
            total_found=len(similar_results)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to find similar items for {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to find similar items")


@router.post("/embeddings/batch", response_model=EmbeddingBatchResponse)
async def create_batch_embeddings(
    request: EmbeddingBatchRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    weaviate_service: WeaviateService = Depends(get_weaviate_service)
):
    """Create embeddings for multiple items in batch."""
    try:
        # Get items from database
        query = select(Item).options(
            selectinload(Item.category),
            selectinload(Item.inventory_entries).selectinload(Inventory.location)
        ).where(
            and_(
                Item.id.in_(request.item_ids),
                Item.is_active == True
            )
        )
        
        result = await session.execute(query)
        items = result.scalars().all()
        
        if not items:
            return EmbeddingBatchResponse(
                success_count=0,
                failed_count=0,
                skipped_count=len(request.item_ids),
                total_processed=len(request.item_ids),
                errors=["No valid items found"]
            )
        
        # Prepare items data for batch processing
        items_data = []
        for item in items:
            category_name = item.category.name if item.category else ""
            location_names = [
                entry.location.name for entry in (item.inventory_entries or [])
                if entry.location
            ]
            items_data.append((item, category_name, location_names))
        
        # Process embeddings
        stats = await weaviate_service.batch_create_embeddings(items_data)
        
        logger.info(f"Batch embedding creation completed: {stats}")
        
        return EmbeddingBatchResponse(
            success_count=stats.get("success", 0),
            failed_count=stats.get("failed", 0),
            skipped_count=stats.get("skipped", 0),
            total_processed=len(items_data),
            errors=[]
        )
        
    except Exception as e:
        logger.error(f"Batch embedding creation failed: {e}")
        raise HTTPException(status_code=500, detail="Batch embedding creation failed")