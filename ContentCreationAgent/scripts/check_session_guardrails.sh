#!/bin/bash
# Database Session Management Guardrails - Local Check Script
# Run this before committing to ensure session management patterns are correct

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

ERROR_COUNT=0

echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}🔒 Database Session Management Guardrails Check${NC}"
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check 1: Invalid Depends(get_session)
echo -n "🔍 Checking for invalid Depends(get_session)..."
if grep -r "Depends(get_session)" backend/api --include="*.py" | grep -v "# NEVER use" > /dev/null 2>&1; then
    echo -e " ${RED}❌ FAILED${NC}"
    echo -e "   ${RED}Found invalid Depends(get_session) in:${NC}"
    grep -rn "Depends(get_session)" backend/api --include="*.py" | grep -v "# NEVER use" | sed 's/^/   - /'
    ((ERROR_COUNT++))
else
    echo -e " ${GREEN}✅ PASSED${NC}"
fi

# Check 2: Invalid Depends(get_db)
echo -n "🔍 Checking for invalid Depends(get_db)..."
if grep -r "Depends(get_db)" backend/api --include="*.py" | grep -v "# NEVER use" > /dev/null 2>&1; then
    echo -e " ${RED}❌ FAILED${NC}"
    echo -e "   ${RED}Found invalid Depends(get_db) in:${NC}"
    grep -rn "Depends(get_db)" backend/api --include="*.py" | grep -v "# NEVER use" | sed 's/^/   - /'
    ((ERROR_COUNT++))
else
    echo -e " ${GREEN}✅ PASSED${NC}"
fi

# Check 3: Invalid Depends(get_async_session)
echo -n "🔍 Checking for invalid Depends(get_async_session)..."
if grep -r "Depends(get_async_session)" backend/ --include="*.py" | grep -v "# NEVER use" > /dev/null 2>&1; then
    echo -e " ${RED}❌ FAILED${NC}"
    echo -e "   ${RED}Found invalid Depends(get_async_session) in:${NC}"
    grep -rn "Depends(get_async_session)" backend/ --include="*.py" | grep -v "# NEVER use" | sed 's/^/   - /'
    ((ERROR_COUNT++))
else
    echo -e " ${GREEN}✅ PASSED${NC}"
fi

# Check 4: Canonical helpers exist
echo -n "🔍 Verifying canonical session helpers..."
if ! grep -q "async def get_db_session():" backend/database/models.py; then
    echo -e " ${RED}❌ FAILED${NC}"
    echo -e "   ${RED}get_db_session() not found in models.py!${NC}"
    ((ERROR_COUNT++))
elif ! grep -q "async def open_session():" backend/database/models.py; then
    echo -e " ${RED}❌ FAILED${NC}"
    echo -e "   ${RED}open_session() not found in models.py!${NC}"
    ((ERROR_COUNT++))
else
    echo -e " ${GREEN}✅ PASSED${NC}"
fi

# Check 5: LangGraph reserved fields
echo -n "🔍 Checking for LangGraph reserved field 'checkpoint_id'..."
if grep -r "checkpoint_id:" backend/state --include="*.py" | grep -v "checkpoint_ref" > /dev/null 2>&1; then
    echo -e " ${RED}❌ FAILED${NC}"
    echo -e "   ${RED}Found 'checkpoint_id' in state schema (use 'checkpoint_ref' instead):${NC}"
    grep -rn "checkpoint_id:" backend/state --include="*.py" | grep -v "checkpoint_ref" | sed 's/^/   - /'
    ((ERROR_COUNT++))
else
    echo -e " ${GREEN}✅ PASSED${NC}"
fi

# Check 6: Protective comments
echo -n "🔍 Verifying protective comments..."
if ! grep -q "DATABASE SESSION MANAGEMENT GUARDRAILS" backend/api/routes.py; then
    echo -e " ${YELLOW}⚠️  WARNING${NC}"
    echo -e "   ${YELLOW}Protective comment missing in routes.py${NC}"
elif ! grep -q "DATABASE SESSION MANAGEMENT GUARDRAILS" backend/api/chat_routes.py; then
    echo -e " ${YELLOW}⚠️  WARNING${NC}"
    echo -e "   ${YELLOW}Protective comment missing in chat_routes.py${NC}"
else
    echo -e " ${GREEN}✅ PASSED${NC}"
fi

echo ""
echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

if [ $ERROR_COUNT -gt 0 ]; then
    echo -e "${RED}❌ GUARDRAILS FAILED: $ERROR_COUNT error(s) detected${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "${YELLOW}RULES:${NC}"
    echo -e "${YELLOW}1. FastAPI routes MUST use: session: AsyncSession = Depends(get_db_session)${NC}"
    echo -e "${YELLOW}2. Background tasks MUST use: async with open_session() as session:${NC}"
    echo -e "${YELLOW}3. NEVER use get_session, get_db, or get_async_session${NC}"
    echo -e "${YELLOW}4. State schemas MUST use 'checkpoint_ref' not 'checkpoint_id'${NC}"
    echo ""
    exit 1
else
    echo -e "${GREEN}✅ All guardrails passed! Safe to commit.${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
fi
