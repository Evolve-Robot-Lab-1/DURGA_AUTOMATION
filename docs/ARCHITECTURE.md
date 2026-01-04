# DURGA AI - Complete System Architecture

## Overview

DURGA AI is a multi-tenant SaaS platform that serves as an "AI Chief of Staff" for business owners. It automates email campaigns, WhatsApp messaging, form collection, and business intelligence.

## System Components

### 1. Dashboard (Port 8080)

**Technology:** WordPress + Docker

The central hub that provides:
- Workspace navigation (Gmail, WhatsApp, Forms, etc.)
- Business settings management
- Analytics overview
- User authentication flow

### 2. DURGA_AUTH (Port 3001)

**Technology:** Cloudflare Workers + Hono + D1 + Drizzle ORM

Centralized authentication service:
- JWT-based authentication
- 15-minute access tokens, 7-day refresh tokens
- Multi-tenant business context
- Serves all workspaces

**Token Structure:**
```json
{
  "sub": "user_id",
  "bid": "business_id",
  "role": "owner|member",
  "exp": 1234567890,
  "iat": 1234567890
}
```

### 3. Brain API / Sales_AGENT (Port 3002)

**Technology:** Cloudflare Workers + D1

Central data hub containing:
- Company settings (name, logo, WhatsApp keyword, UPI ID)
- Knowledge base (intents, responses)
- Products catalog
- Business flows
- Campaign data

**Key Endpoints:**
```
GET  /api/company/keyword/:keyword  - Public keyword lookup (no auth)
GET  /api/knowledge                 - List knowledge items
POST /api/knowledge                 - Create knowledge item
GET  /api/products                  - List products
POST /api/products                  - Create product
GET  /api/v1/brain/context          - AI context for workspaces
GET  /api/v1/brain/search?q=        - Unified search
```

### 4. Claude Bridge (Port 3003)

**Technology:** Node.js + Claude CLI

AI processing layer that:
- Uses Claude CLI instead of API (no API key needed)
- Autonomous polling for Gmail, WhatsApp, Forms
- Event queue for user approval
- Browser automation control

**Key Endpoints:**
```
POST /ask                 - Query Claude
GET  /inbox               - Fetch emails
GET  /events              - Event queue
POST /events/:id/approve  - Approve action
GET  /tokens              - Token usage
POST /config              - Update settings
GET  /browser/status      - Automation status
POST /browser/action      - Execute action
```

### 5. WhatsApp Bot (Port 3004)

**Technology:** Cloudflare Workers + KV

WhatsApp Business API integration:
- Keyword-based business routing
- Multi-tenant message handling
- Dynamic response from knowledge base
- Campaign message sending

**Routing Logic:**
```
User sends: "Hi KEYWORD"
→ Extract KEYWORD
→ Lookup business by keyword in Brain API
→ Route to correct business context
→ Respond with business-specific content
```

### 6. Gmail Workspace (Port 5002)

**Technology:** Flask + SQLite + OAuth2

Email campaign management:
- OAuth2 Google authentication
- Campaign creation and scheduling
- Template management
- Analytics and tracking
- Bulk email sending

### 7. FORM_SPACE (Port 5173)

**Technology:** React + Vite + Tailwind (Frontend), Hono on Workers (API)

Payment-first form builder:
- Three creation modes: Templates, AI Builder, Block Editor
- UPI payment integration (per-business UPI from Brain API)
- Payment state tracking
- Follow-up reminders

**Form Templates:**
1. Quick Payment
2. Service Booking
3. Price Confirmation
4. Quotation Request
5. Training Registration
6. Event Registration

### 8. ConversationAI (Port 3006)

**Technology:** Cloudflare Workers + Vectorize

Advanced conversation engine:
- RAG (Retrieval-Augmented Generation)
- Intent routing
- Context memory management
- Multi-LLM provider support

## Data Flow

```
┌──────────────────────────────────────────────────────────────────────┐
│                         User Request                                  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         DURGA_AUTH                                    │
│  1. Validate JWT token                                               │
│  2. Extract user_id and business_id                                  │
│  3. Verify user belongs to business                                  │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                         Brain API                                     │
│  1. Load business context (settings, knowledge)                      │
│  2. Filter all data by business_id                                   │
│  3. Return business-specific response                                │
└───────────────────────────────┬──────────────────────────────────────┘
                                │
                ┌───────────────┼───────────────┐
                │               │               │
                ▼               ▼               ▼
         ┌──────────┐    ┌──────────┐    ┌──────────┐
         │ WhatsApp │    │  Gmail   │    │  Forms   │
         │   Bot    │    │ Workspace│    │  Builder │
         └──────────┘    └──────────┘    └──────────┘
                │               │               │
                └───────────────┼───────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Claude Bridge                                   │
│  1. Receive action request                                           │
│  2. Spawn Claude CLI process                                         │
│  3. Process with AI                                                  │
│  4. Execute browser automation if needed                             │
└──────────────────────────────────────────────────────────────────────┘
```

## Database Schema

### company_settings
```sql
business_id       TEXT PRIMARY KEY
company_name      TEXT
whatsapp_keyword  TEXT UNIQUE    -- For routing
upi_id            TEXT           -- For payments
phone             TEXT
logo_url          TEXT
created_at        TIMESTAMP
updated_at        TIMESTAMP
```

### knowledge
```sql
id                TEXT PRIMARY KEY
business_id       TEXT           -- Foreign key
intent            TEXT
keywords          TEXT[]
response          TEXT
category          TEXT
created_at        TIMESTAMP
```

### products
```sql
id                TEXT PRIMARY KEY
business_id       TEXT           -- Foreign key
name              TEXT
description       TEXT
price             DECIMAL
currency          TEXT
active            BOOLEAN
created_at        TIMESTAMP
```

## Security Model

### Authentication Flow
```
1. User logs in via DURGA_AUTH
2. Receives JWT with user_id + business_id
3. All API requests include JWT in Authorization header
4. Each service validates JWT and extracts business_id
5. All queries filtered by business_id
```

### Business Isolation
```
- Every table has business_id as primary/foreign key
- Default behavior: DENY access across businesses
- No cross-business data access possible
- Switching workspace does NOT switch business context
```

### API Validation
```python
def validate_request(request):
    user_id = extract_user_id(request.jwt)
    business_id = extract_business_id(request.jwt)

    # Verify user belongs to business
    if not user_in_business(user_id, business_id):
        raise AuthorizationError("Access denied")

    # All subsequent queries use business_id
    return business_id
```

## Deployment

### Production URLs
| Service | URL |
|---------|-----|
| Dashboard | https://durgaai.com |
| Auth | https://auth.durgaai.com |
| Brain API | https://api.durgaai.com |
| WhatsApp | https://whatsapp.durgaai.com |
| Gmail | https://mailbot.durgaai.com |
| Forms | https://forms.durgaai.com |

### Local Development Ports
| Port | Service |
|------|---------|
| 3001 | DURGA_AUTH |
| 3002 | Brain API |
| 3003 | Claude Bridge |
| 3004 | WhatsApp Bot |
| 3005 | Session Manager |
| 5002 | Gmail Workspace |
| 5173 | FORM_SPACE |
| 8080 | Dashboard |

## Start Script

Use the master start script to launch all services:

```bash
./start-durga.sh all      # Start everything
./start-durga.sh status   # Check service status
./start-durga.sh stop     # Stop all services
./start-durga.sh attach   # Attach to tmux session
```

Individual services:
```bash
./start-durga.sh auth     # Start DURGA_AUTH only
./start-durga.sh brain    # Start Brain API only
./start-durga.sh forms    # Start FORM_SPACE only
./start-durga.sh whatsapp # Start WhatsApp bot only
./start-durga.sh gmail    # Start Gmail workspace only
./start-durga.sh ai       # Start ConversationAI only
./start-durga.sh task     # Start Claude Bridge only
```
