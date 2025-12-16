#!/bin/bash
# VANTA-25: Rule Management API Testing Script
# Tests all CRUD operations, enable/disable, and history endpoints

API_URL="http://localhost:8000"
RULE_ID=""

echo "======================================"
echo "VANTA-25: Rule Management API Testing"
echo "======================================"
echo ""

# Test 1: Create a new rule
echo "Test 1: Create a new rule (POST /api/rules/)"
echo "--------------------------------------------"
RESPONSE=$(curl -s -X POST "$API_URL/api/rules/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Anger Detection Test",
    "type": "threshold",
    "condition_json": {
      "emotion": "angry",
      "threshold": 0.7,
      "min_confidence": 0.8
    },
    "action": "alert",
    "enabled": true
  }')

echo "Response: $RESPONSE"
RULE_ID=$(echo "$RESPONSE" | jq -r '.id')
echo "Rule ID: $RULE_ID"
echo ""

# Test 2: List all rules
echo "Test 2: List all rules (GET /api/rules/)"
echo "----------------------------------------"
curl -s "$API_URL/api/rules/" | jq '.'
echo ""

# Test 3: Get specific rule
echo "Test 3: Get rule by ID (GET /api/rules/{rule_id})"
echo "--------------------------------------------------"
curl -s "$API_URL/api/rules/$RULE_ID" | jq '.'
echo ""

# Test 4: Update rule
echo "Test 4: Update rule (PUT /api/rules/{rule_id})"
echo "----------------------------------------------"
curl -s -X PUT "$API_URL/api/rules/$RULE_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "condition_json": {
      "emotion": "angry",
      "threshold": 0.8,
      "min_confidence": 0.85
    }
  }' | jq '.'
echo ""

# Test 5: Disable rule
echo "Test 5: Disable rule (PATCH /api/rules/{rule_id}/disable)"
echo "----------------------------------------------------------"
curl -s -X PATCH "$API_URL/api/rules/$RULE_ID/disable" | jq '.'
echo ""

# Test 6: Enable rule
echo "Test 6: Enable rule (PATCH /api/rules/{rule_id}/enable)"
echo "-------------------------------------------------------"
curl -s -X PATCH "$API_URL/api/rules/$RULE_ID/enable" | jq '.'
echo ""

# Test 7: Get rule history (should be empty for new rule)
echo "Test 7: Get rule history (GET /api/rules/{rule_id}/history)"
echo "------------------------------------------------------------"
curl -s "$API_URL/api/rules/$RULE_ID/history" | jq '.'
echo ""

# Test 8: Validation - Invalid threshold (should return 400)
echo "Test 8: Validation - Invalid threshold (should return 400)"
echo "-----------------------------------------------------------"
curl -s -X POST "$API_URL/api/rules/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Invalid Threshold Test",
    "type": "threshold",
    "condition_json": {
      "emotion": "angry",
      "threshold": 1.5
    },
    "action": "alert",
    "enabled": true
  }' | jq '.'
echo ""

# Test 9: Validation - Duplicate name (should return 409)
echo "Test 9: Validation - Duplicate name (should return 409)"
echo "--------------------------------------------------------"
curl -s -X POST "$API_URL/api/rules/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "High Anger Detection Test",
    "type": "threshold",
    "condition_json": {
      "emotion": "angry",
      "threshold": 0.7
    },
    "action": "alert",
    "enabled": true
  }' | jq '.'
echo ""

# Test 10: Get non-existent rule (should return 404)
echo "Test 10: Get non-existent rule (should return 404)"
echo "---------------------------------------------------"
curl -s "$API_URL/api/rules/00000000-0000-0000-0000-000000000000" | jq '.'
echo ""

# Test 11: Delete rule
echo "Test 11: Delete rule (DELETE /api/rules/{rule_id})"
echo "---------------------------------------------------"
curl -s -X DELETE "$API_URL/api/rules/$RULE_ID" -w "\nHTTP Status: %{http_code}\n"
echo ""

# Test 12: Verify deletion (should return 404)
echo "Test 12: Verify deletion (should return 404)"
echo "---------------------------------------------"
curl -s "$API_URL/api/rules/$RULE_ID" | jq '.'
echo ""

echo "======================================"
echo "Testing Complete!"
echo "======================================"
