# DURGA AI - Automation Platform

**AI Chief of Staff for Business Owners**

A comprehensive multi-tenant SaaS platform providing AI-powered automation for email campaigns, WhatsApp messaging, form building, and business intelligence.

## System Architecture

```
                              ┌─────────────────────────────────────┐
                              │         WordPress Dashboard          │
                              │            (Port 8080)               │
                              │    Central Hub for all workspaces    │
                              └──────────────────┬──────────────────┘
                                                 │
                    ┌────────────────────────────┼────────────────────────────┐
                    │                            │                            │
                    ▼                            ▼                            ▼
         ┌──────────────────┐        ┌──────────────────┐        ┌──────────────────┐
         │   DURGA_AUTH     │        │   Brain API      │        │  Claude Bridge   │
         │   (Port 3001)    │        │   (Port 3002)    │        │   (Port 3003)    │
         │                  │        │                  │        │                  │
         │  JWT Auth        │        │  Central Data    │        │  AI Processing   │
         │  User Sessions   │◄──────►│  Knowledge Base  │◄──────►│  Claude CLI      │
         │  Multi-tenant    │        │  Company Config  │        │  No API Key!     │
         └──────────────────┘        └────────┬─────────┘        └──────────────────┘
                                              │
              ┌───────────────┬───────────────┼───────────────┬───────────────┐
              │               │               │               │               │
              ▼               ▼               ▼               ▼               ▼
    ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
    │  WhatsApp   │  │   Gmail     │  │ FORM_SPACE  │  │  Browser    │  │Conversation │
    │    Bot      │  │  Workspace  │  │             │  │ Automation  │  │     AI      │
    │ (Port 3004) │  │ (Port 5002) │  │ (Port 5173) │  │  Scripts    │  │ (Port 3006) │
    │             │  │             │  │             │  │             │  │             │
    │ - Keywords  │  │ - Campaigns │  │ - Forms     │  │ - Inbox     │  │ - RAG       │
    │ - Routing   │  │ - Templates │  │ - Payments  │  │ - Reply     │  │ - Routing   │
    │ - Multi-biz │  │ - Analytics │  │ - Templates │  │ - Sessions  │  │ - Memory    │
    └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
              │               │               │               │               │
              └───────────────┴───────────────┴───────────────┴───────────────┘
                                              │
                                              ▼
                              ┌─────────────────────────────────────┐
                              │        Playwright Browser            │
                              │   Headless automation for all tasks  │
                              └─────────────────────────────────────┘
```

## Core Components

| Service | Port | Technology | Purpose |
|---------|------|------------|---------|
| **Dashboard** | 8080 | WordPress + Docker | Central hub, workspace navigation |
| **DURGA_AUTH** | 3001 | Cloudflare Workers + D1 | JWT authentication, multi-tenant |
| **Brain API** | 3002 | Cloudflare Workers + D1 | Central data, knowledge base |
| **Claude Bridge** | 3003 | Node.js + Claude CLI | AI processing without API key |
| **WhatsApp Bot** | 3004 | Cloudflare Workers + KV | Keyword routing, multi-business |
| **Gmail Workspace** | 5002 | Flask + SQLite | Email campaigns, templates |
| **FORM_SPACE** | 5173 | React + Vite + Hono | Payment forms, UPI integration |
| **ConversationAI** | 3006 | Workers + Vectorize | RAG, intent routing |

## What's in This Repo

This repository contains the **automation layer** of DURGA:

```
DURGA_AUTOMATION/
├── README.md                    # This file
├── browser_automation/          # Python browser automation scripts
│   ├── campaign_auto.py         # Full campaign automation CLI
│   ├── marketing_campaign.py    # Quick campaign runner
│   ├── ask_durga_marketing.py   # Interactive AI assistant
│   ├── open_gmail_inbox.py      # Gmail inbox automation
│   ├── durga_controller.py      # REST API (port 3004)
│   ├── session_manager.py       # Session API (port 3005)
│   ├── requirements.txt         # Python dependencies
│   └── campaign_input/          # Campaign data files
│
├── claude-bridge/               # Node.js AI bridge server
│   ├── server.js                # Main server (port 3003)
│   └── package.json             # Node dependencies
│
├── docs/                        # Architecture documentation
│   ├── ARCHITECTURE.md          # Detailed system architecture
│   ├── MULTI_TENANT.md          # Multi-tenant design
│   └── API_REFERENCE.md         # API endpoints reference
│
└── scripts/
    └── start-services.sh        # Start all automation services
```

## Prerequisites

- **Python 3.11+**
- **Node.js 18+**
- **Claude Code CLI** (installed and authenticated)
- **Playwright** (for browser automation)

### Install Claude Code CLI

```bash
# Install globally
npm install -g @anthropic-ai/claude-code

# Authenticate (one-time)
claude login
```

## Quick Start

### 1. Clone & Setup

```bash
git clone <repo-url>
cd DURGA_AUTOMATION

# Setup Python environment
cd browser_automation
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Setup Claude Bridge
cd ../claude-bridge
npm install
```

### 2. Start Services

```bash
# Terminal 1: Start Claude Bridge (AI processing)
cd claude-bridge
node server.js

# Terminal 2: Run automation scripts
cd browser_automation
source venv/bin/activate
python campaign_auto.py scan
```

### 3. Test the Setup

```bash
# Check Claude Bridge health
curl http://localhost:3003/health

# Send a test query
curl -X POST http://localhost:3003/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "show inbox"}'
```

## Claude Bridge - The AI Core

The Claude Bridge is the key innovation - it uses **Claude CLI** instead of the Anthropic API, meaning:

- **No API key required** - Uses your Claude Code subscription
- **No token costs** - Included in Claude Code pricing
- **Local processing** - Runs on your machine

### How It Works

```javascript
// Instead of API calls, we spawn Claude CLI
const claude = spawn('claude', ['--print']);
claude.stdin.write(prompt);
// Response comes from your authenticated Claude Code
```

### Bridge Features

- **Autonomous Polling** - Monitors Gmail (60s), WhatsApp (30s), Forms (120s)
- **Event Queue** - Queues actions for user approval
- **Token Tracking** - Daily usage monitoring
- **Browser Control** - Direct control of Playwright automation

### Bridge Endpoints

```
POST /ask                 - Natural language query to Claude
GET  /inbox               - Fetch emails
GET  /events              - Event queue
POST /events/:id/approve  - Approve action
POST /events/:id/dismiss  - Dismiss event
GET  /tokens              - Token usage stats
POST /config              - Update settings
GET  /health              - Health check

# Browser Control
GET  /browser/status      - Automation status
POST /browser/action      - Execute action
POST /browser/take-control - Manual mode
POST /browser/stop        - Stop session
```

## Browser Automation Scripts

### Campaign Automation

```bash
# Scan for campaign files
python campaign_auto.py scan

# Create campaign
python campaign_auto.py create --csv contacts.csv --company "Your Company" --goal partnership

# Control campaign
python campaign_auto.py status
python campaign_auto.py pause
python campaign_auto.py resume
python campaign_auto.py analytics
```

### Gmail Inbox

```bash
# List emails
python3 open_gmail_inbox.py list

# View email
python3 open_gmail_inbox.py view 3

# Reply with template
python3 open_gmail_inbox.py reply 4 job_application

# Templates: job_application, interview_invite, general_response
```

### Interactive Assistant

```bash
python ask_durga_marketing.py

# Then type natural language:
> show inbox
> view email 1
> reply to email 2
> create campaign
```

## Multi-Tenant Architecture

DURGA is built for multiple businesses on a single platform:

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Authentication                       │
│  "Login identifies WHO the user is"                             │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Business Context                         │
│  "Business ID defines WHAT world they operate in"               │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │ Business A  │  │ Business B  │  │ Business C  │             │
│  │             │  │             │  │             │             │
│  │ - Keyword   │  │ - Keyword   │  │ - Keyword   │             │
│  │ - UPI ID    │  │ - UPI ID    │  │ - UPI ID    │             │
│  │ - Knowledge │  │ - Knowledge │  │ - Knowledge │             │
│  │ - Campaigns │  │ - Campaigns │  │ - Campaigns │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
└─────────────────────────────────────────────────────────────────┘
```

**Key Principle:** Every database query is filtered by `business_id`. Switching workspaces does NOT switch business context.

## Service Ports Reference

| Port | Service | Description |
|------|---------|-------------|
| 3001 | DURGA_AUTH | Authentication service |
| 3002 | Brain API | Central data hub |
| 3003 | Claude Bridge | AI processing |
| 3004 | WhatsApp Bot / Durga Controller | Messaging / Browser API |
| 3005 | Session Manager | Browser sessions |
| 5002 | Gmail Workspace | Email campaigns |
| 5173 | FORM_SPACE | Form builder |
| 8080 | Dashboard | WordPress hub |

## Configuration

### Environment Variables

Create `.env` in `browser_automation/`:

```bash
# Optional - only if using direct API calls
ANTHROPIC_API_KEY=your_key_here
```

**Note:** Claude Bridge doesn't need API key - it uses Claude CLI.

### Claude Bridge Config

Update via API:

```bash
curl -X POST http://localhost:3003/config \
  -H "Content-Type: application/json" \
  -d '{
    "polling": true,
    "autoProcess": false,
    "tokenLimit": 100000
  }'
```

## Troubleshooting

### Claude CLI Not Working

```bash
# Check installation
which claude

# Reinstall if needed
npm install -g @anthropic-ai/claude-code

# Re-authenticate
claude login
```

### Browser Automation Issues

```bash
# Reinstall Playwright
playwright install chromium --force
playwright install-deps  # Linux only

# Clear session state
rm -rf /tmp/durga_browser_session
rm /tmp/durga_inbox_state.json
```

### Service Not Starting

```bash
# Check if port is in use
lsof -i :3003

# Kill existing process
kill -9 $(lsof -t -i:3003)
```

## Related Repositories

The full DURGA platform consists of:

| Repository | Purpose |
|------------|---------|
| **DURGA_AUTOMATION** | This repo - Browser automation & Claude Bridge |
| DURGA_AUTH | Authentication service |
| Sales_AGENT | Brain API - Central data |
| FORM_SPACE | Payment-first form builder |
| whatsapp-bot | WhatsApp integration |
| durga_site | WordPress dashboard |
| ConversationAI | RAG & intent routing |

## License

Proprietary - Evolve Robot Lab

## Support

For issues or questions, contact the Evolve Robot Lab team.
