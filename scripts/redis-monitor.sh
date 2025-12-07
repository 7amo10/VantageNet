#!/bin/bash
# ========================================
# Redis Monitoring Script
# ========================================
# Purpose: Monitor Redis streams, memory, and performance metrics
# Usage: ./scripts/redis-monitor.sh
# ========================================

set -e

REDIS_HOST="${REDIS_HOST:-localhost}"
REDIS_PORT="${REDIS_PORT:-6380}"

echo "=========================================="
echo "Redis Monitoring Dashboard"
echo "=========================================="
echo "Host: ${REDIS_HOST}:${REDIS_PORT}"
echo "Time: $(date)"
echo ""

# ========================================
# Stream Metrics
# ========================================
echo "📊 STREAM METRICS"
echo "=========================================="

echo ""
echo "emotion:events stream:"
EMOTION_LEN=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XLEN emotion:events)
echo "  Length: ${EMOTION_LEN} messages"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO STREAM emotion:events | grep -E "length|radix-tree|first-entry|last-entry"

echo ""
echo "sentiment:crowd stream:"
SENTIMENT_LEN=$(redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XLEN sentiment:crowd)
echo "  Length: ${SENTIMENT_LEN} messages"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO STREAM sentiment:crowd | grep -E "length|radix-tree|first-entry|last-entry"

# ========================================
# Consumer Group Metrics
# ========================================
echo ""
echo "=========================================="
echo "👥 CONSUMER GROUP METRICS"
echo "=========================================="

echo ""
echo "emotion:events consumer groups:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO GROUPS emotion:events

echo ""
echo "sentiment:crowd consumer groups:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" XINFO GROUPS sentiment:crowd

# ========================================
# Memory Metrics
# ========================================
echo ""
echo "=========================================="
echo "💾 MEMORY METRICS"
echo "=========================================="

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" INFO memory | grep -E "used_memory_human|used_memory_rss_human|used_memory_peak_human|maxmemory|maxmemory_policy|mem_fragmentation_ratio"

echo ""
echo "Detailed memory stats:"
redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" MEMORY STATS | grep -E "peak.allocated|total.allocated|startup.allocated|overhead.total|keys.count|keys.bytes-per-key"

# ========================================
# Performance Metrics
# ========================================
echo ""
echo "=========================================="
echo "⚡ PERFORMANCE METRICS"
echo "=========================================="

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" INFO stats | grep -E "total_connections_received|total_commands_processed|instantaneous_ops_per_sec|rejected_connections|expired_keys|evicted_keys"

# ========================================
# Persistence Metrics
# ========================================
echo ""
echo "=========================================="
echo "💿 PERSISTENCE METRICS (AOF)"
echo "=========================================="

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" INFO persistence | grep -E "aof_enabled|aof_current_size|aof_base_size|aof_pending_rewrite|aof_last_write_status|aof_last_rewrite_time_sec"

# ========================================
# Slowlog
# ========================================
echo ""
echo "=========================================="
echo "🐌 SLOWLOG (Last 10 entries)"
echo "=========================================="

redis-cli -h "${REDIS_HOST}" -p "${REDIS_PORT}" SLOWLOG GET 10

# ========================================
# Summary
# ========================================
echo ""
echo "=========================================="
echo "📈 SUMMARY"
echo "=========================================="
echo "  emotion:events length: ${EMOTION_LEN}"
echo "  sentiment:crowd length: ${SENTIMENT_LEN}"
echo ""
echo "Stream health checks:"

# Check if streams are within expected limits
if [ "${EMOTION_LEN}" -gt 1000 ]; then
  echo "  ⚠️  emotion:events exceeds MAXLEN ~1000 (current: ${EMOTION_LEN})"
else
  echo "  ✅ emotion:events within limits"
fi

if [ "${SENTIMENT_LEN}" -gt 10000 ]; then
  echo "  ⚠️  sentiment:crowd exceeds MAXLEN ~10000 (current: ${SENTIMENT_LEN})"
else
  echo "  ✅ sentiment:crowd within limits"
fi

echo ""
echo "=========================================="
