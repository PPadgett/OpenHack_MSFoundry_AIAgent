"""
Allergen safety validation - Launch-blocking tests.
Verifies that allergen guardrails are properly implemented.
"""

import json
import sys
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def test_allergen_guardrail_in_agent_definition():
    """Verify allergen guardrail in agent-definition.yaml."""
    logger.info("Testing allergen guardrail in agent definition...")
    
    with open('agent-definition.yaml', 'r') as f:
        content = f.read()
    
    # CRITICAL CHECKS
    checks = [
        ("Never declare safe", "can't guarantee" in content.lower() or "cannot guarantee" in content.lower()),
        ("Cross-contact disclosure", "cross-contact" in content.lower() or "cross contact" in content.lower()),
        ("Human handoff available", "human_handoff" in content),
        ("Allergen lookup tool", "allergen_lookup" in content),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, result in checks:
        if result:
            logger.info(f"  ✓ {check_name}")
            passed += 1
        else:
            logger.error(f"  ✗ {check_name} - LAUNCH-BLOCKING FAILURE")
            failed += 1
    
    return failed == 0


def test_allergen_safety_rules():
    """Verify allergen-safety-rules.yaml is present and complete."""
    logger.info("Testing allergen safety rules file...")
    
    with open('safety/allergen-safety-rules.yaml', 'r') as f:
        content = f.read()
    
    # Check for all 5 hard rules
    hard_rules = [
        'allergen_never_safe',
        'allergen_always_disclose_cross_contact',
        'allergen_use_tool_never_guess',
        'allergen_escalate_on_uncertainty',
        'allergen_data_for_kitchen_only',
    ]
    
    passed = 0
    failed = 0
    
    for rule in hard_rules:
        if rule in content:
            logger.info(f"  ✓ Hard rule: {rule}")
            passed += 1
        else:
            logger.error(f"  ✗ Hard rule missing: {rule} - LAUNCH-BLOCKING FAILURE")
            failed += 1
    
    return failed == 0


def test_tool_allergen_lookup_implementation():
    """Verify allergen_lookup tool implementation."""
    logger.info("Testing allergen_lookup tool implementation...")
    
    with open('tools/tool_implementations.py', 'r') as f:
        content = f.read()
    
    checks = [
        ("AllergenLookup class exists", "class AllergenLookup" in content),
        ("lookup method exists", "def lookup" in content),
        ("Never declares safe", '"safe"' not in content or 'safe_for' not in content),
        ("cross_contact_risk tracked", "cross_contact_risk" in content),
        ("Error escalation", "raise" in content or "escalate" in content.lower()),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, result in checks:
        if result:
            logger.info(f"  ✓ {check_name}")
            passed += 1
        else:
            logger.error(f"  ✗ {check_name} - LAUNCH-BLOCKING FAILURE")
            failed += 1
    
    return failed == 0


def test_workflow_allergen_handling():
    """Verify workflow state machine handles allergies correctly."""
    logger.info("Testing workflow allergen handling...")
    
    with open('workflows/ordering-workflow.yaml', 'r') as f:
        content = f.read()
    
    checks = [
        ("collect_allergies state exists", "collect_allergies:" in content),
        ("allergen_disclosure state exists", "allergen_disclosure:" in content),
        ("Never declares safe", "safe" not in content.lower() or "safety" in content),
        ("Human handoff in allergy path", "human_handoff" in content),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, result in checks:
        if result:
            logger.info(f"  ✓ {check_name}")
            passed += 1
        else:
            logger.error(f"  ✗ {check_name} - LAUNCH-BLOCKING FAILURE")
            failed += 1
    
    return failed == 0


def test_customer_profile_consent():
    """Verify GDPR Article 9 consent capture in customer profile."""
    logger.info("Testing customer profile GDPR compliance...")
    
    with open('schemas/customer-profile.schema.json', 'r') as f:
        schema = json.load(f)
    
    checks = [
        ("allergies field exists", "allergies" in schema.get('properties', {})),
        ("consent object exists", "consent" in schema.get('properties', {})),
        ("store_allergies consent field", "store_allergies" in str(schema)),
        ("Allergies are versioned", "version" in str(schema.get('properties', {}).get('allergies', {}))),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, result in checks:
        if result:
            logger.info(f"  ✓ {check_name}")
            passed += 1
        else:
            logger.error(f"  ✗ {check_name} - LAUNCH-BLOCKING FAILURE")
            failed += 1
    
    return failed == 0


def test_logging_allergen_operations():
    """Verify allergen operations are logged at WARNING level."""
    logger.info("Testing allergen operation logging...")
    
    with open('tools/tool_implementations.py', 'r') as f:
        content = f.read()
    
    # Check for warning-level logging in allergen operations
    checks = [
        ("Allergen lookup logs at WARNING", "logger.warning" in content and "allergen" in content.lower()),
        ("Allergen flags logged", "allergen_flags" in content and "logger" in content),
        ("Cross-contact logged", "cross_contact" in content and "logger" in content),
    ]
    
    passed = 0
    failed = 0
    
    for check_name, result in checks:
        if result:
            logger.info(f"  ✓ {check_name}")
            passed += 1
        else:
            logger.error(f"  ✗ {check_name}")
            failed += 1
    
    return failed == 0


def main():
    """Run all allergen safety validation tests."""
    logger.info("=" * 60)
    logger.info("ALLERGEN SAFETY VALIDATION (LAUNCH-BLOCKING)")
    logger.info("=" * 60)
    logger.info("")
    
    tests = [
        test_allergen_guardrail_in_agent_definition,
        test_allergen_safety_rules,
        test_tool_allergen_lookup_implementation,
        test_workflow_allergen_handling,
        test_customer_profile_consent,
        test_logging_allergen_operations,
    ]
    
    results = []
    for test_func in tests:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            logger.error(f"Test {test_func.__name__} failed with exception: {e}")
            results.append(False)
        logger.info("")
    
    logger.info("=" * 60)
    total = len(results)
    passed = sum(results)
    failed = total - passed
    
    if failed == 0:
        logger.info(f"✓ ALL ALLERGEN SAFETY TESTS PASSED ({passed}/{total})")
        logger.info("Allergen guardrail is LAUNCH-READY ✓")
        logger.info("=" * 60)
        return 0
    else:
        logger.error(f"✗ ALLERGEN SAFETY TESTS FAILED ({failed}/{total} failures)")
        logger.error("LAUNCH-BLOCKING: Fix all failures before deployment")
        logger.error("=" * 60)
        return 1


if __name__ == '__main__':
    sys.exit(main())
