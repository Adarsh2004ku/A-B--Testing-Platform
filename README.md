# A/B Testing Platform

A production-grade experimentation platform built with FastAPI, PostgreSQL, SQLAlchemy, and MLflow. Implements the same core architecture used by Netflix, Uber, and Airbnb for data-driven product decisions — consistent hashing for fair user assignment, statistical significance testing, SRM detection, and a live results dashboard.

> **For recruiters:** This project demonstrates applied statistics, backend engineering, database design, and MLOps — all in one end-to-end system built from scratch. Jump to [What Recruiters Look For](#what-recruiters-look-for) for a quick summary.

---

## Problem Statement

Companies make product decisions based on guesses. Testing changes properly — fair user splitting, statistically correct analysis, experiment isolation — is hard to do right. Enterprise tools like Optimizely and LaunchDarkly cost thousands of dollars per month. This platform solves the same core problems from scratch using open-source tools.

**Real-world use cases this platform supports:**

- An e-commerce company tests whether a green checkout button converts better than a red one
- A fintech startup safely rolls out a new payment flow to 10% of users before full release
- A SaaS product compares two onboarding flows across mobile vs desktop users separately
- A data science team validates whether a new recommendation model improves engagement on live traffic

---

## What It Does

- **Fair user assignment** — consistent hashing ensures the same user always gets the same variant, with no database lookup required
- **Segmentation** — filter experiment eligibility by country, device type, or user type
- **Statistical analysis** — four statistical models implemented from scratch (details below)
- **Experiment tracking** — every assignment and conversion event persisted to PostgreSQL
- **MLflow integration** — all experiment results automatically logged with metrics, params, and ship/no-ship decisions
- **Live dashboard** — visual charts showing variant distribution, conversion rates, and significance badges
- **REST API** — three production-ready endpoints powering the entire platform

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI + Uvicorn | Async, auto-generates OpenAPI docs |
| Database | PostgreSQL 15 | ACID compliance, UUID primary keys |
| ORM + Migrations | SQLAlchemy 2.0 + Alembic | Type-safe queries, schema versioning |
| Statistics | SciPy + NumPy | Industry-standard scientific computing |
| Experiment Tracking | MLflow | Standard MLOps tool for experiment logging |
| Frontend Dashboard | Vanilla HTML + Chart.js | Zero-dependency, browser-native |
| Containerization | Docker + Docker Compose | Reproducible environments |
| Logging | Structured JSON | Parseable by Grafana/Loki/Splunk |

---

## Statistical Models

This is the core of the platform. Four statistical methods are implemented in `src/core/stats/engine.py`, each solving a distinct problem in experimentation.

### 1. Two-Sample Z-Test for Proportions

**What it answers:** Is the difference in conversion rates between control and treatment statistically real, or could it be random chance?

**Why Z-test (not T-test):** Conversion rate data is binary (converted: yes/no), making it a proportion problem. Z-test is the correct choice for large samples with binary outcomes. T-test is for continuous data like revenue or session duration.

**Formula used:**

```
z = (p_treatment - p_control) / sqrt(p_pooled * (1 - p_pooled) * (1/n1 + 1/n2))

p_pooled = (conversions_control + conversions_treatment) / (n_control + n_treatment)
```

**Output:** p-value, z-score, relative lift %, absolute lift, 95% confidence interval, significance flag.

**Significance threshold:** p < 0.05 (two-tailed). This means there is less than a 5% probability that the observed difference occurred by chance.

**Real result on 10,000-user dataset:**
```
Control   conversion rate:  1.87%   (62 / 3,324 users)
Treatment conversion rate:  2.36%   (80 / 3,391 users)
Relative lift:              +26.48%
Z-score:                    1.4067
P-value:                    0.1595
Decision:                   Not significant — keep running
```
The treatment showed a 26% lift but p=0.16 means there is a 16% chance this difference is noise. The platform correctly held back the ship decision.

---

### 2. Chi-Square Goodness of Fit — SRM Detection

**What it answers:** Were users assigned in the expected ratio? If not, the entire experiment is invalid regardless of how good the results look.

**Why this matters:** If you expect 50% control / 50% treatment but get 60% / 40%, your assignment engine has a bug. Even correct-looking results cannot be trusted — some users may have been preferentially routed to one variant based on an unintended factor (browser type, time of day, geography). This is called a Sample Ratio Mismatch (SRM).

**Model used:** Chi-square goodness of fit test comparing observed counts against expected counts derived from traffic weights.

```
chi2 = sum((observed - expected)^2 / expected)
```

**SRM threshold:** p < 0.01 (stricter than significance threshold because SRM invalidates the whole experiment, not just one metric).

**Example:**
```
Expected:  [500, 500]   (50/50 split)
Observed:  [502, 498]   → chi2=0.008, p=0.93  → ✅ No SRM, healthy
Observed:  [700, 300]   → chi2=80.0,  p≈0.00  → ⚠️  SRM DETECTED — discard results
```

---

### 3. Statistical Power Analysis

**What it answers:** How many users do you need before running the experiment?

**Why it matters:** Starting an experiment without calculating sample size is one of the most common mistakes in A/B testing. Stop too early and you make decisions on noise (underpowered). Run too long and you waste resources on an experiment that has already answered the question.

**Inputs:** baseline conversion rate, minimum detectable effect (MDE), alpha (0.05), power (0.80).

**Formula:**

```
n = ((z_alpha * sqrt(2 * p_avg * (1 - p_avg)) + z_beta * sqrt(p1*(1-p1) + p2*(1-p2)))^2) / (p2 - p1)^2
```

**Example output:**
```
Baseline rate:                10%
Minimum detectable effect:    2%   (want to detect improvement to 12%)
Required per variant:         3,841 users
Total required:               7,682 users
```

---

### 4. Bonferroni Correction — Multiple Testing Adjustment

**What it answers:** When testing multiple variants simultaneously, how do you prevent false positives from inflating?

**Why it matters:** If you run 20 statistical tests at alpha=0.05, you expect roughly 1 false positive by definition — even when nothing is actually different. This is the multiple comparisons problem. The Bonferroni correction adjusts the significance threshold downward proportionally.

**Correction:** `alpha_corrected = 0.05 / number_of_comparisons`

**Example with 3 variants:**
```
Original alpha:   0.05
Corrected alpha:  0.0167   (0.05 / 3)

Variant A: p=0.030 → NOT significant (0.030 > 0.0167)
Variant B: p=0.080 → NOT significant
Variant C: p=0.012 → SIGNIFICANT     (0.012 < 0.0167) ✅
```

---

## Project Structure

```
AB_Testing/
├── src/
│   ├── api/
│   │   ├── main.py                  # FastAPI app, CORS middleware, startup checks
│   │   └── routes/
│   │       ├── assign.py            # POST /api/v1/assign
│   │       ├── events.py            # POST /api/v1/events
│   │       └── results.py          # GET  /api/v1/results/{experiment}
│   ├── core/
│   │   ├── assignment.py           # Consistent hashing, segmentation logic
│   │   ├── mlflow_tracker.py       # MLflow run logging
│   │   └── stats/
│   │       └── engine.py           # Z-test, SRM, power analysis, Bonferroni
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── base.py
│   │   ├── user.py
│   │   ├── experiment.py
│   │   ├── variant.py
│   │   ├── assignment.py
│   │   ├── event.py
│   │   └── feature_flag.py
│   ├── utils/
│   │   ├── database.py             # Engine, session factory, health check
│   │   └── logger.py              # Structured JSON logger
│   └── dashboard/
│       └── index.html              # Live results dashboard
├── scripts/
│   ├── seed.py                     # Seed base experiment + variants
│   ├── generate_data.py            # Simulate 1000 users + conversions
│   └── load_csv_data.py            # Load external A/B test CSV into DB
├── alembic/                        # Versioned DB migrations
├── logs/                           # app.log in JSON format
├── data/                           # CSV datasets
├── docker-compose.yml
├── Makefile
├── requirements.txt
└── .env
```

---

## Quick Start

### Prerequisites

- Python 3.11+
- Docker Desktop running

### Setup

```bash
# Clone and enter project
git clone <repo-url>
cd AB_Testing

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start PostgreSQL
make run

# Run database migrations
alembic upgrade head

# Seed initial data
python scripts/seed.py

# Start the API server
uvicorn src.api.main:app --reload --port 8000
```

API is live at `http://localhost:8000`. Interactive docs at `http://localhost:8000/docs`.

---

## API Endpoints

### Assign a user to an experiment

```bash
POST /api/v1/assign
{
  "user_id": "user_001",
  "experiment_name": "checkout_button_color"
}
```

Response:
```json
{
  "assigned": true,
  "user_id": "user_001",
  "experiment": "checkout_button_color",
  "variant": "treatment",
  "config": { "button_color": "green" }
}
```

### Log a conversion event

```bash
POST /api/v1/events
{
  "user_id": "user_001",
  "experiment_name": "checkout_button_color",
  "event_type": "conversion"
}
```

### Get experiment results with full statistical analysis

```bash
GET /api/v1/results/checkout_button_color?log_to_mlflow=true
```

Response:
```json
{
  "experiment": "checkout_button_color",
  "status": "running",
  "srm_check": {
    "has_srm": false,
    "verdict": "✅ No SRM - assignment looks healthy",
    "p_value": 0.4136
  },
  "variants": [
    {
      "variant": "control",
      "assignments": 3324,
      "conversions": 62,
      "conversion_rate": 0.0187
    },
    {
      "variant": "treatment",
      "assignments": 3391,
      "conversions": 80,
      "conversion_rate": 0.0236,
      "significance": {
        "relative_lift": 26.48,
        "p_value": 0.1595,
        "is_significant": false,
        "ci_lower": -0.0019,
        "ci_upper": 0.0118
      }
    }
  ]
}
```

---

## Database Schema

Six tables designed to support the full experiment lifecycle:

| Table | Purpose | Key Constraint |
|---|---|---|
| `users` | User registry with segmentation attributes | `external_id` unique |
| `experiments` | Experiment config and lifecycle status | `name` unique, status enum |
| `variants` | Control/treatment config per experiment | FK to experiments |
| `assignments` | User-to-variant mapping | `UNIQUE(user_id, experiment_id)` |
| `events` | Conversion and behavioral events | FK to users + experiments |
| `feature_flags` | Percentage-based feature rollouts | `key` unique |

The `UNIQUE(user_id, experiment_id)` constraint on assignments is enforced at the database level — not just application level — meaning even under concurrent load, a user cannot be assigned two variants.

---

## MLflow Experiment Tracking

Every call to `/results?log_to_mlflow=true` creates an MLflow run with:

- **Params** — SRM result, significance flags per variant
- **Metrics** — assignments, conversions, conversion rate, p-value, z-score, relative lift per variant
- **Tags** — `winner`, `decision` (ship_treatment / keep_control / keep_running)

Start MLflow UI:

```bash
mlflow ui --backend-store-uri sqlite:///mlflow.db --port 5000
```

Open `http://localhost:5000` to compare experiment runs over time.

---

## Dashboard

Open `src/dashboard/index.html` in the browser while the API server is running. Calls your live FastAPI and renders:

- Total users and conversions
- Variant distribution bar chart
- Conversion rate comparison chart
- Statistical significance badge (significant / not significant yet)
- SRM check status with chi-square statistic
- Ship / keep running decision

---


Data flows from user action (assignment) through event logging, statistical analysis, MLflow tracking, and dashboard visualization. No step is outsourced to a library that hides the logic. The Z-test, SRM check, power analysis, and Bonferroni correction are all written from the formula up using SciPy primitives.

MLflow integration shows awareness of experiment management and reproducibility — a growing requirement in consulting engagements where clients ask how models and decisions can be audited.

The six-table PostgreSQL schema with foreign keys, uniqueness constraints, and Alembic migrations demonstrates database literacy that goes well beyond `pd.read_csv()`.

Being able to explain null hypothesis, Type I error, Type II error, statistical power, and confidence intervals — all of which appear directly in this project's output — prepares you for the technical screening rounds these firms run.


---

## Makefile Commands

```bash
make run        # Start Docker containers (PostgreSQL)
make stop       # Stop containers
make psql       # Open PostgreSQL shell
make logs       # Tail container logs
make clean      # Remove containers and volumes (deletes all data)
```

---

## Environment Variables

Create a `.env` file in the project root:

```env
POSTGRES_USER=abtest_user
POSTGRES_PASSWORD=abtest_pass
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=abtest_db
```

---

## Requirements

```
fastapi==0.111.0
uvicorn==0.29.0
sqlalchemy==2.0.30
alembic==1.13.1
psycopg2-binary==2.9.9
python-dotenv==1.0.1
scipy==1.14.1
numpy==2.0.0
mlflow==2.13.0
pytest==8.2.0
httpx==0.27.0
```
