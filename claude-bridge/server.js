const http = require('http');
const https = require('https');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const PORT = 3003;
// Local services for testing
const GMAIL_API_URL = 'http://localhost:5002';
const WHATSAPP_API_URL = 'http://localhost:3004';
const BRAIN_API_URL = 'http://localhost:3002';
const BROWSER_SCRIPT = '/home/evolve/AI PROJECT/browser_automation/open_gmail_inbox.py';

// ============================================
// AUTONOMOUS TRIGGERS CONFIGURATION
// ============================================
const CONFIG = {
  polling: {
    enabled: true,
    intervals: {
      gmail: 60000,      // Check emails every 60 seconds
      whatsapp: 30000,   // Check WhatsApp every 30 seconds
      forms: 120000      // Check form submissions every 2 minutes
    }
  },
  autoProcess: {
    enabled: false,       // Set to true for full auto mode
    requireApproval: true // Require user approval for actions
  },
  tokenTracking: {
    enabled: true,
    dailyLimit: 100000    // Token limit per day
  }
};

// ============================================
// STATE MANAGEMENT
// ============================================
const STATE = {
  // Event queue for pending actions
  eventQueue: [],

  // Processed event IDs to avoid duplicates
  processedEvents: new Set(),

  // Token usage tracking
  tokenUsage: {
    today: 0,
    total: 0,
    lastReset: new Date().toDateString()
  },

  // Last check timestamps
  lastCheck: {
    gmail: null,
    whatsapp: null,
    forms: null
  },

  // Polling intervals
  pollingIntervals: {},

  // Browser automation state
  browser: {
    status: 'idle',           // idle, running, paused, manual
    lastAction: null,
    lastScreenshot: null,
    currentEmail: null,
    process: null
  }
};

// Persist state to file
const STATE_FILE = path.join(__dirname, 'state.json');

function saveState() {
  const stateToSave = {
    processedEvents: Array.from(STATE.processedEvents),
    tokenUsage: STATE.tokenUsage,
    lastCheck: STATE.lastCheck,
    eventQueue: STATE.eventQueue.slice(-100) // Keep last 100 events
  };
  fs.writeFileSync(STATE_FILE, JSON.stringify(stateToSave, null, 2));
}

function loadState() {
  try {
    if (fs.existsSync(STATE_FILE)) {
      const saved = JSON.parse(fs.readFileSync(STATE_FILE, 'utf8'));
      STATE.processedEvents = new Set(saved.processedEvents || []);
      STATE.tokenUsage = saved.tokenUsage || STATE.tokenUsage;
      STATE.lastCheck = saved.lastCheck || STATE.lastCheck;
      STATE.eventQueue = saved.eventQueue || [];
      console.log('[State] Loaded previous state');
    }
  } catch (e) {
    console.error('[State] Failed to load state:', e.message);
  }
}

// ============================================
// TOKEN TRACKING
// ============================================
function trackTokens(prompt, response) {
  // Rough estimation: ~4 chars per token
  const promptTokens = Math.ceil(prompt.length / 4);
  const responseTokens = Math.ceil(response.length / 4);
  const total = promptTokens + responseTokens;

  // Reset daily counter if new day
  const today = new Date().toDateString();
  if (STATE.tokenUsage.lastReset !== today) {
    STATE.tokenUsage.today = 0;
    STATE.tokenUsage.lastReset = today;
  }

  STATE.tokenUsage.today += total;
  STATE.tokenUsage.total += total;
  saveState();

  return { promptTokens, responseTokens, total, dailyTotal: STATE.tokenUsage.today };
}

function canUseTokens() {
  if (!CONFIG.tokenTracking.enabled) return true;
  return STATE.tokenUsage.today < CONFIG.tokenTracking.dailyLimit;
}

// ============================================
// HTTP HELPERS
// ============================================
function fetchUrl(url, options = {}) {
  return new Promise((resolve, reject) => {
    const client = url.startsWith('https') ? https : http;
    const req = client.request(url, {
      method: options.method || 'GET',
      headers: options.headers || {}
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          resolve({ raw: data });
        }
      });
    });
    req.on('error', reject);
    if (options.body) req.write(options.body);
    req.end();
  });
}

// ============================================
// POLLING SERVICES
// ============================================

async function pollGmail() {
  if (!CONFIG.polling.enabled) return;

  try {
    console.log('[Poll:Gmail] Checking for new emails...');
    const data = await fetchUrl(`${GMAIL_API_URL}/api/emails/fetch?max_results=5`);

    if (data.emails && data.emails.length > 0) {
      for (const email of data.emails) {
        const eventId = `gmail_${email.id || email.message_id}`;

        if (!STATE.processedEvents.has(eventId)) {
          // New email detected
          const event = {
            id: eventId,
            type: 'new_email',
            source: 'gmail',
            timestamp: new Date().toISOString(),
            data: {
              from: email.from,
              subject: email.subject,
              snippet: email.snippet,
              date: email.date
            },
            status: 'pending',
            suggestedAction: null
          };

          // Auto-process if enabled
          if (CONFIG.autoProcess.enabled && canUseTokens()) {
            event.suggestedAction = await generateSuggestedAction(event);
          }

          STATE.eventQueue.push(event);
          STATE.processedEvents.add(eventId);
          console.log(`[Poll:Gmail] New email from: ${email.from}`);
        }
      }
    }

    STATE.lastCheck.gmail = new Date().toISOString();
    saveState();
  } catch (e) {
    console.error('[Poll:Gmail] Error:', e.message);
  }
}

async function pollWhatsApp() {
  if (!CONFIG.polling.enabled) return;

  try {
    console.log('[Poll:WhatsApp] Checking for new messages...');
    const data = await fetchUrl(`${WHATSAPP_API_URL}/api/messages/recent`);

    if (data.messages && data.messages.length > 0) {
      for (const msg of data.messages) {
        const eventId = `whatsapp_${msg.id || msg.timestamp}`;

        if (!STATE.processedEvents.has(eventId)) {
          const event = {
            id: eventId,
            type: 'new_whatsapp',
            source: 'whatsapp',
            timestamp: new Date().toISOString(),
            data: {
              from: msg.from,
              body: msg.body,
              timestamp: msg.timestamp
            },
            status: 'pending',
            suggestedAction: null
          };

          if (CONFIG.autoProcess.enabled && canUseTokens()) {
            event.suggestedAction = await generateSuggestedAction(event);
          }

          STATE.eventQueue.push(event);
          STATE.processedEvents.add(eventId);
          console.log(`[Poll:WhatsApp] New message from: ${msg.from}`);
        }
      }
    }

    STATE.lastCheck.whatsapp = new Date().toISOString();
    saveState();
  } catch (e) {
    // WhatsApp API might not have this endpoint yet
    if (!e.message.includes('ECONNREFUSED')) {
      console.error('[Poll:WhatsApp] Error:', e.message);
    }
  }
}

async function pollForms() {
  if (!CONFIG.polling.enabled) return;

  try {
    console.log('[Poll:Forms] Checking for new submissions...');
    const data = await fetchUrl(`${BRAIN_API_URL}/api/submissions/recent`);

    if (data.submissions && data.submissions.length > 0) {
      for (const sub of data.submissions) {
        const eventId = `form_${sub.id}`;

        if (!STATE.processedEvents.has(eventId)) {
          const event = {
            id: eventId,
            type: 'new_submission',
            source: 'forms',
            timestamp: new Date().toISOString(),
            data: sub,
            status: 'pending',
            suggestedAction: null
          };

          if (CONFIG.autoProcess.enabled && canUseTokens()) {
            event.suggestedAction = await generateSuggestedAction(event);
          }

          STATE.eventQueue.push(event);
          STATE.processedEvents.add(eventId);
          console.log(`[Poll:Forms] New submission: ${sub.id}`);
        }
      }
    }

    STATE.lastCheck.forms = new Date().toISOString();
    saveState();
  } catch (e) {
    if (!e.message.includes('ECONNREFUSED')) {
      console.error('[Poll:Forms] Error:', e.message);
    }
  }
}

// ============================================
// AI ACTION GENERATION
// ============================================

async function generateSuggestedAction(event) {
  return new Promise((resolve) => {
    const prompts = {
      new_email: `You are Durga AI. A new email arrived:
From: ${event.data.from}
Subject: ${event.data.subject}
Preview: ${event.data.snippet}

Suggest a brief action (1-2 sentences). Options: reply, follow-up later, archive, mark important.`,

      new_whatsapp: `You are Durga AI. A new WhatsApp message:
From: ${event.data.from}
Message: ${event.data.body}

Suggest a brief response or action (1-2 sentences).`,

      new_submission: `You are Durga AI. A new form submission:
${JSON.stringify(event.data, null, 2)}

Suggest next steps (1-2 sentences). Consider: follow-up call, send info, add to CRM.`
    };

    const prompt = prompts[event.type] || 'Analyze this event and suggest an action.';

    const claude = spawn('claude', ['--print'], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    let output = '';
    claude.stdout.on('data', data => output += data);
    claude.on('close', () => {
      trackTokens(prompt, output);
      resolve(output.trim());
    });
    claude.on('error', () => resolve(null));

    claude.stdin.write(prompt);
    claude.stdin.end();
  });
}

// ============================================
// START POLLING
// ============================================

function startPolling() {
  if (!CONFIG.polling.enabled) {
    console.log('[Polling] Disabled');
    return;
  }

  console.log('[Polling] Starting autonomous triggers...');

  // Initial poll
  setTimeout(pollGmail, 5000);
  setTimeout(pollWhatsApp, 10000);
  setTimeout(pollForms, 15000);

  // Set up intervals
  STATE.pollingIntervals.gmail = setInterval(pollGmail, CONFIG.polling.intervals.gmail);
  STATE.pollingIntervals.whatsapp = setInterval(pollWhatsApp, CONFIG.polling.intervals.whatsapp);
  STATE.pollingIntervals.forms = setInterval(pollForms, CONFIG.polling.intervals.forms);

  console.log(`[Polling] Gmail: every ${CONFIG.polling.intervals.gmail/1000}s`);
  console.log(`[Polling] WhatsApp: every ${CONFIG.polling.intervals.whatsapp/1000}s`);
  console.log(`[Polling] Forms: every ${CONFIG.polling.intervals.forms/1000}s`);
}

function stopPolling() {
  Object.values(STATE.pollingIntervals).forEach(clearInterval);
  STATE.pollingIntervals = {};
  console.log('[Polling] Stopped');
}

// ============================================
// ORIGINAL HELPERS
// ============================================

function isInboxQuery(query) {
  if (!query) return false;
  const q = query.toLowerCase();
  return q.includes('inbox') || q.includes('email') || q.includes('mail') ||
         q.includes('message') || q.includes('unread');
}

function formatEmailsForContext(emails) {
  if (!emails || !emails.length) return 'No emails found.';
  return emails.map((email, i) => {
    const from = email.from || 'Unknown';
    const subject = email.subject || 'No Subject';
    const date = email.date || 'Unknown date';
    const snippet = email.snippet || '';
    return `${i + 1}. From: ${from}
   Subject: ${subject}
   Date: ${date}
   Preview: ${snippet.substring(0, 150)}...`;
  }).join('\n\n');
}

function determineResponseType(query) {
  if (!query) return 'general';
  const q = query.toLowerCase();
  if (q.includes('inbox') || q.includes('email') || q.includes('mail')) return 'inbox';
  if (q.includes('today') || q.includes('status') || q.includes('summary')) return 'summary';
  if (q.includes('follow') || q.includes('remind') || q.includes('task')) return 'task_list';
  if (q.includes('payment') || q.includes('pending') || q.includes('money')) return 'payment_status';
  if (q.includes('lead') || q.includes('customer') || q.includes('client')) return 'leads';
  if (q.includes('event') || q.includes('queue') || q.includes('trigger')) return 'events';
  return 'general';
}

// ============================================
// BROWSER AUTOMATION COMMANDS
// ============================================

function parseBrowserCommand(query) {
  if (!query) return null;
  const q = query.toLowerCase();

  // List inbox (stop at inbox, show results)
  if (q.includes('list inbox') || q.includes('show inbox') || q.includes('open inbox') ||
      q.includes('check inbox') || q.includes('my emails') || q.includes('show emails') ||
      q.includes('open mail') || q.includes('show mail') || q.includes('check mail') ||
      q.includes('open gmail') || q.includes('show gmail')) {
    return { action: 'list', emailNum: 0 };
  }

  // View specific email
  if (q.includes('view email') || q.includes('read email') || q.includes('open email')) {
    let emailNum = 1;
    const numMatch = q.match(/email\s*#?(\d+)|(\d+)(?:st|nd|rd|th)\s*email|#(\d+)/);
    if (numMatch) {
      emailNum = parseInt(numMatch[1] || numMatch[2] || numMatch[3]);
    }
    return { action: 'view', emailNum };
  }

  // Reply to email
  if (q.includes('reply')) {
    let emailNum = 1;
    const numMatch = q.match(/email\s*#?(\d+)|(\d+)(?:st|nd|rd|th)\s*email|#(\d+)/);
    if (numMatch) {
      emailNum = parseInt(numMatch[1] || numMatch[2] || numMatch[3]);
    }

    let template = null;
    if (q.includes('internship') && (q.includes('completion') || q.includes('report') || q.includes('final'))) {
      template = 'internship_completion';
    } else if (q.includes('job') || q.includes('application') || q.includes('resume')) {
      template = 'job_application';
    } else if (q.includes('interview') || q.includes('invite')) {
      template = 'interview_invite';
    } else if (q.includes('acknowledge') || q.includes('received')) {
      template = 'job_acknowledgment';
    }

    return { action: 'reply', emailNum, template };
  }

  // Close session
  if (q.includes('close inbox') || q.includes('close browser') || q.includes('close session')) {
    return { action: 'close' };
  }

  return null;
}

function runBrowserAutomation(emailNum, action, template) {
  return new Promise((resolve, reject) => {
    // Script expects: action [email_num] [template]
    const args = [BROWSER_SCRIPT, action];
    if (emailNum > 0) args.push(emailNum.toString());
    if (template) args.push(template);

    console.log(`[Browser] Running: python3 ${args.join(' ')}`);

    const proc = spawn('python3', args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      detached: true,
      env: { ...process.env, DISPLAY: process.env.DISPLAY || ':0' }
    });

    let output = '';
    let error = '';

    proc.stdout.on('data', data => {
      output += data;
      console.log(`[Browser] ${data}`);
    });

    proc.stderr.on('data', data => {
      error += data;
    });

    proc.on('close', code => {
      if (code === 0) {
        resolve({
          success: true,
          message: `Browser automation completed. Action: ${action} on email #${emailNum}${template ? ` with template: ${template}` : ''}`,
          output: output.slice(-500) // Last 500 chars
        });
      } else {
        resolve({
          success: false,
          message: `Browser automation failed with code ${code}`,
          error: error || output
        });
      }
    });

    proc.on('error', err => {
      reject(err);
    });

    // Don't wait for completion - let it run in background
    proc.unref();

    // Return immediately with "started" status
    setTimeout(() => {
      resolve({
        success: true,
        message: `Browser automation started. Opening email #${emailNum} with action: ${action}${template ? `, template: ${template}` : ''}. Check the browser window.`,
        status: 'started'
      });
    }, 1000);
  });
}

// ============================================
// HTTP SERVER
// ============================================

const server = http.createServer(async (req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'POST, GET, OPTIONS, DELETE');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.writeHead(200);
    res.end();
    return;
  }

  // ---- POST /ask - Main query endpoint ----
  if (req.method === 'POST' && req.url === '/ask') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { query, context } = JSON.parse(body);

        // Check for browser automation commands first
        const browserCmd = parseBrowserCommand(query);
        if (browserCmd) {
          console.log(`[Browser] Command detected: ${JSON.stringify(browserCmd)}`);
          try {
            const result = await runBrowserAutomation(
              browserCmd.emailNum,
              browserCmd.action,
              browserCmd.template
            );
            res.writeHead(200, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
              success: true,
              response: {
                message: result.message,
                type: 'browser_automation',
                actions: [{
                  type: 'browser',
                  emailNum: browserCmd.emailNum,
                  action: browserCmd.action,
                  template: browserCmd.template
                }],
                sources: ['Browser Automation']
              }
            }));
          } catch (err) {
            res.writeHead(500, { 'Content-Type': 'application/json' });
            res.end(JSON.stringify({
              success: false,
              error: `Browser automation error: ${err.message}`
            }));
          }
          return;
        }

        if (!canUseTokens()) {
          res.writeHead(429, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: false,
            error: 'Daily token limit reached',
            tokenUsage: STATE.tokenUsage
          }));
          return;
        }

        let enrichedContext = context || '';
        let responseType = determineResponseType(query);

        // Fetch emails for inbox queries
        if (isInboxQuery(query)) {
          try {
            const emailData = await fetchUrl(`${GMAIL_API_URL}/api/emails/fetch?max_results=5`);
            if (emailData.emails && emailData.emails.length > 0) {
              enrichedContext = `INBOX DATA (${emailData.emails.length} recent emails):\n${formatEmailsForContext(emailData.emails)}\n\nUser context: ${context || 'None'}`;
              responseType = 'inbox';
            }
          } catch (err) {
            enrichedContext = `Note: Could not fetch emails. Error: ${err.message}. ${context || ''}`;
          }
        }

        // Add pending events to context if asking about events
        if (responseType === 'events' || query.toLowerCase().includes('pending')) {
          const pendingEvents = STATE.eventQueue.filter(e => e.status === 'pending');
          if (pendingEvents.length > 0) {
            enrichedContext += `\n\nPENDING EVENTS (${pendingEvents.length}):\n`;
            pendingEvents.forEach((e, i) => {
              enrichedContext += `${i+1}. [${e.type}] ${e.source} - ${JSON.stringify(e.data).substring(0, 100)}...\n`;
            });
          }
        }

        const prompt = `You are Durga, an AI chief-of-staff for business owners.

IMPORTANT RULES:
- Never auto-send messages or take actions without explicit user approval
- Always suggest actions, never execute them
- Keep responses brief and actionable
- When showing inbox, summarize each email briefly

Context: ${enrichedContext}

User query: ${query}

Respond concisely as Durga.`;

        const claude = spawn('claude', ['--print'], { stdio: ['pipe', 'pipe', 'pipe'] });
        let output = '';
        let error = '';

        claude.stdout.on('data', data => output += data);
        claude.stderr.on('data', data => error += data);

        claude.on('close', code => {
          const tokenInfo = trackTokens(prompt, output);
          res.writeHead(200, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({
            success: code === 0,
            response: {
              message: output.trim() || error || 'No response from Claude',
              type: responseType,
              actions: [],
              sources: responseType === 'inbox' ? ['Gmail API'] : []
            },
            tokenUsage: tokenInfo
          }));
        });

        claude.on('error', (err) => {
          res.writeHead(500, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ success: false, error: 'Failed to spawn Claude CLI: ' + err.message }));
        });

        claude.stdin.write(prompt);
        claude.stdin.end();
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
  }

  // ---- GET /events - Get event queue ----
  else if (req.method === 'GET' && req.url === '/events') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      events: STATE.eventQueue,
      pending: STATE.eventQueue.filter(e => e.status === 'pending').length,
      total: STATE.eventQueue.length
    }));
  }

  // ---- GET /events/pending - Get only pending events ----
  else if (req.method === 'GET' && req.url === '/events/pending') {
    const pending = STATE.eventQueue.filter(e => e.status === 'pending');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      events: pending,
      count: pending.length
    }));
  }

  // ---- POST /events/:id/approve - Approve an event action ----
  else if (req.method === 'POST' && req.url.startsWith('/events/') && req.url.endsWith('/approve')) {
    const eventId = req.url.split('/')[2];
    const event = STATE.eventQueue.find(e => e.id === eventId);
    if (event) {
      event.status = 'approved';
      event.approvedAt = new Date().toISOString();
      saveState();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, event }));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: 'Event not found' }));
    }
  }

  // ---- POST /events/:id/dismiss - Dismiss an event ----
  else if (req.method === 'POST' && req.url.startsWith('/events/') && req.url.endsWith('/dismiss')) {
    const eventId = req.url.split('/')[2];
    const event = STATE.eventQueue.find(e => e.id === eventId);
    if (event) {
      event.status = 'dismissed';
      event.dismissedAt = new Date().toISOString();
      saveState();
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: true, event }));
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: 'Event not found' }));
    }
  }

  // ---- DELETE /events/clear - Clear event queue ----
  else if (req.method === 'DELETE' && req.url === '/events/clear') {
    STATE.eventQueue = [];
    saveState();
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, message: 'Event queue cleared' }));
  }

  // ---- GET /tokens - Get token usage ----
  else if (req.method === 'GET' && req.url === '/tokens') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      usage: STATE.tokenUsage,
      limit: CONFIG.tokenTracking.dailyLimit,
      remaining: CONFIG.tokenTracking.dailyLimit - STATE.tokenUsage.today
    }));
  }

  // ---- POST /config - Update configuration ----
  else if (req.method === 'POST' && req.url === '/config') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', () => {
      try {
        const updates = JSON.parse(body);
        if (updates.polling !== undefined) CONFIG.polling.enabled = updates.polling;
        if (updates.autoProcess !== undefined) CONFIG.autoProcess.enabled = updates.autoProcess;
        if (updates.tokenLimit !== undefined) CONFIG.tokenTracking.dailyLimit = updates.tokenLimit;

        if (updates.polling === true) startPolling();
        if (updates.polling === false) stopPolling();

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, config: CONFIG }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
  }

  // ---- GET /config - Get current configuration ----
  else if (req.method === 'GET' && req.url === '/config') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, config: CONFIG }));
  }

  // ---- POST /webhook/gmail - Webhook for Gmail events ----
  else if (req.method === 'POST' && req.url === '/webhook/gmail') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const event = JSON.parse(body);
        const eventId = `gmail_webhook_${Date.now()}`;

        STATE.eventQueue.push({
          id: eventId,
          type: 'new_email',
          source: 'gmail_webhook',
          timestamp: new Date().toISOString(),
          data: event,
          status: 'pending'
        });
        STATE.processedEvents.add(eventId);
        saveState();

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, eventId }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
  }

  // ---- POST /webhook/whatsapp - Webhook for WhatsApp events ----
  else if (req.method === 'POST' && req.url === '/webhook/whatsapp') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const event = JSON.parse(body);
        const eventId = `whatsapp_webhook_${Date.now()}`;

        STATE.eventQueue.push({
          id: eventId,
          type: 'new_whatsapp',
          source: 'whatsapp_webhook',
          timestamp: new Date().toISOString(),
          data: event,
          status: 'pending'
        });
        STATE.processedEvents.add(eventId);
        saveState();

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, eventId }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
  }

  // ---- POST /webhook/forms - Webhook for form submissions ----
  else if (req.method === 'POST' && req.url === '/webhook/forms') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const event = JSON.parse(body);
        const eventId = `form_webhook_${Date.now()}`;

        STATE.eventQueue.push({
          id: eventId,
          type: 'new_submission',
          source: 'forms_webhook',
          timestamp: new Date().toISOString(),
          data: event,
          status: 'pending'
        });
        STATE.processedEvents.add(eventId);
        saveState();

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, eventId }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
  }

  // ---- GET /inbox - Direct inbox endpoint ----
  else if (req.method === 'GET' && req.url === '/inbox') {
    try {
      const emailData = await fetchUrl(`${GMAIL_API_URL}/api/emails/fetch?max_results=10`);
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({
        success: true,
        emails: emailData.emails || [],
        count: emailData.emails?.length || 0
      }));
    } catch (err) {
      res.writeHead(500, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ success: false, error: err.message }));
    }
  }

  // ---- GET /health - Health check ----
  else if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'healthy',
      service: 'Claude Bridge',
      port: PORT,
      polling: CONFIG.polling.enabled,
      pendingEvents: STATE.eventQueue.filter(e => e.status === 'pending').length,
      tokenUsage: STATE.tokenUsage
    }));
  }

  // ============================================
  // BROWSER CONTROL ENDPOINTS
  // ============================================

  // ---- GET /browser-control - Serve browser control UI ----
  else if (req.method === 'GET' && req.url === '/browser-control') {
    const html = `<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DURGA Browser Control</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0a0a0a; color: #fff; min-height: 100vh; }
        .header { display: flex; justify-content: space-between; align-items: center; padding: 16px 24px; background: #111; border-bottom: 1px solid #333; }
        .header h1 { font-size: 1.5rem; color: #00ff88; }
        .header-controls { display: flex; gap: 12px; }
        .btn { padding: 10px 20px; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
        .btn-home { background: #333; color: #fff; }
        .btn-pause { background: #ff9500; color: #000; }
        .btn-resume { background: #00ff88; color: #000; }
        .btn-stop { background: #ff3b30; color: #fff; }
        .btn-manual { background: #007aff; color: #fff; }
        .btn:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.3); }
        .main-container { display: grid; grid-template-columns: 1fr 400px; gap: 20px; padding: 20px; height: calc(100vh - 80px); }
        .screenshot-container { background: #111; border-radius: 12px; overflow: hidden; display: flex; flex-direction: column; }
        .screenshot-header { padding: 12px 16px; background: #1a1a1a; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
        .status-badge { padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 600; }
        .status-idle { background: #333; color: #888; }
        .status-running { background: #00ff88; color: #000; }
        .status-paused { background: #ff9500; color: #000; }
        .status-manual { background: #007aff; color: #fff; }
        .screenshot-img { flex: 1; display: flex; align-items: center; justify-content: center; padding: 16px; overflow: hidden; }
        .screenshot-img img { max-width: 100%; max-height: 100%; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.5); }
        .no-screenshot { color: #666; text-align: center; }
        .sidebar { display: flex; flex-direction: column; gap: 16px; overflow-y: auto; }
        .panel { background: #111; border-radius: 12px; overflow: hidden; }
        .panel-header { padding: 12px 16px; background: #1a1a1a; border-bottom: 1px solid #333; font-weight: 600; }
        .panel-content { padding: 16px; }
        .inbox-list { max-height: 250px; overflow-y: auto; }
        .email-item { padding: 12px; border-radius: 8px; background: #1a1a1a; margin-bottom: 8px; }
        .email-from { font-weight: 600; margin-bottom: 4px; font-size: 13px; }
        .email-subject { font-size: 12px; color: #888; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        .email-actions { display: flex; gap: 8px; margin-top: 8px; }
        .email-actions button { flex: 1; padding: 6px; border: none; border-radius: 4px; font-size: 11px; cursor: pointer; }
        .btn-view { background: #333; color: #fff; }
        .btn-reply { background: #00ff88; color: #000; }
        .events-list { max-height: 200px; overflow-y: auto; }
        .event-item { padding: 12px; border-radius: 8px; background: #1a1a1a; margin-bottom: 8px; }
        .event-type { font-size: 11px; color: #00ff88; text-transform: uppercase; margin-bottom: 4px; }
        .event-data { font-size: 13px; color: #888; }
        .event-actions { display: flex; gap: 8px; margin-top: 8px; }
        .event-actions button { flex: 1; padding: 6px; border: none; border-radius: 4px; font-size: 11px; cursor: pointer; }
        .btn-approve { background: #00ff88; color: #000; }
        .btn-dismiss { background: #ff3b30; color: #fff; }
        @media (max-width: 900px) { .main-container { grid-template-columns: 1fr; } }
    </style>
</head>
<body>
    <div class="header">
        <h1>DURGA Browser Control</h1>
        <div class="header-controls">
            <button class="btn btn-home" onclick="goHome()">Home</button>
            <button class="btn btn-pause" id="pauseBtn" onclick="pauseAutomation()">Pause</button>
            <button class="btn btn-resume" id="resumeBtn" onclick="resumeAutomation()" style="display:none;">Resume</button>
            <button class="btn btn-manual" onclick="openInbox()">Open Inbox</button>
            <button class="btn btn-stop" onclick="stopBrowser()">Stop</button>
        </div>
    </div>
    <div class="main-container">
        <div class="screenshot-container">
            <div class="screenshot-header">
                <span>Live View</span>
                <span class="status-badge status-idle" id="statusBadge">IDLE</span>
            </div>
            <div class="screenshot-img" id="screenshotContainer">
                <div class="no-screenshot">
                    <p>No screenshot available</p>
                    <p style="font-size: 13px; margin-top: 8px;">Click "Open Inbox" to start</p>
                </div>
            </div>
        </div>
        <div class="sidebar">
            <div class="panel">
                <div class="panel-header">Inbox Emails</div>
                <div class="panel-content">
                    <div class="inbox-list" id="inboxList"><p style="color: #666;">Loading...</p></div>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">Pending Events (<span id="eventCount">0</span>)</div>
                <div class="panel-content">
                    <div class="events-list" id="eventsList"><p style="color: #666;">No pending events</p></div>
                </div>
            </div>
            <div class="panel">
                <div class="panel-header">Quick Actions</div>
                <div class="panel-content">
                    <button class="btn btn-resume" style="width: 100%; margin-bottom: 8px;" onclick="openInbox()">Refresh Inbox</button>
                    <button class="btn" style="width: 100%; background: #333; color: #fff;" onclick="refreshStatus()">Refresh Status</button>
                </div>
            </div>
        </div>
    </div>
    <script>
        const BASE = window.location.origin;
        let currentStatus = 'idle';
        function goHome() { window.location.href = 'http://localhost:8080'; }
        async function fetchStatus() {
            try {
                const res = await fetch(BASE + '/browser/status');
                const data = await res.json();
                currentStatus = data.browser?.status || 'idle';
                updateStatusBadge(currentStatus);
                if (data.inbox?.emails) updateInboxList(data.inbox.emails);
                document.getElementById('eventCount').textContent = data.pendingEvents || 0;
                if (data.browser?.hasScreenshot) loadScreenshot();
            } catch (e) { console.error('Status error:', e); }
        }
        async function fetchEvents() {
            try {
                const res = await fetch(BASE + '/events/pending');
                const data = await res.json();
                if (data.events) updateEventsList(data.events);
            } catch (e) {}
        }
        function updateStatusBadge(status) {
            const badge = document.getElementById('statusBadge');
            badge.className = 'status-badge status-' + status;
            badge.textContent = status.toUpperCase();
            document.getElementById('pauseBtn').style.display = status === 'running' ? 'block' : 'none';
            document.getElementById('resumeBtn').style.display = status === 'paused' ? 'block' : 'none';
        }
        function updateInboxList(emails) {
            const list = document.getElementById('inboxList');
            if (!emails.length) { list.innerHTML = '<p style="color: #666;">No emails</p>'; return; }
            list.innerHTML = emails.slice(0, 8).map(email =>
                '<div class="email-item"><div class="email-from">' + escapeHtml(email.from) + '</div>' +
                '<div class="email-subject">' + escapeHtml(email.subject) + '</div>' +
                '<div class="email-actions"><button class="btn-view" onclick="viewEmail(' + email.index + ')">View</button>' +
                '<button class="btn-reply" onclick="replyEmail(' + email.index + ')">Reply</button></div></div>'
            ).join('');
        }
        function updateEventsList(events) {
            const list = document.getElementById('eventsList');
            if (!events.length) { list.innerHTML = '<p style="color: #666;">No pending events</p>'; return; }
            list.innerHTML = events.slice(0, 5).map(event =>
                '<div class="event-item"><div class="event-type">' + event.type + '</div>' +
                '<div class="event-data">' + escapeHtml(event.data?.from || event.data?.subject || '') + '</div>' +
                '<div class="event-actions"><button class="btn-approve" onclick="approveEvent(\\'' + event.id + '\\')">Approve</button>' +
                '<button class="btn-dismiss" onclick="dismissEvent(\\'' + event.id + '\\')">Dismiss</button></div></div>'
            ).join('');
        }
        function loadScreenshot() {
            const container = document.getElementById('screenshotContainer');
            container.innerHTML = '<img src="' + BASE + '/browser/screenshot?t=' + Date.now() + '" alt="Browser" onerror="this.parentElement.innerHTML=\\'<div class=no-screenshot><p>Screenshot failed</p></div>\\'">';
        }
        async function pauseAutomation() { await fetch(BASE + '/browser/pause', { method: 'POST' }); fetchStatus(); }
        async function resumeAutomation() { await fetch(BASE + '/browser/resume', { method: 'POST' }); fetchStatus(); }
        async function stopBrowser() { if (confirm('Stop browser?')) { await fetch(BASE + '/browser/stop', { method: 'POST' }); fetchStatus(); } }
        async function openInbox() {
            await fetch(BASE + '/browser/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'list' }) });
            setTimeout(() => { loadScreenshot(); fetchStatus(); }, 3000);
        }
        async function viewEmail(num) {
            await fetch(BASE + '/browser/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'view', emailNum: num }) });
            setTimeout(loadScreenshot, 2000);
        }
        async function replyEmail(num) {
            const template = prompt('Template (job_application, interview_invite, general_response):') || 'job_application';
            await fetch(BASE + '/browser/action', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ action: 'reply', emailNum: num, template }) });
            setTimeout(loadScreenshot, 2000);
        }
        async function approveEvent(id) { await fetch(BASE + '/events/' + id + '/approve', { method: 'POST' }); fetchEvents(); }
        async function dismissEvent(id) { await fetch(BASE + '/events/' + id + '/dismiss', { method: 'POST' }); fetchEvents(); }
        function refreshStatus() { fetchStatus(); fetchEvents(); loadScreenshot(); }
        function escapeHtml(text) { const div = document.createElement('div'); div.textContent = text || ''; return div.innerHTML; }
        fetchStatus(); fetchEvents();
        setInterval(() => { fetchStatus(); if (currentStatus === 'running') loadScreenshot(); }, 3000);
    </script>
</body>
</html>`;
    res.writeHead(200, { 'Content-Type': 'text/html' });
    res.end(html);
  }

  // ---- GET /browser/status - Get browser automation status ----
  else if (req.method === 'GET' && req.url === '/browser/status') {
    // Check if there's a saved state file from browser automation
    let inboxState = null;
    const inboxStateFile = '/tmp/durga_inbox_state.json';
    try {
      if (fs.existsSync(inboxStateFile)) {
        inboxState = JSON.parse(fs.readFileSync(inboxStateFile, 'utf8'));
      }
    } catch (e) {}

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      browser: {
        status: STATE.browser.status,
        lastAction: STATE.browser.lastAction,
        currentEmail: STATE.browser.currentEmail,
        hasScreenshot: fs.existsSync('/tmp/durga_screenshot.png')
      },
      inbox: inboxState,
      pendingEvents: STATE.eventQueue.filter(e => e.status === 'pending').length
    }));
  }

  // ---- GET /browser/screenshot - Serve latest screenshot ----
  else if (req.method === 'GET' && req.url === '/browser/screenshot') {
    const screenshotPath = '/tmp/durga_screenshot.png';
    if (fs.existsSync(screenshotPath)) {
      const stat = fs.statSync(screenshotPath);
      res.writeHead(200, {
        'Content-Type': 'image/png',
        'Content-Length': stat.size,
        'Cache-Control': 'no-cache'
      });
      fs.createReadStream(screenshotPath).pipe(res);
    } else {
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'No screenshot available' }));
    }
  }

  // ---- POST /browser/pause - Pause automation ----
  else if (req.method === 'POST' && req.url === '/browser/pause') {
    STATE.browser.status = 'paused';
    saveState();
    console.log('[Browser] Paused');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, status: 'paused' }));
  }

  // ---- POST /browser/resume - Resume automation ----
  else if (req.method === 'POST' && req.url === '/browser/resume') {
    STATE.browser.status = 'running';
    saveState();
    console.log('[Browser] Resumed');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, status: 'running' }));
  }

  // ---- POST /browser/stop - Stop browser session ----
  else if (req.method === 'POST' && req.url === '/browser/stop') {
    // Run close command
    spawn('python3', [BROWSER_SCRIPT, 'close'], { detached: true }).unref();
    STATE.browser.status = 'idle';
    STATE.browser.lastAction = 'stopped';
    saveState();
    console.log('[Browser] Stopped');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, status: 'stopped' }));
  }

  // ---- POST /browser/take-control - Switch to manual mode ----
  else if (req.method === 'POST' && req.url === '/browser/take-control') {
    // Launch browser with visible window using 'list' command (opens inbox visibly)
    STATE.browser.status = 'manual';
    STATE.browser.lastAction = 'manual_control';
    saveState();
    console.log('[Browser] Switching to manual control - opening visible browser');

    // Run list command to open browser
    spawn('python3', [BROWSER_SCRIPT, 'list'], {
      detached: true,
      stdio: 'ignore'
    }).unref();

    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      success: true,
      status: 'manual',
      message: 'Browser window opening on your desktop. You have full control.'
    }));
  }

  // ---- POST /browser/return-control - Return to auto mode ----
  else if (req.method === 'POST' && req.url === '/browser/return-control') {
    STATE.browser.status = 'running';
    STATE.browser.lastAction = 'returned_control';
    saveState();
    console.log('[Browser] Control returned to automation');
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ success: true, status: 'running' }));
  }

  // ---- POST /browser/action - Execute specific browser action ----
  else if (req.method === 'POST' && req.url === '/browser/action') {
    let body = '';
    req.on('data', chunk => body += chunk);
    req.on('end', async () => {
      try {
        const { action, emailNum, template } = JSON.parse(body);
        console.log(`[Browser] Action requested: ${action} email:${emailNum} template:${template}`);

        STATE.browser.status = 'running';
        STATE.browser.lastAction = action;
        STATE.browser.currentEmail = emailNum;

        const result = await runBrowserAutomation(emailNum || 0, action, template);

        res.writeHead(200, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: true, ...result }));
      } catch (e) {
        res.writeHead(400, { 'Content-Type': 'application/json' });
        res.end(JSON.stringify({ success: false, error: e.message }));
      }
    });
  }

  // ---- GET / - Info endpoint ----
  else {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({
      status: 'Claude Bridge with Autonomous Triggers',
      port: PORT,
      polling: CONFIG.polling.enabled,
      autoProcess: CONFIG.autoProcess.enabled,
      endpoints: {
        'POST /ask': 'Send queries to Claude CLI (includes browser commands)',
        'GET /inbox': 'Fetch emails from Gmail API',
        'GET /events': 'Get all events in queue',
        'GET /events/pending': 'Get pending events only',
        'POST /events/:id/approve': 'Approve an event action',
        'POST /events/:id/dismiss': 'Dismiss an event',
        'DELETE /events/clear': 'Clear event queue',
        'GET /tokens': 'Get token usage stats',
        'GET /config': 'Get current configuration',
        'POST /config': 'Update configuration',
        'POST /webhook/gmail': 'Receive Gmail events',
        'POST /webhook/whatsapp': 'Receive WhatsApp events',
        'POST /webhook/forms': 'Receive form submissions',
        'GET /health': 'Health check',
        'GET /browser/status': 'Get browser automation status',
        'GET /browser/screenshot': 'Serve latest screenshot',
        'POST /browser/pause': 'Pause automation',
        'POST /browser/resume': 'Resume automation',
        'POST /browser/stop': 'Stop browser session',
        'POST /browser/take-control': 'Switch to manual mode',
        'POST /browser/return-control': 'Return to auto mode',
        'POST /browser/action': 'Execute browser action'
      },
      browserCommands: {
        description: 'Say these to trigger browser automation:',
        examples: [
          'open inbox',
          'open gmail',
          'view email #2',
          'check email',
          'reply to email #3',
          'reply to email with job application template',
          'reply to 2nd email with interview invite'
        ],
        templates: ['job_application', 'job_acknowledgment', 'interview_invite', 'general_response']
      }
    }));
  }
});

// ============================================
// SERVER STARTUP
// ============================================

server.listen(PORT, () => {
  console.log(`
  =============================================
  Claude Bridge Server (Autonomous Mode)
  =============================================
  Running at: http://localhost:${PORT}

  Services:
    Gmail API:    ${GMAIL_API_URL}
    WhatsApp API: ${WHATSAPP_API_URL}
    Brain API:    ${BRAIN_API_URL}

  Features:
    Polling:      ${CONFIG.polling.enabled ? 'ENABLED' : 'DISABLED'}
    Auto-Process: ${CONFIG.autoProcess.enabled ? 'ENABLED' : 'DISABLED'}
    Token Limit:  ${CONFIG.tokenTracking.dailyLimit}/day

  Endpoints:
    POST /ask              - Query Claude
    GET  /events           - View event queue
    GET  /events/pending   - View pending events
    POST /events/:id/approve - Approve action
    POST /events/:id/dismiss - Dismiss event
    GET  /tokens           - Token usage stats
    POST /config           - Update settings
    POST /webhook/*        - Receive events

  Ready for autonomous operation...
  `);

  loadState();
  startPolling();
});

// Graceful shutdown
process.on('SIGINT', () => {
  console.log('\n[Shutdown] Saving state...');
  stopPolling();
  saveState();
  process.exit(0);
});
