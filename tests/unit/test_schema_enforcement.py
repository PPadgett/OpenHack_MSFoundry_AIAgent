"""Schema enforcement tests for JSON schemas and field data types."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path

import pytest
from jsonschema import Draft7Validator


def _load_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _iso_now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


class TestCustomerProfileSchemaTyping:
    def setup_method(self) -> None:
        self.schema = _load_json("schemas/customer-profile.schema.json")
        self.validator = Draft7Validator(self.schema)

    def test_customer_profile_accepts_valid_typed_payload(self) -> None:
        payload = {
            "customer_id": str(uuid.uuid4()),
            "preferred_name": "Jamie",
            "contact_preferences": {
                "email": "jamie@example.com",
                "phone": "+12065550123",
                "sms_opted_in": True,
                "marketing_opted_in": False,
            },
            "dietary_restrictions": ["vegetarian"],
            "allergies": [
                {
                    "allergen": "peanuts",
                    "severity": "severe",
                    "source": "customer_stated",
                    "version": 1,
                    "created_at": _iso_now(),
                    "updated_at": None,
                    "notes": "Carries epinephrine",
                }
            ],
            "consent": {
                "store_profile": True,
                "store_allergies": True,
                "marketing_communications": False,
                "captured_on": _iso_now(),
                "policy_version": "1.0",
                "ip_address": None,
            },
            "retention": {
                "ttl_days": 365,
                "inactivity_threshold_days": 90,
                "last_activity": _iso_now(),
                "expires_on": "2027-08-26",
                "deletion_requested": None,
            },
        }
        assert not list(self.validator.iter_errors(payload))

    def test_customer_profile_rejects_wrong_types(self) -> None:
        payload = {
            "customer_id": str(uuid.uuid4()),
            "consent": {
                "store_profile": "yes",  # should be boolean
                "captured_on": _iso_now(),
                "policy_version": "1.0",
            },
            "retention": {
                "ttl_days": "365",  # should be integer
                "inactivity_threshold_days": 90,
                "last_activity": _iso_now(),
                "expires_on": "2027-08-26",
            },
        }
        errors = list(self.validator.iter_errors(payload))
        assert errors

    def test_customer_profile_requires_core_fields(self) -> None:
        payload = {"customer_id": str(uuid.uuid4())}
        errors = list(self.validator.iter_errors(payload))
        missing_paths = {"/".join([str(x) for x in e.path]) for e in errors}
        assert errors
        assert "" in missing_paths or len(errors) >= 1


class TestToolContractTypes:
    @pytest.mark.parametrize(
        "file_path, tool_name, required_fields",
        [
            (
                "tools/order_submit.json",
                "order_submit",
                [
                    "order_id",
                    "customer_id",
                    "items",
                    "fulfillment_type",
                    "fulfillment_time",
                ],
            ),
            (
                "tools/pizza_quantity_estimate.json",
                "pizza_quantity_estimate",
                ["number_of_people", "appetite_level"],
            ),
            ("tools/allergen_lookup.json", "allergen_lookup", ["item_id"]),
            ("tools/order_status.json", "order_status", ["order_id"]),
        ],
    )
    def test_tool_contract_declares_required_fields(
        self, file_path: str, tool_name: str, required_fields: list[str]
    ) -> None:
        schema_obj = _load_json(file_path)
        assert schema_obj["properties"]["name"]["const"] == tool_name
        actual_required = schema_obj["properties"]["parameters"]["properties"][
            "required"
        ]["const"]
        assert actual_required == required_fields

    def test_order_submit_contract_has_expected_scalar_types(self) -> None:
        schema_obj = _load_json("tools/order_submit.json")
        props = schema_obj["properties"]["parameters"]["properties"]["properties"][
            "properties"
        ]

        assert props["order_id"]["properties"]["type"]["const"] == "string"
        assert props["customer_id"]["properties"]["type"]["const"] == "string"
        assert props["fulfillment_type"]["properties"]["type"]["const"] == "string"
        assert props["items"]["properties"]["type"]["const"] == "array"
        assert (
            props["allergen_flags"]["properties"]["items"]["properties"]["type"][
                "const"
            ]
            == "string"
        )

    def test_pizza_quantity_contract_has_expected_scalar_types(self) -> None:
        schema_obj = _load_json("tools/pizza_quantity_estimate.json")
        props = schema_obj["properties"]["parameters"]["properties"]["properties"][
            "properties"
        ]

        assert props["number_of_people"]["properties"]["type"]["const"] == "integer"
        assert props["appetite_level"]["properties"]["type"]["const"] == "string"
        assert props["slices_per_pizza"]["properties"]["type"]["const"] == "integer"
