# DURGA AI - API Reference

## Claude Bridge (Port 3003)

The main AI processing service using Claude CLI.

### Core Endpoints

#### POST /ask
Send a natural language query to Claude.

**Request:**
```json
{
  "query": "show inbox",
  "context": "optional additional context"
}
```

**Response:**
```json
{
  "success": true,
  "response": {
    "message": "Here are your recent emails...",
    "type": "inbox",
    "actions": [],
    "sources": ["Gmail API"]
  },
  "tokenUsage": {
    "promptTokens": 150,
    "responseTokens": 200,
    "total": 350,
    "dailyTotal": 5000
  }
}
```

#### GET /inbox
Fetch emails directly from Gmail API.

**Response:**
```json
{
  "success": true,
  "emails": [
    {
      "id": "msg123",
      "from": "john@example.com",
      "subject": "Meeting Tomorrow",
      "snippet": "Hi, let's discuss...",
      "date": "2024-01-03"
    }
  ],
  "count": 10
}
```

#### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "Claude Bridge",
  "port": 3003,
  "polling": true,
  "pendingEvents": 3,
  "tokenUsage": {
    "today": 5000,
    "total": 150000,
    "lastReset": "2024-01-03"
  }
}
```

### Event Queue Endpoints

#### GET /events
Get all events in the queue.

**Response:**
```json
{
  "success": true,
  "events": [
    {
      "id": "gmail_abc123",
      "type": "new_email",
      "source": "gmail",
      "timestamp": "2024-01-03T10:00:00Z",
      "data": {
        "from": "john@example.com",
        "subject": "Hello"
      },
      "status": "pending",
      "suggestedAction": "Reply with acknowledgment"
    }
  ],
  "pending": 3,
  "total": 10
}
```

#### GET /events/pending
Get only pending events.

#### POST /events/:id/approve
Approve an event for action.

**Response:**
```json
{
  "success": true,
  "event": {
    "id": "gmail_abc123",
    "status": "approved",
    "approvedAt": "2024-01-03T10:05:00Z"
  }
}
```

#### POST /events/:id/dismiss
Dismiss an event.

#### DELETE /events/clear
Clear all events from queue.

### Token Management

#### GET /tokens
Get token usage statistics.

**Response:**
```json
{
  "success": true,
  "usage": {
    "today": 5000,
    "total": 150000,
    "lastReset": "2024-01-03"
  },
  "limit": 100000,
  "remaining": 95000
}
```

### Configuration

#### GET /config
Get current configuration.

**Response:**
```json
{
  "success": true,
  "config": {
    "polling": {
      "enabled": true,
      "intervals": {
        "gmail": 60000,
        "whatsapp": 30000,
        "forms": 120000
      }
    },
    "autoProcess": {
      "enabled": false,
      "requireApproval": true
    },
    "tokenTracking": {
      "enabled": true,
      "dailyLimit": 100000
    }
  }
}
```

#### POST /config
Update configuration.

**Request:**
```json
{
  "polling": true,
  "autoProcess": false,
  "tokenLimit": 50000
}
```

### Browser Control Endpoints

#### GET /browser/status
Get browser automation status.

**Response:**
```json
{
  "success": true,
  "browser": {
    "status": "idle",
    "lastAction": "list",
    "currentEmail": null,
    "hasScreenshot": true
  },
  "inbox": {
    "emails": [...],
    "current_view": "inbox"
  },
  "pendingEvents": 0
}
```

#### GET /browser/screenshot
Serve the latest screenshot as PNG image.

#### POST /browser/action
Execute a browser automation action.

**Request:**
```json
{
  "action": "view",
  "emailNum": 3,
  "template": null
}
```

**Actions:**
- `list` - List inbox emails
- `view` - View specific email
- `reply` - Reply to email (with optional template)
- `close` - Close browser session

**Templates:**
- `job_application`
- `job_acknowledgment`
- `interview_invite`
- `general_response`
- `internship_completion`

#### POST /browser/pause
Pause browser automation.

#### POST /browser/resume
Resume browser automation.

#### POST /browser/stop
Stop browser session completely.

#### POST /browser/take-control
Switch to manual mode (opens visible browser).

#### POST /browser/return-control
Return to automated mode.

### Webhook Endpoints

#### POST /webhook/gmail
Receive Gmail webhook events.

**Request:**
```json
{
  "type": "new_email",
  "messageId": "msg123",
  "from": "sender@example.com",
  "subject": "New message"
}
```

#### POST /webhook/whatsapp
Receive WhatsApp webhook events.

#### POST /webhook/forms
Receive form submission events.

---

## Durga Controller (Port 3004)

Python-based REST API for browser automation.

### Inbox Endpoints

#### GET /api/inbox
Get all inbox emails.

**Response:**
```json
{
  "success": true,
  "emails": [
    {
      "id": 1,
      "from": "john@example.com",
      "subject": "Meeting",
      "date": "2024-01-03",
      "snippet": "Let's discuss..."
    }
  ]
}
```

#### GET /api/inbox/:id
Get specific email details.

#### POST /api/inbox/reply
Reply to an email.

**Request:**
```json
{
  "emailId": 1,
  "message": "Thank you for your email...",
  "template": "general_response"
}
```

#### POST /api/inbox/refresh
Refresh inbox data.

### Campaign Endpoints

#### GET /api/campaign/status
Get current campaign status.

**Response:**
```json
{
  "success": true,
  "campaign": {
    "id": "camp123",
    "name": "Q1 Outreach",
    "status": "running",
    "sent": 150,
    "total": 500,
    "errors": 2
  }
}
```

#### POST /api/campaign/create
Create a new campaign.

**Request:**
```json
{
  "name": "Q1 Outreach",
  "recipients": ["email1@example.com", "email2@example.com"],
  "goal": "partnership",
  "company": "Evolve Robot Lab"
}
```

#### POST /api/campaign/pause
Pause running campaign.

#### POST /api/campaign/resume
Resume paused campaign.

### Analytics

#### GET /api/analytics
Get campaign analytics.

**Response:**
```json
{
  "success": true,
  "analytics": {
    "totalSent": 1500,
    "totalOpened": 800,
    "totalReplied": 150,
    "openRate": 53.3,
    "replyRate": 10.0
  }
}
```

### Natural Language

#### POST /api/ask
Send natural language query.

**Request:**
```json
{
  "query": "show me emails from last week"
}
```

---

## Session Manager (Port 3005)

Manages persistent browser sessions.

#### GET /status
Get all session states.

**Response:**
```json
{
  "success": true,
  "sessions": {
    "email": {
      "status": "active",
      "lastActivity": "2024-01-03T10:00:00Z"
    }
  }
}
```

#### GET /email/status
Get email session state.

#### GET /email/emails
Get emails from current session.

#### POST /email/start
Start a new email session.

#### POST /email/action
Execute action in session.

**Request:**
```json
{
  "action": "view",
  "params": {
    "emailNum": 3
  }
}
```

#### POST /email/stop
Stop email session.

---

## Brain API (Port 3002)

Central data hub for all business data.

### Company Settings

#### GET /api/company
Get company settings.

**Headers:** `Authorization: Bearer <jwt>`

**Response:**
```json
{
  "success": true,
  "company": {
    "business_id": "abc123",
    "company_name": "Evolve Robot Lab",
    "whatsapp_keyword": "EVOLVE",
    "upi_id": "evolve@upi",
    "phone": "+91xxxxxxxxxx"
  }
}
```

#### PUT /api/company
Update company settings.

### Knowledge Base

#### GET /api/knowledge
List all knowledge items.

**Response:**
```json
{
  "success": true,
  "knowledge": [
    {
      "id": "k123",
      "intent": "greeting",
      "keywords": ["hi", "hello"],
      "response": "Welcome! How can I help?"
    }
  ]
}
```

#### POST /api/knowledge
Create knowledge item.

#### PUT /api/knowledge/:id
Update knowledge item.

#### DELETE /api/knowledge/:id
Delete knowledge item.

### Products

#### GET /api/products
List all products.

#### POST /api/products
Create product.

#### PUT /api/products/:id
Update product.

#### DELETE /api/products/:id
Delete product.

### Public Endpoints (No Auth)

#### GET /api/company/keyword/:keyword
Lookup business by WhatsApp keyword.

**Response:**
```json
{
  "success": true,
  "business_id": "abc123",
  "company_name": "Evolve Robot Lab"
}
```

---

## Authentication Headers

All protected endpoints require:

```
Authorization: Bearer <jwt_token>
```

JWT structure:
```json
{
  "sub": "user_id",
  "bid": "business_id",
  "role": "owner",
  "exp": 1234567890
}
```

## Error Responses

All endpoints return errors in this format:

```json
{
  "success": false,
  "error": "Error message description",
  "code": "ERROR_CODE"
}
```

Common error codes:
- `UNAUTHORIZED` - Missing or invalid token
- `FORBIDDEN` - Insufficient permissions
- `NOT_FOUND` - Resource not found
- `VALIDATION_ERROR` - Invalid request data
- `RATE_LIMITED` - Too many requests
- `TOKEN_LIMIT_EXCEEDED` - Daily token limit reached
