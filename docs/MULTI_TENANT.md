# DURGA AI - Multi-Tenant Architecture

## Core Principle

> "Login identifies WHO the user is. Business ID defines WHAT world they operate in."

## The Business ID Spine

Every piece of data in DURGA is associated with a `business_id`. This is the fundamental isolation mechanism that ensures:

1. **Data Isolation** - Business A cannot see Business B's data
2. **Context Preservation** - Switching workspaces doesn't switch business
3. **Scalability** - Single codebase serves unlimited businesses

## User Journey

### Signup Flow

```
1. User signs up with email/password
   └─► System creates user_id

2. System creates new business
   └─► System creates business_id

3. User linked as owner
   └─► business_members(user_id, business_id, role="owner")

4. User receives JWT
   └─► { sub: user_id, bid: business_id, role: "owner" }
```

### Login Flow

```
1. User logs in
   └─► Validate credentials

2. Fetch user's business associations
   └─► SELECT * FROM business_members WHERE user_id = ?

3. Return JWT with primary business
   └─► { sub: user_id, bid: primary_business_id, role: "owner" }
```

## Database Design

### Every Table Has business_id

```sql
-- Example: knowledge table
CREATE TABLE knowledge (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,  -- ← Always present
    intent TEXT,
    keywords TEXT,
    response TEXT,
    FOREIGN KEY (business_id) REFERENCES company_settings(business_id)
);

-- Example: products table
CREATE TABLE products (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,  -- ← Always present
    name TEXT,
    price DECIMAL,
    FOREIGN KEY (business_id) REFERENCES company_settings(business_id)
);

-- Example: campaigns table
CREATE TABLE campaigns (
    id TEXT PRIMARY KEY,
    business_id TEXT NOT NULL,  -- ← Always present
    name TEXT,
    status TEXT,
    FOREIGN KEY (business_id) REFERENCES company_settings(business_id)
);
```

### business_members (User-Business Link)

```sql
CREATE TABLE business_members (
    user_id TEXT NOT NULL,
    business_id TEXT NOT NULL,
    role TEXT NOT NULL,  -- 'owner', 'admin', 'member'
    joined_at TIMESTAMP,
    PRIMARY KEY (user_id, business_id)
);
```

## Query Patterns

### Always Filter by business_id

```javascript
// ✅ CORRECT - Always filter
async function getProducts(businessId) {
    return db.query(
        'SELECT * FROM products WHERE business_id = ?',
        [businessId]
    );
}

// ❌ WRONG - Never query without filter
async function getProducts() {
    return db.query('SELECT * FROM products');  // DANGEROUS!
}
```

### Extract business_id from JWT

```javascript
// Middleware to extract and validate business context
function businessContext(req, res, next) {
    const token = req.headers.authorization?.split(' ')[1];
    const decoded = jwt.verify(token, SECRET);

    req.userId = decoded.sub;
    req.businessId = decoded.bid;  // ← Always available
    req.role = decoded.role;

    next();
}

// Usage in route handlers
app.get('/api/products', businessContext, async (req, res) => {
    const products = await getProducts(req.businessId);
    res.json(products);
});
```

## Per-Business Configuration

Each business has unique settings stored in `company_settings`:

| Field | Purpose |
|-------|---------|
| `business_id` | Primary key |
| `company_name` | Display name |
| `whatsapp_keyword` | Unique keyword for WhatsApp routing |
| `upi_id` | UPI ID for payment collection |
| `phone` | Contact phone |
| `logo_url` | Company logo |

### WhatsApp Keyword Routing

```
User sends: "Hi EVOLVE"
                │
                ▼
┌────────────────────────────────────┐
│ Extract keyword: "EVOLVE"          │
│                                    │
│ Query: SELECT business_id          │
│        FROM company_settings       │
│        WHERE whatsapp_keyword =    │
│              'EVOLVE'              │
│                                    │
│ Result: business_id = "abc123"     │
└────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────┐
│ Load business context              │
│ Route to correct business          │
│ Respond with business content      │
└────────────────────────────────────┘
```

### UPI Payment Integration

```
Form submission with payment
                │
                ▼
┌────────────────────────────────────┐
│ Get UPI ID for business            │
│                                    │
│ Query: SELECT upi_id               │
│        FROM company_settings       │
│        WHERE business_id = ?       │
│                                    │
│ Result: upi_id = "business@upi"    │
└────────────────────────────────────┘
                │
                ▼
┌────────────────────────────────────┐
│ Generate UPI payment link          │
│ upi://pay?pa=business@upi&am=100   │
└────────────────────────────────────┘
```

## Workspace Switching

### Key Rule: Switching workspace ≠ switching business

```
User in Gmail Workspace (business_id = "abc123")
         │
         │ Clicks "WhatsApp" in sidebar
         ▼
User in WhatsApp Workspace (business_id = "abc123")  ← SAME!
```

### When Business Changes

Business context only changes when:
1. User explicitly switches business (multi-business owner)
2. User logs out and logs in to different business
3. Admin assigns user to different business

## Security Rules

### Default Deny

```javascript
// Every API endpoint assumes no access by default
function checkAccess(userId, businessId, resource) {
    // 1. Verify user belongs to business
    const member = await db.query(
        'SELECT * FROM business_members WHERE user_id = ? AND business_id = ?',
        [userId, businessId]
    );

    if (!member) {
        throw new Error('Access denied');  // Default: DENY
    }

    // 2. Check role permissions
    if (!hasPermission(member.role, resource)) {
        throw new Error('Insufficient permissions');
    }

    return true;
}
```

### No Cross-Business Access

```javascript
// ❌ This should NEVER be possible
GET /api/business/other-business-id/products

// ✅ Only access own business
GET /api/products  // Uses business_id from JWT
```

## Adding a New User to Business

### Invite Flow

```
1. Owner sends invite
   └─► Create invite token with business_id

2. New user accepts invite
   └─► Verify invite token

3. Create user account (if new)
   └─► Create user_id

4. Link to business
   └─► INSERT INTO business_members (user_id, business_id, role)

5. Return JWT with business context
   └─► { sub: user_id, bid: business_id, role: "member" }
```

## Multi-Business Users

Some users may belong to multiple businesses (consultants, agencies):

```sql
-- User belongs to multiple businesses
SELECT * FROM business_members WHERE user_id = 'user123';

-- Results:
-- user_id  | business_id | role
-- user123  | business_a  | owner
-- user123  | business_b  | admin
-- user123  | business_c  | member
```

### Business Switcher UI

```
┌─────────────────────────────────┐
│  Current: Evolve Robot Lab     │
│  ─────────────────────────────  │
│  Switch to:                     │
│  • Acme Corporation            │
│  • Beta Startup                │
└─────────────────────────────────┘
```

When switching:
1. New JWT issued with different `bid`
2. All workspaces reload with new context
3. Data filtered by new business_id

## Best Practices

### For Developers

1. **Always use business_id** - Never query without it
2. **Extract from JWT** - Don't trust client-provided business_id
3. **Validate membership** - Verify user belongs to business
4. **Log with context** - Include business_id in all logs
5. **Test isolation** - Verify cross-business access is blocked

### For API Design

```javascript
// ✅ Good: business_id from JWT
app.get('/api/products', auth, (req, res) => {
    const products = await getProducts(req.businessId);
});

// ❌ Bad: business_id from URL (can be spoofed)
app.get('/api/business/:bid/products', (req, res) => {
    const products = await getProducts(req.params.bid);
});
```

### For Database Queries

```sql
-- ✅ Always include business_id in WHERE clause
SELECT * FROM products
WHERE business_id = ? AND active = true;

-- ✅ Always include business_id in INSERT
INSERT INTO products (id, business_id, name, price)
VALUES (?, ?, ?, ?);

-- ✅ Always include business_id in UPDATE
UPDATE products
SET price = ?
WHERE id = ? AND business_id = ?;

-- ✅ Always include business_id in DELETE
DELETE FROM products
WHERE id = ? AND business_id = ?;
```
