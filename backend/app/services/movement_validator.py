"""
Movement Validation Service for enforcing business rules and validating movement operations.

Provides comprehensive validation for all types of item movements including:
- Business rule enforcement
- Inventory constraint validation  
- Location hierarchy validation
- Quantity validation
- Conflict prevention
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, func, and_, or_
from decimal import Decimal
import logging

from app.models.item import Item
from app.models.location import Location
from app.models.inventory import Inventory
from app.models.item_movement_history import ItemMovementHistory
from app.schemas.movement_history import MovementHistoryCreate
from app.schemas.inventory import InventoryCreate

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Custom exception for movement validation errors."""
    
    def __init__(self, message: str, error_code: str = "VALIDATION_ERROR", details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)


class MovementValidationResult:
    """Result of movement validation with detailed information."""
    
    def __init__(
        self, 
        is_valid: bool, 
        errors: List[str] = None, 
        warnings: List[str] = None,
        business_rules_applied: List[str] = None,
        validation_metadata: Optional[Dict[str, Any]] = None
    ):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
        self.business_rules_applied = business_rules_applied or []
        self.validation_metadata = validation_metadata or {}
    
    def add_error(self, error: str) -> None:
        """Add a validation error."""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str) -> None:
        """Add a validation warning."""
        self.warnings.append(warning)
    
    def add_business_rule(self, rule: str) -> None:
        """Add applied business rule."""
        self.business_rules_applied.append(rule)


class MovementValidator:
    """Service for validating movement operations and enforcing business rules."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.business_rules = self._initialize_business_rules()

    def _initialize_business_rules(self) -> Dict[str, Dict[str, Any]]:
        """Initialize business rules configuration."""
        return {
            "max_concurrent_movements": {
                "enabled": True,
                "limit": 100,
                "description": "Maximum concurrent movements per item per hour"
            },
            "location_capacity_check": {
                "enabled": True,
                "enforce_hard_limits": False,
                "description": "Check location capacity constraints"
            },
            "item_status_constraints": {
                "enabled": True,
                "blocked_statuses": ["disposed", "sold", "lost"],
                "description": "Prevent movement of items with blocked statuses"
            },
            "quantity_consistency": {
                "enabled": True,
                "allow_negative_inventory": False,
                "description": "Ensure quantity consistency in movements"
            },
            "location_hierarchy_validation": {
                "enabled": True,
                "enforce_depth_limits": True,
                "max_depth": 4,
                "description": "Validate location hierarchy constraints"
            },
            "duplicate_movement_prevention": {
                "enabled": True,
                "time_window_minutes": 5,
                "description": "Prevent duplicate movements within time window"
            },
            "value_tracking": {
                "enabled": True,
                "require_value_for_high_quantity": True,
                "high_quantity_threshold": 10,
                "description": "Track estimated values for movements"
            }
        }

    async def validate_movement_create(
        self, 
        movement_data: MovementHistoryCreate,
        enforce_strict_validation: bool = True
    ) -> MovementValidationResult:
        """
        Validate a new movement creation.
        
        Args:
            movement_data: Movement data to validate
            enforce_strict_validation: Whether to enforce strict business rules
            
        Returns:
            Validation result with errors, warnings, and applied rules
        """
        result = MovementValidationResult(is_valid=True)
        
        try:
            # Basic data validation
            await self._validate_basic_movement_data(movement_data, result)
            
            # Entity existence validation
            await self._validate_entities_exist(movement_data, result)
            
            # Business rules validation
            if enforce_strict_validation:
                await self._validate_business_rules(movement_data, result)
            
            # Movement type specific validation
            await self._validate_movement_type_rules(movement_data, result)
            
            # Quantity and inventory validation
            await self._validate_quantity_constraints(movement_data, result)
            
            # Location validation
            await self._validate_location_constraints(movement_data, result)
            
            # Duplicate detection
            await self._validate_duplicate_prevention(movement_data, result)
            
            # Performance and conflict validation
            await self._validate_performance_constraints(movement_data, result)
            
        except Exception as e:
            logger.error(f"Validation error: {str(e)}")
            result.add_error(f"Validation system error: {str(e)}")
        
        return result

    async def validate_bulk_movement(
        self, 
        movements: List[MovementHistoryCreate],
        enforce_atomic_validation: bool = True
    ) -> Tuple[MovementValidationResult, List[MovementValidationResult]]:
        """
        Validate bulk movement operations.
        
        Args:
            movements: List of movements to validate
            enforce_atomic_validation: If True, all movements must be valid
            
        Returns:
            Tuple of (overall_result, individual_results)
        """
        overall_result = MovementValidationResult(is_valid=True)
        individual_results = []
        
        if not movements:
            overall_result.add_error("No movements provided for bulk validation")
            return overall_result, individual_results
        
        # Validate each movement individually
        for i, movement in enumerate(movements):
            individual_result = await self.validate_movement_create(movement)
            individual_results.append(individual_result)
            
            if not individual_result.is_valid:
                overall_result.add_error(f"Movement {i+1} failed validation: {'; '.join(individual_result.errors)}")
                if enforce_atomic_validation:
                    overall_result.is_valid = False
        
        # Cross-movement validation
        await self._validate_bulk_movement_conflicts(movements, overall_result)
        
        return overall_result, individual_results

    async def _validate_basic_movement_data(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Validate basic movement data integrity."""
        
        # Item ID validation
        if not movement_data.item_id or movement_data.item_id <= 0:
            result.add_error("Valid item ID is required")
        
        # Movement type validation
        valid_movement_types = ["create", "move", "adjust", "split", "merge", "dispose"]
        if not movement_data.movement_type or movement_data.movement_type not in valid_movement_types:
            result.add_error(f"Movement type must be one of: {', '.join(valid_movement_types)}")
        
        # Quantity validation
        if movement_data.quantity_moved is not None and movement_data.quantity_moved < 0:
            result.add_error("Quantity moved cannot be negative")
        
        # Location validation for movement types
        if movement_data.movement_type == "move":
            if not movement_data.from_location_id or not movement_data.to_location_id:
                result.add_error("Move operations require both from_location_id and to_location_id")
            if movement_data.from_location_id == movement_data.to_location_id:
                result.add_error("Cannot move item to the same location")
        
        elif movement_data.movement_type == "create":
            if not movement_data.to_location_id:
                result.add_error("Create operations require to_location_id")
            if movement_data.from_location_id:
                result.add_warning("Create operations should not have from_location_id")
        
        # Quantity consistency validation
        if (movement_data.quantity_before is not None and 
            movement_data.quantity_after is not None and
            movement_data.quantity_moved is not None):
            
            expected_change = movement_data.quantity_after - movement_data.quantity_before
            if abs(expected_change) != movement_data.quantity_moved:
                result.add_error("Quantity moved does not match before/after difference")

    async def _validate_entities_exist(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Validate that referenced entities exist in the database."""
        
        # Validate item exists
        item_result = await self.db.execute(
            select(Item).where(Item.id == movement_data.item_id)
        )
        item = item_result.scalar_one_or_none()
        if not item:
            result.add_error(f"Item with ID {movement_data.item_id} does not exist")
            return
        
        # Store item for further validation
        result.validation_metadata["item"] = item
        
        # Validate from_location exists
        if movement_data.from_location_id:
            from_location_result = await self.db.execute(
                select(Location).where(Location.id == movement_data.from_location_id)
            )
            from_location = from_location_result.scalar_one_or_none()
            if not from_location:
                result.add_error(f"From location with ID {movement_data.from_location_id} does not exist")
            else:
                result.validation_metadata["from_location"] = from_location
        
        # Validate to_location exists
        if movement_data.to_location_id:
            to_location_result = await self.db.execute(
                select(Location).where(Location.id == movement_data.to_location_id)
            )
            to_location = to_location_result.scalar_one_or_none()
            if not to_location:
                result.add_error(f"To location with ID {movement_data.to_location_id} does not exist")
            else:
                result.validation_metadata["to_location"] = to_location

    async def _validate_business_rules(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Apply and validate business rules."""
        
        item = result.validation_metadata.get("item")
        if not item:
            return
        
        # Item status constraints
        if self.business_rules["item_status_constraints"]["enabled"]:
            blocked_statuses = self.business_rules["item_status_constraints"]["blocked_statuses"]
            if item.status in blocked_statuses:
                result.add_error(f"Cannot move item with status: {item.status}")
            result.add_business_rule("item_status_constraints")
        
        # Concurrent movements limit
        if self.business_rules["max_concurrent_movements"]["enabled"]:
            limit = self.business_rules["max_concurrent_movements"]["limit"]
            hour_ago = datetime.now() - timedelta(hours=1)
            
            recent_movements_result = await self.db.execute(
                select(func.count()).where(
                    and_(
                        ItemMovementHistory.item_id == movement_data.item_id,
                        ItemMovementHistory.created_at >= hour_ago
                    )
                )
            )
            recent_count = recent_movements_result.scalar()
            
            if recent_count >= limit:
                result.add_error(f"Too many movements for this item in the last hour: {recent_count}/{limit}")
            result.add_business_rule("max_concurrent_movements")

    async def _validate_movement_type_rules(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Validate rules specific to movement types."""
        
        if movement_data.movement_type == "create":
            # For create operations, verify item doesn't already exist in inventory
            existing_inventory_result = await self.db.execute(
                select(Inventory).where(Inventory.item_id == movement_data.item_id)
            )
            existing_inventory = existing_inventory_result.scalars().all()
            
            if existing_inventory:
                result.add_warning("Item already exists in inventory - this may create duplicates")
        
        elif movement_data.movement_type == "move":
            # For move operations, verify item exists in from_location
            if movement_data.from_location_id:
                from_inventory_result = await self.db.execute(
                    select(Inventory).where(
                        and_(
                            Inventory.item_id == movement_data.item_id,
                            Inventory.location_id == movement_data.from_location_id
                        )
                    )
                )
                from_inventory = from_inventory_result.scalar_one_or_none()
                
                if not from_inventory:
                    result.add_error("Item not found in source location")
                elif movement_data.quantity_moved and from_inventory.quantity < movement_data.quantity_moved:
                    result.add_error(f"Insufficient quantity in source location: {from_inventory.quantity} < {movement_data.quantity_moved}")

    async def _validate_quantity_constraints(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Validate quantity-related constraints."""
        
        if not self.business_rules["quantity_consistency"]["enabled"]:
            return
        
        # Negative inventory prevention
        if not self.business_rules["quantity_consistency"]["allow_negative_inventory"]:
            if movement_data.from_location_id and movement_data.quantity_moved:
                current_inventory_result = await self.db.execute(
                    select(Inventory.quantity).where(
                        and_(
                            Inventory.item_id == movement_data.item_id,
                            Inventory.location_id == movement_data.from_location_id
                        )
                    )
                )
                current_quantity = current_inventory_result.scalar() or 0
                
                if current_quantity < movement_data.quantity_moved:
                    result.add_error(f"Movement would create negative inventory: {current_quantity} - {movement_data.quantity_moved}")
        
        result.add_business_rule("quantity_consistency")

    async def _validate_location_constraints(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Validate location-specific constraints."""
        
        if not self.business_rules["location_hierarchy_validation"]["enabled"]:
            return
        
        to_location = result.validation_metadata.get("to_location")
        if to_location and self.business_rules["location_hierarchy_validation"]["enforce_depth_limits"]:
            max_depth = self.business_rules["location_hierarchy_validation"]["max_depth"]
            if to_location.depth > max_depth:
                result.add_error(f"Location depth exceeds maximum allowed: {to_location.depth} > {max_depth}")
        
        result.add_business_rule("location_hierarchy_validation")

    async def _validate_duplicate_prevention(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Prevent duplicate movements within time window."""
        
        if not self.business_rules["duplicate_movement_prevention"]["enabled"]:
            return
        
        time_window = self.business_rules["duplicate_movement_prevention"]["time_window_minutes"]
        cutoff_time = datetime.now() - timedelta(minutes=time_window)
        
        # Look for similar movements in the time window
        similar_movements_result = await self.db.execute(
            select(ItemMovementHistory).where(
                and_(
                    ItemMovementHistory.item_id == movement_data.item_id,
                    ItemMovementHistory.movement_type == movement_data.movement_type,
                    ItemMovementHistory.from_location_id == movement_data.from_location_id,
                    ItemMovementHistory.to_location_id == movement_data.to_location_id,
                    ItemMovementHistory.quantity_moved == movement_data.quantity_moved,
                    ItemMovementHistory.created_at >= cutoff_time
                )
            )
        )
        similar_movements = similar_movements_result.scalars().all()
        
        if similar_movements:
            result.add_warning(f"Similar movement detected within {time_window} minutes - possible duplicate")
        
        result.add_business_rule("duplicate_movement_prevention")

    async def _validate_performance_constraints(
        self, 
        movement_data: MovementHistoryCreate, 
        result: MovementValidationResult
    ) -> None:
        """Validate performance-related constraints."""
        
        # Check for high-frequency movements that might indicate system issues
        recent_movements_result = await self.db.execute(
            select(func.count()).where(
                and_(
                    ItemMovementHistory.item_id == movement_data.item_id,
                    ItemMovementHistory.created_at >= datetime.now() - timedelta(minutes=1)
                )
            )
        )
        recent_count = recent_movements_result.scalar()
        
        if recent_count > 10:
            result.add_warning("High frequency movements detected - possible system issue")

    async def _validate_bulk_movement_conflicts(
        self, 
        movements: List[MovementHistoryCreate], 
        result: MovementValidationResult
    ) -> None:
        """Validate conflicts between movements in a bulk operation."""
        
        # Group movements by item and location for conflict detection
        item_location_movements = {}
        
        for i, movement in enumerate(movements):
            key = (movement.item_id, movement.from_location_id, movement.to_location_id)
            if key not in item_location_movements:
                item_location_movements[key] = []
            item_location_movements[key].append((i, movement))
        
        # Check for conflicting movements
        for key, movement_list in item_location_movements.items():
            if len(movement_list) > 1:
                total_quantity = sum(m[1].quantity_moved or 0 for m in movement_list)
                movement_indices = [str(m[0] + 1) for m in movement_list]
                
                result.add_warning(
                    f"Multiple movements for same item/location combination "
                    f"(movements {', '.join(movement_indices)}): total quantity {total_quantity}"
                )

    async def get_validation_report(self, item_id: Optional[int] = None) -> Dict[str, Any]:
        """Generate a comprehensive validation report."""
        
        report = {
            "business_rules": self.business_rules,
            "validation_statistics": {},
            "recent_validation_failures": [],
            "system_health": {}
        }
        
        # Get validation statistics
        base_query = select(ItemMovementHistory)
        if item_id:
            base_query = base_query.where(ItemMovementHistory.item_id == item_id)
        
        # Count movements by type
        movement_stats_result = await self.db.execute(
            select(
                ItemMovementHistory.movement_type,
                func.count().label('count')
            ).group_by(ItemMovementHistory.movement_type)
        )
        
        movement_stats = {}
        for row in movement_stats_result:
            movement_stats[row.movement_type] = row.count
        
        report["validation_statistics"]["movement_types"] = movement_stats
        
        # System health checks
        recent_failures = await self.db.execute(
            select(func.count()).where(
                ItemMovementHistory.created_at >= datetime.now() - timedelta(hours=24)
            )
        )
        
        report["system_health"]["movements_last_24h"] = recent_failures.scalar()
        report["system_health"]["validation_rules_active"] = sum(
            1 for rule in self.business_rules.values() if rule.get("enabled", False)
        )
        
        return report

    async def apply_business_rule_overrides(self, overrides: Dict[str, Any]) -> None:
        """Apply temporary business rule overrides."""
        
        for rule_name, override_config in overrides.items():
            if rule_name in self.business_rules:
                self.business_rules[rule_name].update(override_config)
                logger.info(f"Applied business rule override for {rule_name}: {override_config}")