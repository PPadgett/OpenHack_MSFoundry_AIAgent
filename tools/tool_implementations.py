"""
Tool implementations for Crust agent.
All tools are idempotent, immutable, and declarative.
"""

import os
import json
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import requests
from dataclasses import dataclass, asdict
from functools import wraps

# Configuration
PIZZA_API_URL = os.getenv("PIZZA_API_URL", "https://func-pizza-api-ceki46omdafoe.azurewebsites.net/")
REGISTRATION_API_URL = os.getenv("REGISTRATION_API_URL", "https://func-registration-api-ceki46omdafoe.azurewebsites.net/")
API_TIMEOUT = int(os.getenv("API_TIMEOUT_SECONDS", 30))
API_MAX_RETRIES = int(os.getenv("API_MAX_RETRIES", 3))
API_RETRY_BACKOFF = int(os.getenv("API_RETRY_BACKOFF_SECONDS", 2))

logger = logging.getLogger(__name__)


# ===== Data Classes (Immutable) =====
@dataclass(frozen=True)
class MenuItem:
    """Immutable menu item."""
    item_id: str
    name: str
    description: str
    price: float
    size: Optional[str]
    crust: Optional[str]
    available: bool


@dataclass(frozen=True)
class AllergenData:
    """Immutable allergen information."""
    item_id: str
    allergens: List[str]
    cross_contact_risk: bool
    contains_fda_big_nine: List[str]
    contains_eu_fourteen: List[str]
    preparation_notes: str


@dataclass(frozen=True)
class PriceCalculation:
    """Immutable price calculation."""
    order_id: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    delivery_fee: float
    total: float
    calculated_at: str


@dataclass(frozen=True)
class Order:
    """Immutable order object."""
    order_id: str
    version: int
    customer_id: str
    items: List[Dict[str, Any]]
    subtotal: float
    tax: float
    delivery_fee: float
    total: float
    fulfillment_type: str  # "pickup" | "delivery"
    fulfillment_address: Optional[str]
    fulfillment_time: str  # ISO 8601
    allergen_flags: List[str]
    status: str  # "pending_confirmation" | "confirmed" | "submitted"
    special_requests: Optional[str]
    created_at: str
    updated_at: str


class AllergenSeverity(Enum):
    """Allergen severity levels."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"
    ANAPHYLAXIS = "anaphylaxis"


# ===== Decorator: Idempotence & Retry Logic =====
def idempotent_get(max_retries=API_MAX_RETRIES):
    """Decorator for idempotent GET operations (safe to retry)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_retries):
                try:
                    result = func(*args, **kwargs)
                    logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    return result
                except requests.RequestException as e:
                    last_error = e
                    if attempt < max_retries - 1:
                        backoff = API_RETRY_BACKOFF * (2 ** attempt)
                        logger.warning(f"{func.__name__} failed; retrying in {backoff}s: {e}")
                        import time
                        time.sleep(backoff)
            logger.error(f"{func.__name__} failed after {max_retries} attempts: {last_error}")
            raise last_error
        return wrapper
    return decorator


def idempotent_post(func):
    """Decorator for idempotent POST operations (with idempotency key)."""
    @wraps(func)
    def wrapper(idempotency_key, *args, **kwargs):
        # Validate idempotency key format (UUID)
        try:
            uuid.UUID(idempotency_key)
        except ValueError:
            raise ValueError(f"Invalid idempotency key (must be UUID): {idempotency_key}")
        
        # Check idempotency store (cache) for prior result
        cache_key = f"post_idempotent:{func.__name__}:{idempotency_key}"
        # TODO: Implement cache lookup (Redis, Azure Cache)
        
        # Perform operation
        try:
            result = func(idempotency_key, *args, **kwargs)
            # TODO: Store result in idempotency cache with TTL
            logger.info(f"{func.__name__} succeeded with key {idempotency_key}")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise
    
    return wrapper


# ===== Tool Implementations =====

class MenuLookup:
    """GET /api/menu - Retrieve menu items (idempotent)."""
    
    @staticmethod
    @idempotent_get()
    def lookup(size: Optional[str] = None,
               crust: Optional[str] = None,
               topping_category: Optional[str] = None) -> List[MenuItem]:
        """
        Retrieve menu items.
        
        Args:
            size: Optional filter (small, medium, large, xlarge)
            crust: Optional filter (thin, hand-tossed, stuffed-crust, pan)
            topping_category: Optional filter (meats, veggies, sauces, cheeses, all)
        
        Returns:
            List of MenuItem objects (immutable, idempotent)
        
        Raises:
            requests.RequestException: On API failure
        """
        params = {}
        if size:
            params['size'] = size
        if crust:
            params['crust'] = crust
        if topping_category:
            params['topping_category'] = topping_category
        
        response = requests.get(
            f"{PIZZA_API_URL}/api/menu",
            params=params,
            timeout=API_TIMEOUT,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        items = [
            MenuItem(
                item_id=item['id'],
                name=item['name'],
                description=item['description'],
                price=float(item['price']),
                size=item.get('size'),
                crust=item.get('crust'),
                available=item.get('available', True)
            )
            for item in data.get('items', [])
        ]
        
        logger.info(f"menu_lookup returned {len(items)} items")
        return items


class AllergenLookup:
    """GET /api/allergens - Retrieve allergen data (idempotent, CRITICAL for safety)."""
    
    @staticmethod
    @idempotent_get()
    def lookup(item_id: str, allergen_filter: Optional[str] = None) -> AllergenData:
        """
        Retrieve allergen and ingredient data for a menu item.
        
        CRITICAL: Never guess allergen status. Always call this tool.
        Returns cross-contact warning and kitchen prep notes.
        
        Args:
            item_id: Menu item ID (from menu_lookup)
            allergen_filter: Optional specific allergen (peanuts, tree_nuts, milk, etc., or 'all')
        
        Returns:
            AllergenData object (immutable)
        
        Raises:
            requests.RequestException: On API failure (escalate to human)
        """
        params = {'item_id': item_id}
        if allergen_filter:
            params['allergen'] = allergen_filter
        
        response = requests.get(
            f"{PIZZA_API_URL}/api/allergens",
            params=params,
            timeout=API_TIMEOUT,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        
        allergen_data = AllergenData(
            item_id=item_id,
            allergens=data.get('allergens', []),
            cross_contact_risk=data.get('cross_contact_risk', True),
            contains_fda_big_nine=data.get('contains_fda_big_nine', []),
            contains_eu_fourteen=data.get('contains_eu_fourteen', []),
            preparation_notes=data.get('preparation_notes', 'Prepared in shared kitchen environment.')
        )
        
        logger.info(f"allergen_lookup for {item_id}: {len(allergen_data.allergens)} allergens found")
        logger.warning(f"Cross-contact risk: {allergen_data.cross_contact_risk}")
        
        return allergen_data


class PriceCalculator:
    """GET /api/price - Calculate order total (idempotent, deterministic)."""
    
    @staticmethod
    @idempotent_get()
    def calculate(order_items: List[Dict[str, Any]],
                  tax_jurisdiction: str,
                  fulfillment_type: str = "pickup") -> PriceCalculation:
        """
        Calculate order total with taxes and fees.
        
        CRITICAL: Always use this tool for prices. Never guess.
        Deterministic: same items + jurisdiction + fulfillment → same total.
        
        Args:
            order_items: List of {item_id, quantity}
            tax_jurisdiction: State/province code (e.g., 'CA', 'NY')
            fulfillment_type: 'pickup' or 'delivery'
        
        Returns:
            PriceCalculation object (immutable, deterministic)
        
        Raises:
            requests.RequestException: On API failure
        """
        payload = {
            'items': order_items,
            'tax_jurisdiction': tax_jurisdiction,
            'fulfillment_type': fulfillment_type
        }
        
        response = requests.post(
            f"{PIZZA_API_URL}/api/price",
            json=payload,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        order_id = str(uuid.uuid4())  # Generate order_id for price calculation
        
        calculation = PriceCalculation(
            order_id=order_id,
            items=order_items,
            subtotal=float(data['subtotal']),
            tax=float(data['tax']),
            delivery_fee=float(data.get('delivery_fee', 0.0)),
            total=float(data['total']),
            calculated_at=datetime.utcnow().isoformat() + 'Z'
        )
        
        logger.info(f"price_calc: subtotal={calculation.subtotal}, tax={calculation.tax}, total={calculation.total}")
        
        return calculation


class OrderSubmitter:
    """POST /api/orders - Submit order (idempotent with order_id key, immutable state)."""
    
    @staticmethod
    @idempotent_post
    def submit(order_id: str,
               customer_id: str,
               items: List[Dict[str, Any]],
               fulfillment_type: str,
               fulfillment_address: Optional[str],
               fulfillment_time: str,
               allergen_flags: Optional[List[str]] = None,
               special_requests: Optional[str] = None) -> Order:
        """
        Submit a finalized, customer-confirmed order.
        
        IDEMPOTENT: Same order_id → same result, no double-charge.
        Immutable: Creates new order version; never mutates prior orders.
        
        CRITICAL: Call only after explicit customer confirmation.
        
        Args:
            order_id: UUID (idempotency key; must be unique or reuse for retry)
            customer_id: UUID of customer
            items: List of {item_id, quantity, special_instructions}
            fulfillment_type: 'pickup' or 'delivery'
            fulfillment_address: Delivery address or None for pickup
            fulfillment_time: ISO 8601 datetime
            allergen_flags: List of customer-stated allergies (for kitchen only)
            special_requests: Additional notes for kitchen
        
        Returns:
            Order object (immutable, version tracked)
        
        Raises:
            requests.RequestException: On API failure (retryable or terminal)
            ValueError: On validation error (terminal)
        """
        # Validation (terminal errors)
        if fulfillment_type == "delivery" and not fulfillment_address:
            raise ValueError("delivery_address required for delivery orders")
        
        payload = {
            'order_id': order_id,
            'customer_id': customer_id,
            'items': items,
            'fulfillment_type': fulfillment_type,
            'fulfillment_address': fulfillment_address,
            'fulfillment_time': fulfillment_time,
            'allergen_flags': allergen_flags or [],
            'special_requests': special_requests
        }
        
        response = requests.post(
            f"{PIZZA_API_URL}/api/orders",
            json=payload,
            timeout=API_TIMEOUT,
            headers={
                "Content-Type": "application/json",
                "Idempotency-Key": order_id  # Foundry-standard idempotency header
            }
        )
        response.raise_for_status()
        
        data = response.json()
        
        order = Order(
            order_id=data['order_id'],
            version=data.get('version', 1),
            customer_id=customer_id,
            items=items,
            subtotal=float(data['subtotal']),
            tax=float(data['tax']),
            delivery_fee=float(data.get('delivery_fee', 0.0)),
            total=float(data['total']),
            fulfillment_type=fulfillment_type,
            fulfillment_address=fulfillment_address,
            fulfillment_time=fulfillment_time,
            allergen_flags=allergen_flags or [],
            status="submitted",
            special_requests=special_requests,
            created_at=data['created_at'],
            updated_at=data.get('updated_at', data['created_at'])
        )
        
        # Log allergen flags for audit trail
        if allergen_flags:
            logger.warning(f"Order {order_id} submitted with allergen flags: {allergen_flags}")
        
        logger.info(f"order_submit succeeded: order_id={order.order_id}, status={order.status}")
        
        return order


class OrderStatusChecker:
    """GET /api/orders/{order_id} - Check order status (idempotent)."""
    
    @staticmethod
    @idempotent_get()
    def check(order_id: str, customer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Check status of an existing order.
        
        Idempotent: same order_id → same status.
        Returns status, ETA, and pickup/delivery details.
        
        Args:
            order_id: Order ID to check
            customer_id: Optional customer ID for privacy verification
        
        Returns:
            Order status dict {order_id, status, pickup_time, delivery_eta, items, ...}
        
        Raises:
            requests.RequestException: On API failure or order not found
        """
        params = {}
        if customer_id:
            params['customer_id'] = customer_id
        
        response = requests.get(
            f"{PIZZA_API_URL}/api/orders/{order_id}",
            params=params,
            timeout=API_TIMEOUT,
            headers={"Accept": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        
        logger.info(f"order_status for {order_id}: status={data.get('status')}")
        
        return data


class HumanHandoff:
    """POST /api/escalations - Escalate to human staff (fire-and-forget)."""
    
    @staticmethod
    def escalate(reason: str,
                 context: Optional[Dict[str, Any]] = None,
                 priority: str = "normal") -> Dict[str, Any]:
        """
        Escalate to human staff.
        
        Use when: allergen uncertainty, customer distress, tool failure, complaint, etc.
        Fire-and-forget: creates ticket and routes to support queue.
        
        Args:
            reason: Escalation reason (allergen_uncertainty, customer_distress, etc.)
            context: Conversation context (last messages, customer intent, data)
            priority: 'normal', 'high', 'urgent'
        
        Returns:
            Escalation confirmation {ticket_id, queue_name, estimated_wait}
        
        Raises:
            requests.RequestException: On API failure
        """
        payload = {
            'reason': reason,
            'context': context or {},
            'priority': priority,
            'escalated_at': datetime.utcnow().isoformat() + 'Z'
        }
        
        response = requests.post(
            f"{PIZZA_API_URL}/api/escalations",
            json=payload,
            timeout=API_TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        
        data = response.json()
        
        logger.warning(f"Escalation created: ticket_id={data.get('ticket_id')}, reason={reason}, priority={priority}")
        
        return data


# ===== Tool Registration =====
TOOLS = {
    'menu_lookup': MenuLookup.lookup,
    'allergen_lookup': AllergenLookup.lookup,
    'price_calc': PriceCalculator.calculate,
    'order_submit': OrderSubmitter.submit,
    'order_status': OrderStatusChecker.check,
    'human_handoff': HumanHandoff.escalate,
}


def get_tool(tool_name: str):
    """Get a tool by name."""
    if tool_name not in TOOLS:
        raise ValueError(f"Unknown tool: {tool_name}")
    return TOOLS[tool_name]


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    # Test menu_lookup (idempotent GET)
    try:
        items = MenuLookup.lookup(size="large")
        print(f"Found {len(items)} large pizzas")
    except Exception as e:
        print(f"menu_lookup failed: {e}")
    
    # Test allergen_lookup (idempotent GET)
    try:
        if items:
            allergens = AllergenLookup.lookup(items[0].item_id)
            print(f"Allergens for {items[0].name}: {allergens.allergens}")
    except Exception as e:
        print(f"allergen_lookup failed: {e}")
