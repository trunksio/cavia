#!/bin/bash

# Health check script for CAVIA infrastructure

set -e

echo "🏥 CAVIA Health Check"
echo "===================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

check_service() {
    local name=$1
    local url=$2

    if curl -sf "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $name is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $name is not responding"
        return 1
    fi
}

# Check PostgreSQL
echo -n "Checking PostgreSQL... "
if docker-compose exec -T postgres pg_isready -U cavia > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} PostgreSQL is ready"
else
    echo -e "${RED}✗${NC} PostgreSQL is not ready"
fi

# Check Redis
echo -n "Checking Redis... "
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} Redis is responding"
else
    echo -e "${RED}✗${NC} Redis is not responding"
fi

# Check MinIO
echo -n "Checking MinIO... "
check_service "MinIO" "http://localhost:9000/minio/health/live"

# Check Agent Registry (if running)
echo -n "Checking Agent Registry... "
if check_service "Agent Registry" "http://localhost:8001/health" 2>/dev/null; then
    :
else
    echo -e "${YELLOW}!${NC} Agent Registry not yet running (this is okay if not started)"
fi

# Check RQ Dashboard (if running)
echo -n "Checking RQ Dashboard... "
if check_service "RQ Dashboard" "http://localhost:9181" 2>/dev/null; then
    :
else
    echo -e "${YELLOW}!${NC} RQ Dashboard not yet running (this is okay if not started)"
fi

echo ""
echo "===================="
echo "Health check complete!"
echo ""
echo "Service URLs:"
echo "  - MinIO Console: http://localhost:9001"
echo "  - RQ Dashboard: http://localhost:9181"
echo "  - Agent Registry: http://localhost:8001"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
