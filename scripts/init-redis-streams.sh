#!/bin/bash
# ========================================
# Redis Streams Initialization Script
# ========================================
# Purpose: Initialize Redis streams and consumer groups for VantageNet
# Streams: emotion:events, sentiment:crowd
# Consumer Groups: emotion-detector-group, sentiment-analyzer-group, api-gateway-group
# ========================================

set -e

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6380}"

echo "🚀 Initializing Redis Streams..."
echo "Connecting to Redis at ${REDIS_HOST}:${REDIS_PORT}"

# Wait for Redis to be ready
until redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" ping > /dev/null 2>&1; do
  echo "⏳ Waiting for Redis to be ready..."
  sleep 2
done

echo "✅ Redis is ready!"

# ========================================
# Create emotion:events stream
# ========================================
echo ""
echo "📊 Creating emotion:events stream..."

# Add initial message to create stream
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XADD emotion:events \* \
  type "init" \
  message "Stream initialized" \
  timestamp "$(date -u +%s)" > /dev/null

echo "✅ Stream emotion:events created"

# Create consumer groups for emotion:events
echo "Creating consumer groups for emotion:events..."

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XGROUP CREATE emotion:events emotion-detector-group 0 MKSTREAM > /dev/null 2>&1 || \
  echo "⚠️  Consumer group emotion-detector-group already exists"

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XGROUP CREATE emotion:events sentiment-analyzer-group 0 MKSTREAM > /dev/null 2>&1 || \
  echo "⚠️  Consumer group sentiment-analyzer-group already exists"

echo "✅ Consumer groups created for emotion:events"

# ========================================
# Create sentiment:crowd stream
# ========================================
echo ""
echo "📊 Creating sentiment:crowd stream..."

# Add initial message to create stream
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XADD sentiment:crowd \* \
  type "init" \
  message "Stream initialized" \
  timestamp "$(date -u +%s)" > /dev/null

echo "✅ Stream sentiment:crowd created"

# Create consumer groups for sentiment:crowd
echo "Creating consumer groups for sentiment:crowd..."

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XGROUP CREATE sentiment:crowd api-gateway-group 0 MKSTREAM > /dev/null 2>&1 || \
  echo "⚠️  Consumer group api-gateway-group already exists"

echo "✅ Consumer groups created for sentiment:crowd"

# ========================================
# Verify initialization
# ========================================
echo ""
echo "🔍 Verifying stream configuration..."

echo ""
echo "emotion:events info:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO STREAM emotion:events

echo ""
echo "emotion:events consumer groups:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO GROUPS emotion:events

echo ""
echo "sentiment:crowd info:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO STREAM sentiment:crowd

echo ""
echo "sentiment:crowd consumer groups:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO GROUPS sentiment:crowd

echo ""
echo "✅ Redis streams initialization complete!"
echo ""
echo "📊 Stream Summary:"
echo "  - emotion:events: MAXLEN ~1000 (raw emotion detections)"
echo "  - sentiment:crowd: MAXLEN ~10000 (aggregated sentiment analytics)"
echo ""
echo "👥 Consumer Groups:"
echo "  - emotion-detector-group → emotion:events"
echo "  - sentiment-analyzer-group → emotion:events"
echo "  - api-gateway-group → sentiment:crowd"
echo ""