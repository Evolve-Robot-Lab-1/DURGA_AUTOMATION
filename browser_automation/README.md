# Browser Automation - DurgaAI Platform

A comprehensive browser automation and email campaign management system for the Evolve Robot Lab's DurgaAI platform. Provides AI-powered email campaigns, inbox management, and marketing automation.

## Features

- **Campaign Automation** - AI-powered bulk email campaigns with document parsing
- **Inbox Management** - Automated email handling, viewing, and replies
- **Natural Language Control** - Interactive AI assistant for marketing tasks
- **Claude Bridge** - Uses Claude CLI (no API key needed) for AI processing
- **REST API Services** - Programmatic control via HTTP endpoints
- **Persistent Sessions** - Stateful browser sessions with context preservation
- **Autonomous Polling** - Auto-monitors Gmail, WhatsApp, and form submissions

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Claude Bridge (Port 3003)               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Uses Claude CLI (not API) - No API key required!   │   │
│  │  spawn('claude', ['--print']) → AI responses        │   │
│  └─────────────────────────────────────────────────────┘   │
│                            ↓                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Gmail Poll   │  │ WhatsApp Poll│  │ Forms Poll   │     │
│  │ (60s)        │  │ (30s)        │  │ (120s)       │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│              Browser Automation Scripts                      │
│  campaign_auto.py │ open_gmail_inbox.py │ durga_controller  │
└─────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                    Playwright Browser                        │
│              DurgaMail (5002) │ Gmail │ WhatsApp            │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Python 3.11+
- Node.js 18+
- **Claude Code CLI** (installed and authenticated)
- LibreOffice (optional, for ODT to DOCX conversion)

### Installing Claude Code CLI

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Authenticate (one-time setup)
claude login
```

## Installation

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd browser_automation
```

### 2. Create Python Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt

# Install Playwright browsers
playwright install chromium
playwright install-deps  # Linux only - installs system dependencies
```

Or use the setup script:

```bash
chmod +x setup_browser_use.sh
./setup_browser_use.sh
```

### 4. Install Claude Bridge Dependencies

```bash
cd ../Durga_Task/claude-bridge
npm install
```

### 5. Configure Environment (Optional)

Create a `.env` file if you want to use direct API calls in some scripts:

```bash
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

**Note:** The Claude Bridge uses Claude CLI, so no API key is needed for the bridge.

## Project Structure

```
browser_automation/
├── Core Scripts
│   ├── campaign_auto.py          # Full campaign automation CLI
│   ├── marketing_campaign.py     # Simplified campaign runner
│   ├── ask_durga_marketing.py    # Interactive AI assistant
│   ├── open_gmail_inbox.py       # Gmail inbox automation
│   ├── durga_controller.py       # REST API backend (port 3004)
│   ├── session_manager.py        # Session manager API (port 3005)
│   └── login_test.py             # AI-powered login testing
│
├── Configuration
│   ├── .env                      # API keys (optional)
│   ├── setup_browser_use.sh      # Setup script
│   ├── requirements.txt          # Python dependencies
│   └── .gitignore
│
├── Data
│   └── campaign_input/           # Campaign files (CSV, attachments)
│       ├── *.csv                 # Recipient lists
│       ├── attachments/          # Email attachments
│       └── converted/            # Auto-converted documents
│
└── static/
    └── durga_chat_widget.html    # Chat UI widget

../Durga_Task/claude-bridge/
├── server.js                     # Claude Bridge server (port 3003)
├── package.json                  # Node.js dependencies
└── state.json                    # Persistent state (auto-generated)
```

## Quick Start

### Start All Services

```bash
# Terminal 1: Start Claude Bridge
cd ../Durga_Task/claude-bridge
node server.js

# Terminal 2: Activate Python env and run scripts
cd browser_automation
source venv/bin/activate
python campaign_auto.py scan
```

---

## Claude Bridge (Port 3003)

The Claude Bridge is the core AI service that uses **Claude CLI** instead of the API.

### Start the Bridge

```bash
cd ../Durga_Task/claude-bridge
node server.js
```

### Key Features

- **No API Key Required** - Uses your Claude Code CLI authentication
- **Autonomous Polling** - Auto-monitors Gmail (60s), WhatsApp (30s), Forms (120s)
- **Event Queue** - Queues events for approval before action
- **Token Tracking** - Daily usage limits (default: 100,000 tokens)
- **Browser Control** - Direct control of browser automation

### Bridge Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/ask` | Send natural language query to Claude |
| GET | `/inbox` | Fetch emails from Gmail |
| GET | `/events` | Get all events in queue |
| GET | `/events/pending` | Get pending events only |
| POST | `/events/:id/approve` | Approve an event action |
| POST | `/events/:id/dismiss` | Dismiss an event |
| DELETE | `/events/clear` | Clear event queue |
| GET | `/tokens` | Get token usage stats |
| GET | `/config` | Get configuration |
| POST | `/config` | Update configuration |
| GET | `/health` | Health check |

### Browser Control Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/browser/status` | Get browser automation status |
| GET | `/browser/screenshot` | Get latest screenshot |
| POST | `/browser/pause` | Pause automation |
| POST | `/browser/resume` | Resume automation |
| POST | `/browser/stop` | Stop browser session |
| POST | `/browser/take-control` | Switch to manual mode |
| POST | `/browser/return-control` | Return to auto mode |
| POST | `/browser/action` | Execute browser action |

### Webhook Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/webhook/gmail` | Receive Gmail events |
| POST | `/webhook/whatsapp` | Receive WhatsApp events |
| POST | `/webhook/forms` | Receive form submissions |

### Natural Language Commands via `/ask`

```bash
# Example queries you can send to POST /ask
curl -X POST http://localhost:3003/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "show inbox"}'

curl -X POST http://localhost:3003/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "view email #2"}'

curl -X POST http://localhost:3003/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "reply to email #3 with job application template"}'
```

### Configuration

Update settings via POST `/config`:

```bash
curl -X POST http://localhost:3003/config \
  -H "Content-Type: application/json" \
  -d '{"polling": true, "autoProcess": false, "tokenLimit": 50000}'
```

---

## Python Scripts

### 1. Campaign Automation (`campaign_auto.py`)

Full-featured campaign builder with AI chatbot integration.

```bash
# Scan campaign_input folder for files
python campaign_auto.py scan

# Create campaign with CSV and goal
python campaign_auto.py create --csv contacts.csv --company "Evolve Robot" --goal partnership

# Upload recipients
python campaign_auto.py upload --csv file.csv

# Generate AI emails
python campaign_auto.py generate --company "Your Company"

# Campaign control
python campaign_auto.py status
python campaign_auto.py pause
python campaign_auto.py resume
python campaign_auto.py cancel
python campaign_auto.py analytics
```

**Campaign Goals:**
- `vc_funding` - Seeking VC Funding
- `partnership` - Partnership Opportunities
- `sales` - Selling AI/Robotics Services
- `customers` - Customer Acquisition
- `launch` - Product Launch

---

### 2. Marketing Campaign (`marketing_campaign.py`)

Simplified quick campaign runner.

```bash
# With CSV file
python marketing_campaign.py --csv investors.csv --goal vc_funding

# With direct emails
python marketing_campaign.py --emails "john@company.com,jane@startup.com" --goal partnership
```

---

### 3. Interactive AI Assistant (`ask_durga_marketing.py`)

Natural language control of DurgaMail.

```bash
python ask_durga_marketing.py
```

**Example commands:**
- `show inbox` / `list emails`
- `view email 1`
- `reply to email 2`
- `create campaign`
- `show analytics`
- `start campaign`

---

### 4. Gmail Inbox Automation (`open_gmail_inbox.py`)

Stateful email session management.

```bash
# List all emails
python3 open_gmail_inbox.py list

# View specific email
python3 open_gmail_inbox.py view 3

# Reply with template
python3 open_gmail_inbox.py reply 4 job_application

# Close session
python3 open_gmail_inbox.py close
```

**Reply Templates:**
- `job_application` - Job offer response
- `job_acknowledgment` - Interview confirmation
- `interview_invite` - Interview scheduling
- `general_response` - Generic response
- `internship_completion` - Internship completion

---

### 5. REST API Controllers

#### Durga Controller (Port 3004)

```bash
python durga_controller.py
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/api/inbox` | Get inbox emails |
| GET | `/api/inbox/<id>` | Get specific email |
| POST | `/api/inbox/reply` | Reply to email |
| POST | `/api/inbox/refresh` | Refresh inbox |
| GET | `/api/campaign/status` | Campaign status |
| POST | `/api/campaign/create` | Create campaign |
| POST | `/api/campaign/pause` | Pause campaign |
| POST | `/api/campaign/resume` | Resume campaign |
| GET | `/api/analytics` | Get analytics |
| POST | `/api/ask` | Natural language query |

#### Session Manager (Port 3005)

```bash
python session_manager.py
```

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/status` | All session states |
| GET | `/email/status` | Email session state |
| GET | `/email/emails` | Email list |
| POST | `/email/start` | Start email session |
| POST | `/email/action` | Execute action |
| POST | `/email/stop` | Stop email session |

---

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| Claude Bridge | 3003 | AI processing via Claude CLI |
| Durga Controller | 3004 | Browser automation API |
| Session Manager | 3005 | Session management API |
| DurgaMail | 5002 | Email workspace |
| DurgaAI Dashboard | 8080 | Main dashboard |

---

## Campaign Input Files

Place your campaign files in the `campaign_input/` directory:

- **Recipient Lists:** CSV files with email addresses
- **Campaign Memos:** TXT, PDF, DOCX, or ODT files
- **Attachments:** Place in `campaign_input/attachments/`

The system auto-detects and processes these files.

---

## Dependencies

### Python (requirements.txt)

**Core:**
- `playwright` - Browser automation
- `flask` / `flask-cors` - Web framework
- `browser-use` - AI-powered browser control

**Document Processing:**
- `pypdf` - PDF handling
- `python-docx` - Word documents
- `beautifulsoup4` - HTML parsing

**Google Integration:**
- `google-auth`
- `google-auth-oauthlib`
- `google-api-python-client`

**Utilities:**
- `python-dotenv` - Environment variables
- `aiohttp` - Async HTTP
- `pandas` - Data processing

### Node.js (Claude Bridge)

- `http` / `https` (built-in)
- `child_process` (built-in) - spawns Claude CLI
- `fs` / `path` (built-in)

---

## Troubleshooting

### Claude CLI Not Found

```bash
# Verify Claude CLI is installed
which claude

# If not installed
npm install -g @anthropic-ai/claude-code

# Authenticate
claude login
```

### Playwright Browser Issues

```bash
# Reinstall browsers
playwright install chromium --force

# Install system dependencies (Linux)
playwright install-deps
```

### Permission Errors

```bash
# Make scripts executable
chmod +x *.py setup_browser_use.sh
```

### Missing Dependencies

```bash
pip install -r requirements.txt
# Or reinstall specific packages
pip install --force-reinstall playwright browser-use
```

### Session State Issues

```bash
# Clear session state
rm -rf /tmp/durga_browser_session
rm /tmp/durga_inbox_state.json

# Clear Claude Bridge state
rm ../Durga_Task/claude-bridge/state.json
```

### Token Limit Reached

```bash
# Reset daily limit via API
curl -X POST http://localhost:3003/config \
  -H "Content-Type: application/json" \
  -d '{"tokenLimit": 100000}'
```

---

## Security Notes

- The Claude Bridge uses your Claude Code CLI authentication (no API keys stored)
- Never commit `.env` files with API keys
- The `.gitignore` excludes sensitive files:
  - `venv/` - Virtual environment
  - `.env` - Environment variables
  - `*.png` - Screenshots
  - `__pycache__/` - Python cache
  - `state.json` - Bridge state

---

## License

Proprietary - Evolve Robot Lab

## Support

For issues or questions, contact the Evolve Robot Lab team.
