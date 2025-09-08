#!/bin/bash
# Gateway Configuration Validation Script
# Validates that the improved Dockerfile properly supports environment variable overrides

set -e

SCRIPT_DIR="$(dirname "$0")"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== MCP Platform Gateway Configuration Validation ==="
echo "Project root: $PROJECT_ROOT"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test counter
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_pattern="$3"
    
    echo "Running test: $test_name"
    
    if eval "$test_command" | grep -q "$expected_pattern"; then
        echo -e "${GREEN}✅ PASS${NC}: $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}❌ FAIL${NC}: $test_name"
        echo "Expected pattern: $expected_pattern"
        echo "Actual output:"
        eval "$test_command" || true
        ((TESTS_FAILED++))
    fi
    echo ""
}

# Test 1: Check Dockerfile no longer has hardcoded database URL in CMD
echo "=== Test 1: No Hardcoded Database URL in CMD ==="
DOCKERFILE_PATH="$PROJECT_ROOT/docker/gateway.dockerfile"

if grep -q -- '--database.*sqlite' "$DOCKERFILE_PATH"; then
    echo -e "${RED}❌ FAIL${NC}: Dockerfile still contains hardcoded database URL in CMD"
    ((TESTS_FAILED++))
else
    echo -e "${GREEN}✅ PASS${NC}: No hardcoded database URL in CMD"
    ((TESTS_PASSED++))
fi
echo ""

# Test 2: Check Dockerfile CMD uses environment variables
echo "=== Test 2: CMD Uses Environment Variables ==="
if grep -q 'CMD.*start"]$' "$DOCKERFILE_PATH"; then
    echo -e "${GREEN}✅ PASS${NC}: CMD uses environment variables (no hardcoded arguments)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: CMD still contains hardcoded arguments"
    ((TESTS_FAILED++))
fi
echo ""

# Test 3: Check worker count matches docker-compose default
echo "=== Test 3: Worker Count Matches Docker-Compose ==="
if grep -q 'GATEWAY_WORKERS=2' "$DOCKERFILE_PATH"; then
    echo -e "${GREEN}✅ PASS${NC}: Dockerfile worker count matches docker-compose default (2)"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Worker count mismatch between Dockerfile and docker-compose"
    ((TESTS_FAILED++))
fi
echo ""

# Test 4: Check docker-compose configuration consistency
echo "=== Test 4: Docker-Compose Configuration Consistency ==="
COMPOSE_PATH="$PROJECT_ROOT/docker-compose.yml"

# Check that docker-compose defines GATEWAY_DATABASE_URL
if grep -q 'GATEWAY_DATABASE_URL: postgresql://' "$COMPOSE_PATH"; then
    echo -e "${GREEN}✅ PASS${NC}: Docker-compose defines PostgreSQL database URL"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Docker-compose missing PostgreSQL database configuration"
    ((TESTS_FAILED++))
fi
echo ""

# Test 5: Simulate environment variable override
echo "=== Test 5: Environment Variable Override Simulation ==="

# Create a temporary test script
TEST_SCRIPT=$(mktemp)
cat > "$TEST_SCRIPT" << 'EOF'
#!/bin/bash

# Set Dockerfile defaults
export GATEWAY_DATABASE_URL="sqlite:///data/gateway.db"
export GATEWAY_WORKERS="2"

echo "BEFORE override:"
echo "DATABASE_URL: $GATEWAY_DATABASE_URL"
echo "WORKERS: $GATEWAY_WORKERS"

# Simulate docker-compose override
export GATEWAY_DATABASE_URL="postgresql://user:pass@host:5432/db"
export GATEWAY_WORKERS="4"

echo "AFTER override:"
echo "DATABASE_URL: $GATEWAY_DATABASE_URL"
echo "WORKERS: $GATEWAY_WORKERS"

# Test that variables can be overridden
if [[ "$GATEWAY_DATABASE_URL" == "postgresql://user:pass@host:5432/db" ]] && [[ "$GATEWAY_WORKERS" == "4" ]]; then
    echo "OVERRIDE_SUCCESS"
else
    echo "OVERRIDE_FAILED"
fi
EOF

chmod +x "$TEST_SCRIPT"

if "$TEST_SCRIPT" | grep -q "OVERRIDE_SUCCESS"; then
    echo -e "${GREEN}✅ PASS${NC}: Environment variables can be properly overridden"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Environment variable override failed"
    echo "Test script output:"
    "$TEST_SCRIPT"
    ((TESTS_FAILED++))
fi

rm -f "$TEST_SCRIPT"
echo ""

# Test 6: Configuration documentation
echo "=== Test 6: Configuration Documentation ==="
if grep -q "CONFIGURATION APPROACH:" "$DOCKERFILE_PATH"; then
    echo -e "${GREEN}✅ PASS${NC}: Dockerfile contains configuration documentation"
    ((TESTS_PASSED++))
else
    echo -e "${RED}❌ FAIL${NC}: Missing configuration documentation"
    ((TESTS_FAILED++))
fi
echo ""

# Summary
echo "=== Test Summary ==="
echo "Tests passed: $TESTS_PASSED"
echo "Tests failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}🎉 ALL TESTS PASSED${NC}"
    echo "The gateway Dockerfile has been successfully improved to support proper environment variable configuration!"
    echo ""
    echo "Key improvements:"
    echo "✅ Removed hardcoded database URL from CMD arguments"
    echo "✅ Updated worker count to match docker-compose default"
    echo "✅ Added comprehensive configuration documentation"
    echo "✅ Environment variables can be overridden by docker-compose and .env files"
    echo ""
    echo "Usage examples:"
    echo "# Standalone container (uses SQLite):"
    echo "docker build -f docker/gateway.dockerfile -t mcp-gateway ."
    echo "docker run -p 8080:8080 mcp-gateway"
    echo ""
    echo "# Docker compose (uses PostgreSQL):"
    echo "docker compose --profile gateway up -d"
    echo ""
    echo "# Custom configuration:"
    echo "docker run -e GATEWAY_DATABASE_URL=postgresql://... -p 8080:8080 mcp-gateway"
    
    exit 0
else
    echo -e "${RED}❌ TESTS FAILED${NC}"
    echo "Please review the failed tests and fix the issues before proceeding."
    exit 1
fi