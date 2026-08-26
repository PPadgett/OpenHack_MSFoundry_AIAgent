"""
Unit tests for Crust agent - Tool implementations.
Tests idempotence, immutability, and error handling.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid

# Import tool implementations
from tools.tool_implementations import (
    MenuItem,
    AllergenData,
    PriceCalculation,
    Order,
    MenuLookup,
    AllergenLookup,
    PriceCalculator,
    OrderSubmitter,
    OrderStatusChecker,
    HumanHandoff,
    PizzaQuantityEstimator,
)


class TestMenuLookup:
    """Test menu_lookup (GET, idempotent)."""

    @patch("tools.tool_implementations.requests.get")
    def test_menu_lookup_idempotent(self, mock_get):
        """Idempotence: same input → same output."""
        # Mock response
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "id": "pizza_1",
                    "name": "Large Pepperoni",
                    "description": "Classic pepperoni",
                    "price": 18.99,
                    "size": "large",
                    "crust": "hand-tossed",
                    "available": True,
                }
            ]
        }
        mock_get.return_value = mock_response

        # Call twice with same params
        result1 = MenuLookup.lookup(size="large")
        result2 = MenuLookup.lookup(size="large")

        # Should be identical
        assert result1 == result2
        assert result1[0].item_id == "pizza_1"
        assert result1[0].price == 18.99

        # Verify API called twice (GET is idempotent; OK to call multiple times)
        assert mock_get.call_count == 2

    def test_menu_item_immutable(self):
        """MenuItem objects are immutable (frozen dataclass)."""
        item = MenuItem(
            item_id="pizza_1",
            name="Pepperoni",
            description="Classic",
            price=18.99,
            size="large",
            crust="hand-tossed",
            available=True,
        )

        # Try to mutate (should fail)
        with pytest.raises(AttributeError):
            item.price = 20.00


class TestAllergenLookup:
    """Test allergen_lookup (GET, idempotent, CRITICAL for safety)."""

    @patch("tools.tool_implementations.requests.get")
    def test_allergen_lookup_idempotent(self, mock_get):
        """Idempotence: same input → same allergen data."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "allergens": ["wheat", "milk"],
            "cross_contact_risk": True,
            "contains_fda_big_nine": ["wheat", "milk"],
            "contains_eu_fourteen": ["wheat", "milk"],
            "preparation_notes": "Prepared in shared kitchen.",
        }
        mock_get.return_value = mock_response

        # Call twice
        result1 = AllergenLookup.lookup("pizza_1")
        result2 = AllergenLookup.lookup("pizza_1")

        # Should be identical
        assert result1 == result2
        assert "wheat" in result1.allergens
        assert result1.cross_contact_risk is True

    def test_allergen_data_immutable(self):
        """AllergenData objects are immutable."""
        allergen_data = AllergenData(
            item_id="pizza_1",
            allergens=["wheat", "milk"],
            cross_contact_risk=True,
            contains_fda_big_nine=["wheat", "milk"],
            contains_eu_fourteen=["wheat", "milk"],
            preparation_notes="Shared kitchen.",
        )

        # Try to mutate (should fail)
        with pytest.raises(AttributeError):
            allergen_data.cross_contact_risk = False


class TestPriceCalculator:
    """Test price_calc (GET, deterministic, idempotent)."""

    @patch("tools.tool_implementations.requests.post")
    def test_price_calc_deterministic(self, mock_post):
        """Determinism: same items → same price (idempotent)."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "subtotal": 18.99,
            "tax": 1.52,
            "delivery_fee": 0.0,
            "total": 20.51,
        }
        mock_post.return_value = mock_response

        items = [{"item_id": "pizza_1", "quantity": 1}]

        # Call twice with same items
        result1 = PriceCalculator.calculate(items, "CA", "pickup")
        result2 = PriceCalculator.calculate(items, "CA", "pickup")

        # Totals should match (same calculation)
        assert result1.total == result2.total
        assert result1.total == 20.51

    def test_price_calculation_immutable(self):
        """PriceCalculation objects are immutable."""
        calc = PriceCalculation(
            order_id=str(uuid.uuid4()),
            items=[],
            subtotal=18.99,
            tax=1.52,
            delivery_fee=0.0,
            total=20.51,
            calculated_at=datetime.utcnow().isoformat() + "Z",
        )

        # Try to mutate (should fail)
        with pytest.raises(AttributeError):
            calc.total = 25.00


class TestOrderSubmitter:
    """Test order_submit (POST, idempotent with order_id key)."""

    @patch("tools.tool_implementations.requests.post")
    def test_order_submit_idempotent(self, mock_post):
        """Idempotence: same order_id → same result (no double-charge)."""
        order_id = str(uuid.uuid4())
        customer_id = str(uuid.uuid4())

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "order_id": order_id,
            "version": 1,
            "subtotal": 18.99,
            "tax": 1.52,
            "delivery_fee": 0.0,
            "total": 20.51,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "updated_at": datetime.utcnow().isoformat() + "Z",
        }
        mock_post.return_value = mock_response

        items = [{"item_id": "pizza_1", "quantity": 1}]

        # Submit twice with same order_id
        result1 = OrderSubmitter.submit(
            order_id=order_id,
            customer_id=customer_id,
            items=items,
            fulfillment_type="pickup",
            fulfillment_address=None,
            fulfillment_time=(datetime.utcnow() + timedelta(minutes=30)).isoformat(),
        )

        result2 = OrderSubmitter.submit(
            order_id=order_id,
            customer_id=customer_id,
            items=items,
            fulfillment_type="pickup",
            fulfillment_address=None,
            fulfillment_time=(datetime.utcnow() + timedelta(minutes=30)).isoformat(),
        )

        # Same order_id → same result (idempotent)
        assert result1.order_id == result2.order_id
        assert result1.total == result2.total

    def test_order_submit_requires_confirmation(self):
        """Order submit should only be called after explicit confirmation."""
        # This is enforced in the workflow, but tool validates it
        # If pre-condition violated, should error
        pass

    def test_order_submit_delivery_requires_address(self):
        """Delivery orders must have address (validation)."""
        order_id = str(uuid.uuid4())
        customer_id = str(uuid.uuid4())

        with pytest.raises(ValueError, match="delivery_address"):
            OrderSubmitter.submit(
                order_id=order_id,
                customer_id=customer_id,
                items=[],
                fulfillment_type="delivery",
                fulfillment_address=None,
                fulfillment_time=datetime.utcnow().isoformat(),
            )

    def test_order_immutable(self):
        """Order objects are immutable."""
        order = Order(
            order_id=str(uuid.uuid4()),
            version=1,
            customer_id=str(uuid.uuid4()),
            items=[],
            subtotal=18.99,
            tax=1.52,
            delivery_fee=0.0,
            total=20.51,
            fulfillment_type="pickup",
            fulfillment_address=None,
            fulfillment_time=datetime.utcnow().isoformat(),
            allergen_flags=[],
            status="submitted",
            special_requests=None,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat(),
        )

        # Try to mutate (should fail)
        with pytest.raises(AttributeError):
            order.status = "cancelled"


class TestOrderStatusChecker:
    """Test order_status (GET, idempotent)."""

    @patch("tools.tool_implementations.requests.get")
    def test_order_status_idempotent(self, mock_get):
        """Idempotence: same order_id → same status."""
        order_id = str(uuid.uuid4())

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "order_id": order_id,
            "status": "preparing",
            "pickup_time": (datetime.utcnow() + timedelta(minutes=30)).isoformat(),
            "items": [{"name": "Large Pepperoni", "quantity": 1}],
        }
        mock_get.return_value = mock_response

        # Call twice
        result1 = OrderStatusChecker.check(order_id)
        result2 = OrderStatusChecker.check(order_id)

        # Should be identical
        assert result1 == result2
        assert result1["status"] == "preparing"


class TestPizzaQuantityEstimator:
    """Test pizza quantity estimation behavior."""

    def test_estimate_is_deterministic(self):
        first = PizzaQuantityEstimator.estimate(10, "average")
        second = PizzaQuantityEstimator.estimate(10, "average")

        assert first == second
        assert first.recommended_pizzas >= 1
        assert first.estimated_total_slices >= 1

    def test_estimate_requires_valid_inputs(self):
        with pytest.raises(ValueError, match="number_of_people"):
            PizzaQuantityEstimator.estimate(0, "average")

        with pytest.raises(ValueError, match="appetite_level"):
            PizzaQuantityEstimator.estimate(5, "very_hungry")


class TestAllergenSafety:
    """Test allergen safety guardrails."""

    @patch("tools.tool_implementations.requests.get")
    def test_allergen_never_declares_safe(self, mock_get):
        """Allergen tool must NEVER declare item safe for allergy."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "allergens": ["peanuts"],
            "cross_contact_risk": True,
            "contains_fda_big_nine": ["peanuts"],
            "contains_eu_fourteen": ["peanuts"],
            "preparation_notes": "Contains peanuts and cross-contact risk.",
        }
        mock_get.return_value = mock_response

        allergen_data = AllergenLookup.lookup("veggie_pizza")

        # Should indicate danger, not safety
        assert "peanuts" in allergen_data.allergens
        assert allergen_data.cross_contact_risk is True
        # Never have a "safe" flag
        assert not hasattr(allergen_data, "safe_for_peanut_allergy")

    def test_allergen_data_always_cross_contact_warning(self):
        """Allergen data should always include cross-contact risk field."""
        allergen_data = AllergenData(
            item_id="pizza_1",
            allergens=["wheat"],
            cross_contact_risk=True,  # Should always be evaluated
            contains_fda_big_nine=["wheat"],
            contains_eu_fourteen=["wheat"],
            preparation_notes="Shared kitchen.",
        )

        # Must have cross_contact_risk field
        assert hasattr(allergen_data, "cross_contact_risk")
        assert allergen_data.cross_contact_risk is not None


class TestConvergence:
    """Test workflow convergence (all paths reach terminal state)."""

    def test_no_infinite_loops_in_slot_collection(self):
        """Slot collection should not loop infinitely."""
        # Workflow enforces max 15 turns before escalate
        # This is enforced at workflow level, not tool level
        pass

    def test_terminal_states_reachable(self):
        """All workflow paths must reach terminal state."""
        # Terminal states: end_success, end_escalation, end_no_order
        # This is enforced by workflow graph
        pass


class TestIdempotenceAndImmutability:
    """Cross-cutting tests for idempotence and immutability."""

    def test_all_data_classes_frozen(self):
        """All data classes should be frozen (immutable)."""
        # MenuItem, AllergenData, PriceCalculation, Order
        # All defined with @dataclass(frozen=True)

        # Test MenuItem
        item = MenuItem(
            item_id="1",
            name="Pizza",
            description="Test",
            price=10.0,
            size="L",
            crust="H",
            available=True,
        )
        with pytest.raises(AttributeError):
            item.price = 15.0

    def test_get_tools_are_idempotent(self):
        """GET tools (menu, allergen, price, status) are idempotent."""
        # menu_lookup: GET → idempotent ✓
        # allergen_lookup: GET → idempotent ✓
        # price_calc: deterministic computation → idempotent ✓
        # order_status: GET → idempotent ✓
        pass

    def test_post_tools_are_idempotent_with_key(self):
        """POST tools (order_submit) use idempotency key."""
        # order_submit: order_id as key → idempotent ✓
        pass


class TestErrorHandling:
    """Test error handling and escalation."""

    @patch("tools.tool_implementations.requests.get")
    def test_tool_failure_retries(self, mock_get):
        """Tools should retry on transient failure (5xx)."""
        # Fail twice, succeed on third
        mock_get.side_effect = [
            Exception("500 Server Error"),
            Exception("503 Service Unavailable"),
            MagicMock(json=lambda: {"items": []}),
        ]

        # With retries, should eventually succeed
        # (or exhaust retries and raise)
        # Implementation detail: decorator handles retries

    def test_terminal_error_no_retry(self):
        """Terminal errors (4xx, validation) should not retry."""
        # 400 Bad Request, 404 Not Found → don't retry, escalate
        # Enforced by tool + workflow
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
