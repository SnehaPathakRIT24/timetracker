#!/bin/bash
# TimeTracker Mac Setup Script
# Run once per team member: bash setup_mac.sh

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== TimeTracker Mac Agent Setup ===${NC}"

# 1. Server URL
read -p "Server URL (e.g. https://yourserver.com or http://localhost:8000): " SERVER_URL
SERVER_URL=${SERVER_URL:-http://localhost:8000}

# 2. Auth
read -p "Your email: " EMAIL
read -s -p "Your password: " PASSWORD
echo

# 3. Login and get member ID
echo -e "\n${BLUE}Authenticating with server...${NC}"
RESPONSE=$(curl -s -X POST "$SERVER_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\": \"$EMAIL\", \"password\": \"$PASSWORD\"}")

TOKEN=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['access_token'])" 2>/dev/null)
MEMBER_ID=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['member']['id'])" 2>/dev/null)
MEMBER_NAME=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d['member']['name'])" 2>/dev/null)

if [ -z "$TOKEN" ]; then
  echo -e "${RED}Login failed. Check your credentials and server URL.${NC}"
  exit 1
fi

echo -e "${GREEN}Logged in as: $MEMBER_NAME (ID: $MEMBER_ID)${NC}"

# 4. Install Python deps
AGENT_DIR="$HOME/.timetracker"
mkdir -p "$AGENT_DIR"

echo -e "${BLUE}Installing Python dependencies...${NC}"
pip3 install --quiet requests pynput pyobjc-core pyobjc-framework-Cocoa pyobjc-framework-Quartz

# 5. Copy agent files
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cp -r "$PROJECT_ROOT/agent" "$AGENT_DIR/"

# 6. Write config to SQLite
python3 - <<PYEOF
import sys
sys.path.insert(0, '$AGENT_DIR')
from agent.common.local_db import init_db, set_config
init_db()
set_config('member_id', '$MEMBER_ID')
set_config('server_url', '$SERVER_URL')
print("Config saved.")
PYEOF

# 7. Create launchd plist for startup
PLIST_PATH="$HOME/Library/LaunchAgents/com.timetracker.agent.plist"
cat > "$PLIST_PATH" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.timetracker.agent</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(which python3)</string>
        <string>$AGENT_DIR/agent/mac/agent.py</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>TRACKER_SERVER_URL</key>
        <string>$SERVER_URL</string>
        <key>TRACKER_MEMBER_ID</key>
        <string>$MEMBER_ID</string>
        <key>PYTHONPATH</key>
        <string>$AGENT_DIR</string>
    </dict>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>$AGENT_DIR/agent.log</string>
    <key>StandardErrorPath</key>
    <string>$AGENT_DIR/agent_err.log</string>
</dict>
</plist>
PLIST

launchctl load "$PLIST_PATH" 2>/dev/null || true
launchctl start com.timetracker.agent 2>/dev/null || true

echo -e "\n${GREEN}✓ TimeTracker agent installed and started!${NC}"
echo -e "  → Logs: ${AGENT_DIR}/agent.log"
echo -e "  → Pause tracking: ${BLUE}Cmd+Shift+P${NC} (30 min)"
echo -e "  → Dashboard: ${BLUE}$SERVER_URL${NC}"
