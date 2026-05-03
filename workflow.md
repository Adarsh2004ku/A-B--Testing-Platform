# A/B Testing Platform - Complete Workflow Documentation

## System Overview

The A/B Testing Platform is a production-grade experimentation platform built with **FastAPI** and **PostgreSQL**. It handles user assignment to experiment variants, event tracking, and statistical analysis to determine if experiment results are statistically significant.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client Application                          │
└─────────────────┬───────────────────────────────────────────────────┘
                  │
        ┌─────────┴─────────┬──────────────┬──────────────┐
        │                   │              │              │
    POST /assign        POST /events   GET /results   GET /health
        │                   │              │              │
┌───────▼───────────────────▼──────────────▼──────────────▼──────────┐
│                        FastAPI Application                         │
│                                                                    │
│  ├─ src/api/main.py (FastAPI app setup, CORS, startup)           │
│  ├─ src/api/routes/assign.py (Assignment route)                  │
│  ├─ src/api/routes/events.py (Event logging route)               │
│  └─ src/api/routes/results.py (Results & analysis route)         │
│                                                                    │
│  ├─ src/core/assignment.py (Assignment logic)                    │
│  ├─ src/core/stats/engine.py (Statistical tests)                 │
│  ├─ src/models/ (Database models)                                │
│  └─ src/utils/ (Database, logging)                               │
└───────┬───────────────────────────────────────────────────────────┘
        │
┌───────▼──────────────────────────────────────────────────────────┐
│                    PostgreSQL Database                           │
│                                                                  │
│  Tables:                                                         │
│  ├─ users (user profiles with segments)                        │
│  ├─ experiments (experiment definitions & metadata)            │
│  ├─ variants (treatment variants with traffic weights)         │
│  ├─ assignments (which user got which variant)                 │
│  └─ events (user events: clicks, conversions, etc.)            │
└──────────────────────────────────────────────────────────────────┘
```

---

## Data Models

### 1. **User** Model (`src/models/user.py`)
Stores user information and segmentation attributes.

**Schema:**
```python
User:
  id → UUID (primary key)
  external_id → String (your app's user ID, unique)
  country → String (nullable) # for geographic segmentation
  device_type → String (mobile, desktop, tablet)
  user_type → String (free, premium, enterprise)
  attributes → JSON (custom attributes)
  created_at → DateTime
  
  Relationships:
  - assignments: one-to-many with Assignment
  - events: one-to-many with Event
```

### 2. **Experiment** Model (`src/models/experiment.py`)
Defines an A/B test experiment.

**Schema:**
```python
Experiment:
  id → UUID (primary key)
  name → String (unique, e.g., "checkout_button_color")
  description → String (nullable)
  status → Enum (draft, running, paused, completed)
  layer → String (logical group for experiments)
  target_segments → JSON (e.g., {"country": ["US", "CA"], "device_type": ["mobile"]})
  created_at → DateTime
  started_at → DateTime (nullable)
  ended_at → DateTime (nullable)
  
  Relationships:
  - variations: one-to-many with Variant
  - assignments: one-to-many with Assignment
  - events: one-to-many with Event
```

### 3. **Variant** Model (`src/models/variant.py`)
Represents a treatment variation in an experiment.

**Schema:**
```python
Variant:
  id → UUID (primary key)
  experiment_id → UUID (foreign key to Experiment)
  name → String (e.g., "control", "red_button", "green_button")
  is_control → Boolean (marks the baseline/control group)
  traffic_weight → Float (0.0-1.0, e.g., 0.5 = 50% of users)
  config → JSON (variant-specific configuration, delivered to client)
  created_at → DateTime
  
  Relationships:
  - experiment: many-to-one with Experiment
  - assignments: one-to-many with Assignment
```

### 4. **Assignment** Model (`src/models/assignment.py`)
Records which user was assigned to which variant.

**Schema:**
```python
Assignment:
  id → UUID (primary key)
  user_id → UUID (foreign key to User)
  experiment_id → UUID (foreign key to Experiment)
  variant_id → UUID (foreign key to Variant)
  assigned_at → DateTime
  
  Constraints:
  - Unique(user_id, experiment_id) → one user gets ONE variant per experiment
  
  Relationships:
  - user: many-to-one with User
  - experiment: many-to-one with Experiment
  - variant: many-to-one with Variant
```

### 5. **Event** Model (`src/models/event.py`)
Tracks user events (conversions, clicks, etc.) during an experiment.

**Schema:**
```python
Event:
  id → UUID (primary key)
  user_id → UUID (foreign key to User)
  experiment_id → UUID (foreign key to Experiment)
  event_type → String (e.g., "click", "conversion", "purchase")
  event_metadata → JSON (custom event data)
  created_at → DateTime
  
  Relationships:
  - user: many-to-one with User
  - experiment: many-to-one with Experiment
```

---

## Core Workflows

### **WORKFLOW 1: User Assignment to Experiment Variant**

**Entry Point:** `POST /api/v1/assign`

**Request:**
```json
{
  "user_id": "user123",
  "experiment_name": "checkout_button_color"
}
```

**Flow Diagram:**
```
Client Request
      │
      ▼
assign_router.assign()
      │ (in src/api/routes/assign.py)
      │
      ├─ Validate AssignRequest (user_id, experiment_name)
      │
      ▼
assign_user() function
      │ (in src/core/assignment.py)
      │
      ├─ Step 1: Load User from DB
      │  └─ db.query(User).filter(User.external_id == user_external_id).first()
      │  └─ If not found → return {"assigned": False, "reason": "user_not_found"}
      │
      ├─ Step 2: Load Running Experiment from DB
      │  └─ db.query(Experiment).filter(
      │     Experiment.name == experiment_name,
      │     Experiment.status == "running"
      │  ).first()
      │  └─ If not found → return {"assigned": False, "reason": "experiment_not_found"}
      │
      ├─ Step 3: Check for Existing Assignment (Sticky Assignment)
      │  └─ db.query(Assignment).filter(
      │     Assignment.user_id == user.id,
      │     Assignment.experiment_id == experiment.id
      │  ).first()
      │  └─ If exists → return existing variant (user always sees same variant)
      │     └─ Ensures consistent user experience
      │
      ├─ Step 4: Check Segmentation Rules
      │  └─ check_segment(user, experiment.target_segments)
      │  │
      │  └─ Validates segmentation criteria:
      │     ├─ Country filter (if specified)
      │     ├─ Device type filter (mobile, desktop, tablet)
      │     └─ User type filter (free, premium, enterprise)
      │  └─ If user doesn't match → return {"assigned": False, "reason": "segment_mismatch"}
      │
      ├─ Step 5: Deterministic User Bucketing
      │  │
      │  └─ bucket = get_bucket(user_id, experiment_id)
      │     │
      │     └─ Uses MD5 hash for deterministic assignment:
      │        key = f"{user_id}:{experiment_id}"
      │        hash_hex = hashlib.md5(key.encode()).hexdigest()
      │        bucket = int(hash_hex[:8], 16) % 100
      │        
      │        Result: bucket ∈ [0, 99]
      │        (Same user_id + experiment_id always produces same bucket)
      │
      ├─ Step 6: Select Variant Based on Traffic Weight
      │  │
      │  └─ select_variant(bucket, variants)
      │     │
      │     └─ Matches bucket to variant using cumulative traffic weights:
      │        Example:
      │        - Variant "control": traffic_weight = 0.5 (50%)
      │        - Variant "treatment": traffic_weight = 0.5 (50%)
      │        
      │        Cumulative:
      │        - bucket [0, 49] → "control"
      │        - bucket [50, 99] → "treatment"
      │
      ├─ Step 7: Save Assignment to DB
      │  │
      │  ├─ Create Assignment record:
      │  │  assignment = Assignment(
      │  │    user_id = user.id,
      │  │    experiment_id = experiment.id,
      │  │    variant_id = variant.id
      │  │  )
      │  │
      │  ├─ db.add(assignment)
      │  └─ db.commit()
      │
      ├─ Step 8: Log Assignment
      │  └─ logger.info("User assigned", extra={...})
      │
      ▼
Return Assignment Result
```

**Response:**
```json
{
  "assigned": true,
  "user_id": "user123",
  "experiment": "checkout_button_color",
  "variant": "control",
  "config": {
    "button_color": "#007ACC",
    "button_text": "Buy Now"
  }
}
```

**Key Functions:**
- `assign_user()` → Main assignment orchestrator
- `get_bucket()` → Deterministic hashing for user bucketing
- `select_variant()` → Matches bucket to variant based on traffic weights
- `check_segment()` → Validates segmentation rules (country, device, user type)

---

### **WORKFLOW 2: Event Logging During Experiment**

**Entry Point:** `POST /api/v1/events`

**Request:**
```json
{
  "user_id": "user123",
  "experiment_name": "checkout_button_color",
  "event_type": "conversion",
  "metadata": {
    "order_value": 99.99,
    "timestamp": "2026-05-03T10:30:00Z"
  }
}
```

**Flow Diagram:**
```
Client Event
      │
      ▼
events_router.log_event()
      │ (in src/api/routes/events.py)
      │
      ├─ Validate EventRequest
      │  (user_id, experiment_name, event_type, metadata)
      │
      ├─ Step 1: Load User from DB
      │  └─ db.query(User).filter(User.external_id == request.user_id).first()
      │  └─ If not found → HTTP 404 "user_not_found"
      │
      ├─ Step 2: Load Experiment from DB
      │  └─ db.query(Experiment).filter(
      │     Experiment.name == request.experiment_name
      │  ).first()
      │  └─ If not found → HTTP 404 "experiment_not_found"
      │
      ├─ Step 3: Create Event Record
      │  │
      │  └─ event = Event(
      │     user_id = user.id,
      │     experiment_id = experiment.id,
      │     event_type = request.event_type,
      │     event_metadata = request.metadata
      │  )
      │
      ├─ Step 4: Save Event to DB
      │  │
      │  ├─ db.add(event)
      │  └─ db.commit()
      │
      ├─ Step 5: Log Event
      │  │
      │  └─ logger.info("Event logged", extra={
      │     "user_id": request.user_id,
      │     "experiment": request.experiment_name,
      │     "event_type": request.event_type
      │  })
      │
      ▼
Return Success Response
```

**Response:**
```json
{
  "status": "ok",
  "event_type": "conversion"
}
```

**Key Points:**
- Events are tied to both a user AND an experiment
- Multiple events per user are allowed (e.g., multiple clicks)
- Event metadata is flexible (JSON column) for custom data
- Events are immutable once logged

---

### **WORKFLOW 3: Calculate Results & Statistical Significance**

**Entry Point:** `GET /api/v1/results/{experiment_name}`

**Flow Diagram:**
```
Client Request
      │
      ▼
results_router.get_results()
      │ (in src/api/routes/results.py)
      │
      ├─ Step 1: Load Experiment from DB
      │  └─ db.query(Experiment).filter(
      │     Experiment.name == experiment_name
      │  ).first()
      │  └─ If not found → HTTP 404 "experiment_not_found"
      │
      ├─ Step 2: Load All Variants for Experiment
      │  │
      │  └─ db.query(Variant).filter(
      │     Variant.experiment_id == experiment.id
      │  ).all()
      │
      ├─ Step 3: For Each Variant, Calculate Metrics
      │  │
      │  └─ For each variant:
      │     │
      │     ├─ Count Total Assignments:
      │     │  └─ db.query(Assignment).filter(
      │     │     Assignment.experiment_id == experiment.id,
      │     │     Assignment.variant_id == variant.id
      │     │  ).count()
      │     │
      │     ├─ Count Conversions:
      │     │  └─ db.query(Event).join(Assignment, ...).filter(
      │     │     Assignment.variant_id == variant.id,
      │     │     Event.event_type == "conversion"
      │     │  ).count()
      │     │
      │     ├─ Calculate Conversion Rate:
      │     │  └─ conversion_rate = conversions / assignments
      │     │
      │     └─ Store variant stats:
      │        {
      │          "variant": "control",
      │          "is_control": true,
      │          "assignments": 5000,
      │          "conversions": 500,
      │          "conversion_rate": 0.10
      │        }
      │
      ├─ Step 4: Collect Assignment Distribution for SRM Check
      │  │
      │  └─ Create lists:
      │     observed_counts = [5000, 5100]  # assignments per variant
      │     expected_weights = [0.5, 0.5]    # traffic_weight per variant
      │
      ├─ Step 5: Perform SRM Check (Sample Ratio Mismatch)
      │  │
      │  └─ srm_check(expected_weights, observed_counts)
      │     │
      │     │ Purpose: Detect if assignment is broken
      │     │ 
      │     └─ Uses Chi-Square Goodness of Fit Test:
      │        │
      │        ├─ Total users = 10,100
      │        ├─ Expected distribution:
      │        │  - control: 0.5 × 10,100 = 5,050
      │        │  - treatment: 0.5 × 10,100 = 5,050
      │        │
      │        ├─ Observed distribution:
      │        │  - control: 5,000
      │        │  - treatment: 5,100
      │        │
      │        ├─ Chi² = Σ((observed - expected)² / expected)
      │        ├─ p_value = probability of this distribution by chance
      │        │
      │        └─ If p_value < 0.01 → SRM DETECTED (experiment is broken!)
      │           If p_value ≥ 0.01 → No SRM (assignment looks good)
      │
      ├─ Step 6: For Each Non-Control Variant, Perform Z-Test
      │  │
      │  └─ z_test_proportions(
      │     control_conversions, control_assignments,
      │     treatment_conversions, treatment_assignments
      │  )
      │     │
      │     │ Purpose: Test if treatment conversion rate significantly
      │     │           differs from control conversion rate
      │     │
      │     └─ Statistical Test (2-tailed Z-test):
      │        │
      │        ├─ p_control = control_conversions / control_assignments
      │        │            = 500 / 5000 = 0.10 (10%)
      │        │
      │        ├─ p_treatment = treatment_conversions / treatment_assignments
      │        │              = 575 / 5100 ≈ 0.1127 (11.27%)
      │        │
      │        ├─ p_pooled = (500 + 575) / (5000 + 5100)
      │        │           = 1075 / 10100 ≈ 0.1064
      │        │
      │        ├─ Standard Error:
      │        │  se = √(p_pooled × (1 - p_pooled) × (1/n_control + 1/n_treatment))
      │        │     = √(0.1064 × 0.8936 × (1/5000 + 1/5100))
      │        │     ≈ 0.00628
      │        │
      │        ├─ Z-Score:
      │        │  z = (p_treatment - p_control) / se
      │        │    = (0.1127 - 0.10) / 0.00628
      │        │    ≈ 2.02
      │        │
      │        ├─ P-Value (2-tailed):
      │        │  p_value = 2 × (1 - CDF(|z|))
      │        │          = 2 × (1 - CDF(2.02))
      │        │          ≈ 0.0435
      │        │
      │        ├─ Relative Lift:
      │        │  lift = (p_treatment - p_control) / p_control × 100%
      │        │       = (0.1127 - 0.10) / 0.10 × 100%
      │        │       = 12.7%
      │        │
      │        ├─ 95% Confidence Interval:
      │        │  margin = 1.96 × se ≈ 0.0123
      │        │  ci_lower = (p_treatment - p_control) - margin ≈ -0.0010
      │        │  ci_upper = (p_treatment - p_control) + margin ≈ 0.0256
      │        │
      │        ├─ Significance Determination:
      │        │  is_significant = (p_value < 0.05)
      │        │  (p_value ≈ 0.0435 < 0.05) → TRUE (Significant!)
      │        │
      │        └─ Result:
      │           {
      │             "control_rate": 0.10,
      │             "treatment_rate": 0.1127,
      │             "relative_lift": 12.7,
      │             "absolute_lift": 0.0127,
      │             "z_score": 2.02,
      │             "p_value": 0.0435,
      │             "ci_lower": -0.0010,
      │             "ci_upper": 0.0256,
      │             "is_significant": true,
      │             "confidence_level": "95%"
      │           }
      │
      ▼
Return Results Response
```

**Response:**
```json
{
  "experiment": "checkout_button_color",
  "status": "running",
  "srm_check": {
    "expected_counts": [5050, 5050],
    "observed_counts": [5000, 5100],
    "chi2_statistic": 0.9901,
    "p_value": 0.3195,
    "has_srm": false,
    "verdict": "No SRM - assignment looks healthy"
  },
  "variants": [
    {
      "variant": "control",
      "is_control": true,
      "assignments": 5000,
      "conversions": 500,
      "conversion_rate": 0.10
    },
    {
      "variant": "red_button",
      "is_control": false,
      "assignments": 5100,
      "conversions": 575,
      "conversion_rate": 0.1127,
      "significance": {
        "control_rate": 0.10,
        "treatment_rate": 0.1127,
        "relative_lift": 12.7,
        "absolute_lift": 0.0127,
        "z_score": 2.02,
        "p_value": 0.0435,
        "ci_lower": -0.0010,
        "ci_upper": 0.0256,
        "is_significant": true,
        "confidence_level": "95%"
      }
    }
  ]
}
```

**Key Functions:**
- `get_results()` → Main orchestrator
- `z_test_proportions()` → 2-tailed Z-test for difference in proportions
- `srm_check()` → Chi-square goodness of fit test for assignment distribution

---

## Statistical Methods

### **Z-Test for Proportions** (`src/core/stats/engine.py`)

**What it does:** Tests if the conversion rate difference between control and treatment is statistically significant or due to random chance.

**When it's used:** After collecting enough data, compare conversion rates between variants.

**Formula:**
```
z = (p_treatment - p_control) / √(p_pooled × (1 - p_pooled) × (1/n_control + 1/n_treatment))

where:
- p_control = control conversions / control assignments
- p_treatment = treatment conversions / treatment assignments
- p_pooled = (control conversions + treatment conversions) / (control assignments + treatment assignments)
```

**Interpretation:**
- **p_value < 0.05** → Result is statistically significant (95% confidence)
- **p_value ≥ 0.05** → Insufficient evidence; keep running the experiment

---

### **SRM Check (Sample Ratio Mismatch)** (`src/core/stats/engine.py`)

**What it does:** Detects if users were assigned to variants in the expected ratio.

**When it's used:** On every results page load to validate assignment integrity.

**Formula:**
```
Chi² = Σ((observed_count - expected_count)² / expected_count)
p_value = P(Chi² | df = k-1)

where k = number of variants
```

**Example:**
```
Expected: 50% control, 50% treatment (1000 users total)
- Expected: 500 control, 500 treatment

Observed: 600 control, 400 treatment
- This is suspicious! If Chi² test p_value < 0.01 → SRM DETECTED

Why this matters:
- If assignment is broken, results are meaningless
- Common causes: hash collision, rounding errors, bugs in assignment logic
- If SRM detected: pause experiment, fix assignment, restart
```

---

## API Endpoints Summary

| Endpoint | Method | Purpose | Request | Response |
|----------|--------|---------|---------|----------|
| `/health` | GET | Health check | - | `{"status": "ok", "db": true/false}` |
| `/` | GET | Root info | - | `{"status": "ok", "message": "..."}` |
| `/api/v1/assign` | POST | Assign user to variant | `{user_id, experiment_name}` | `{assigned, variant, config}` |
| `/api/v1/events` | POST | Log user event | `{user_id, experiment_name, event_type, metadata}` | `{status: "ok"}` |
| `/api/v1/results/{experiment_name}` | GET | Get experiment results | - | `{experiment, variants, srm_check}` |

---

## Database Connection Flow

```
FastAPI Application
      │
      ▼
src/utils/database.py
      │
      ├─ check_db_connection()
      │  └─ Tests PostgreSQL connection at startup
      │
      ├─ get_db() → Generator[Session]
      │  └─ Creates SQLAlchemy session for each request
      │  └─ Used via Depends(get_db) in route handlers
      │
      ▼
PostgreSQL (port 5432)
```

---

## Logging Strategy

All components log to `src/utils/logger.py`:

**Events logged:**
- **Startup**: Database connection, application initialization
- **Assignment**: User assignments, segment exclusions
- **Events**: Event logging, user tracking
- **Statistics**: Z-test results, SRM checks, significance findings
- **Errors**: User not found, experiment not found, etc.

**Log output**: JSON formatted with timestamp, level, message, and context

---

## Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| User not found | HTTP 404 + "user_not_found" |
| Experiment not running | Return "experiment_not_found" |
| User doesn't match segments | Skip assignment: "segment_mismatch" |
| No variants found | Skip assignment: "no_variant" |
| Empty assignment/event groups | Z-test returns error |
| SRM detected | Flag in results; recommend investigation |

---

## Complete Request-Response Cycle Example

### Scenario: Red Button Test

**Step 1: Create/Setup Experiment** (Data prep, not shown in API)
```
Experiment: "checkout_button_color"
- Status: running
- Variant 1: "control" (is_control=true, traffic_weight=0.5)
- Variant 2: "red_button" (is_control=false, traffic_weight=0.5)
```

**Step 2: User Visits & Gets Assignment**
```
POST /api/v1/assign
{
  "user_id": "user123",
  "experiment_name": "checkout_button_color"
}

Response:
{
  "assigned": true,
  "user_id": "user123",
  "experiment": "checkout_button_color",
  "variant": "control",
  "config": {"button_color": "#007ACC"}
}
```

**Step 3: User Clicks Button**
```
POST /api/v1/events
{
  "user_id": "user123",
  "experiment_name": "checkout_button_color",
  "event_type": "conversion",
  "metadata": {"order_value": 99.99}
}

Response:
{
  "status": "ok",
  "event_type": "conversion"
}
```

**Step 4: Analyze Results (After ~10k users)**
```
GET /api/v1/results/checkout_button_color

Response: (see results workflow above)
{
  "experiment": "checkout_button_color",
  "srm_check": {...},
  "variants": [
    {
      "variant": "control",
      "assignments": 5000,
      "conversions": 500,
      "conversion_rate": 0.10
    },
    {
      "variant": "red_button",
      "assignments": 5100,
      "conversions": 575,
      "conversion_rate": 0.1127,
      "significance": {
        "is_significant": true,
        "relative_lift": 12.7,
        "p_value": 0.0435
      }
    }
  ]
}
```

**Decision**: Red button shows 12.7% lift with p=0.0435 < 0.05 → **Statistically Significant** → Ship red button to 100% of users!

---

## Key Design Principles

1. **Sticky Assignment**: Once assigned, user always sees same variant (ensures consistent experience)
2. **Deterministic Bucketing**: Same user always maps to same bucket (reproducible, no randomness)
3. **Stateless Scaling**: No session storage needed; can run multiple server instances
4. **Segment Targeting**: Can exclude users by geography, device, user tier
5. **Flexible Events**: Track any event type (clicks, views, purchases, custom)
6. **Statistical Rigor**: Proper hypothesis testing before shipping changes
7. **SRM Monitoring**: Detect broken assignments before trusting results

---

## File Structure Reference

```
src/
├─ api/
│  ├─ main.py (FastAPI app setup)
│  └─ routes/
│     ├─ assign.py (POST /assign)
│     ├─ events.py (POST /events)
│     └─ results.py (GET /results)
├─ core/
│  ├─ assignment.py (User bucketing & variant selection)
│  └─ stats/
│     └─ engine.py (Z-test, SRM check)
├─ models/
│  ├─ base.py (SQLAlchemy base)
│  ├─ user.py
│  ├─ experiment.py
│  ├─ variant.py
│  ├─ assignment.py
│  └─ event.py
└─ utils/
   ├─ database.py (SQLAlchemy session, DB checks)
   └─ logger.py (JSON logging)
```

---

## Execution Flow Summary

```
1. CLIENT sends assignment request
   ↓
2. ASSIGN ROUTE validates & calls assign_user()
   ↓
3. ASSIGNMENT ENGINE performs:
   - Load user profile
   - Validate experiment is running
   - Check for sticky assignment
   - Validate segments
   - Hash-based bucketing
   - Select variant by traffic weight
   - Save assignment to DB
   ↓
4. CLIENT receives variant config
   ↓
5. CLIENT renders variant UI & logs events
   ↓
6. EVENT ROUTE saves events to DB
   ↓
7. ANALYST queries results
   ↓
8. RESULTS ROUTE performs:
   - Count assignments per variant
   - Count conversions per variant
   - Perform SRM check (chi-square test)
   - Perform Z-tests vs control
   - Return statistical summary
   ↓
9. ANALYST reviews p-values and significance
   ↓
10. DECISION: Ship treatment or keep control
```

This workflow ensures statistical rigor, operational robustness, and actionable insights for A/B testing at scale.
