#!/bin/bash
# Port Conflict Resolution Script
# Checks if required ports are available and clears them if needed

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Required ports
BACKEND_PORTS=(8006 8007)
FRONTEND_PORTS=(3006 3007)
DATABASE_PORTS=(5432 6333 6379 7870)

echo "================================================================================"
echo "PORT AVAILABILITY CHECK & RESOLUTION"
echo "================================================================================"
echo ""

# Function to check if port is in use
check_port() {
    local port=$1
    if command -v lsof &> /dev/null; then
        # macOS/Linux with lsof
        lsof -i :$port &> /dev/null
        return $?
    elif command -v netstat &> /dev/null; then
        # Windows/Linux with netstat
        netstat -ano | grep ":$port " &> /dev/null
        return $?
    else
        echo -e "${YELLOW}⚠️  Cannot check port $port (no lsof or netstat)${NC}"
        return 1
    fi
}

# Function to get process using port
get_port_process() {
    local port=$1
    if command -v lsof &> /dev/null; then
        lsof -i :$port -t 2>/dev/null || echo "unknown"
    elif command -v netstat &> /dev/null; then
        netstat -ano | grep ":$port " | awk '{print $5}' | head -1 || echo "unknown"
    else
        echo "unknown"
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local pid=$(get_port_process $port)

    if [ "$pid" != "unknown" ] && [ ! -z "$pid" ]; then
        echo -e "${YELLOW}  Killing process $pid on port $port...${NC}"
        kill -9 $pid 2>/dev/null || true
        sleep 1

        if check_port $port; then
            echo -e "${RED}  ❌ Failed to free port $port${NC}"
            return 1
        else
            echo -e "${GREEN}  ✅ Port $port freed${NC}"
            return 0
        fi
    fi
}

# Check backend ports (8006-8007)
echo "🔍 Checking backend ports (8006-8007)..."
BACKEND_PORT=""
for port in "${BACKEND_PORTS[@]}"; do
    if check_port $port; then
        echo -e "${YELLOW}  ⚠️  Port $port is in use by PID $(get_port_process $port)${NC}"

        # Ask to kill
        read -p "  Kill process on port $port? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill_port $port
            if ! check_port $port; then
                BACKEND_PORT=$port
                break
            fi
        fi
    else
        echo -e "${GREEN}  ✅ Port $port is available${NC}"
        BACKEND_PORT=$port
        break
    fi
done

if [ -z "$BACKEND_PORT" ]; then
    echo -e "${RED}❌ No available backend ports (8006-8007)${NC}"
    exit 1
fi

# Check frontend ports (3006-3007)
echo ""
echo "🔍 Checking frontend ports (3006-3007)..."
FRONTEND_PORT=""
for port in "${FRONTEND_PORTS[@]}"; do
    if check_port $port; then
        echo -e "${YELLOW}  ⚠️  Port $port is in use by PID $(get_port_process $port)${NC}"

        # Ask to kill
        read -p "  Kill process on port $port? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill_port $port
            if ! check_port $port; then
                FRONTEND_PORT=$port
                break
            fi
        fi
    else
        echo -e "${GREEN}  ✅ Port $port is available${NC}"
        FRONTEND_PORT=$port
        break
    fi
done

if [ -z "$FRONTEND_PORT" ]; then
    echo -e "${RED}❌ No available frontend ports (3006-3007)${NC}"
    exit 1
fi

# Check database ports
echo ""
echo "🔍 Checking database/service ports..."
for port in "${DATABASE_PORTS[@]}"; do
    if check_port $port; then
        echo -e "${YELLOW}  ⚠️  Port $port is in use (likely existing service)${NC}"
        read -p "  Kill process on port $port? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            kill_port $port
        fi
    else
        echo -e "${GREEN}  ✅ Port $port is available${NC}"
    fi
done

# Update docker-compose.yml with selected ports
echo ""
echo "================================================================================"
echo "📝 Updating docker-compose.yml with selected ports..."
echo "================================================================================"

# Backup docker-compose.yml
cp docker-compose.yml docker-compose.yml.backup

# Update backend port
sed -i.tmp "s/- \"[0-9]*:8000\"/- \"$BACKEND_PORT:8000\"/" docker-compose.yml

# Update frontend port
sed -i.tmp "s/- \"[0-9]*:8501\"/- \"$FRONTEND_PORT:8501\"/" docker-compose.yml

# Remove temp files
rm -f docker-compose.yml.tmp

echo ""
echo "================================================================================"
echo "✅ PORT CONFIGURATION COMPLETE"
echo "================================================================================"
echo ""
echo "Selected Ports:"
echo "  - Backend:  http://localhost:$BACKEND_PORT"
echo "  - Frontend: http://localhost:$FRONTEND_PORT"
echo ""
echo "Next Steps:"
echo "  1. Start services: docker-compose up -d"
echo "  2. Check status:   docker-compose ps"
echo "  3. View logs:      docker-compose logs -f backend"
echo ""
echo "To restore original ports, restore backup:"
echo "  mv docker-compose.yml.backup docker-compose.yml"
echo ""
echo "================================================================================"
