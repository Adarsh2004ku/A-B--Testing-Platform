# A/B Testing Platform

A simplified A/B testing platform built with FastAPI and PostgreSQL. Provides core experimentation functionality including user assignment, event tracking, and statistical analysis.

## Features

- **User Assignment**: Consistent hashing for fair experiment assignment
- **Event Tracking**: Log conversion and other events
- **Statistical Analysis**: Z-test significance testing and SRM detection
- **REST API**: Simple endpoints for assignment, events, and results
- **Basic Dashboard**: Web interface for viewing results

## Quick Start

1. **Start PostgreSQL**:
   ```bash
   make run
   ```

2. **Run migrations**:
   ```bash
   make migrate
   ```

3. **Seed sample data**:
   ```bash
   make seed
   ```

4. **Start the API**:
   ```bash
   uvicorn src.api.main:app --reload
   ```

5. **View results**:
   - API: http://localhost:8000/docs
   - Dashboard: Open `src/dashboard/index.html` in browser

## API Endpoints

- `POST /api/v1/assign` - Assign user to experiment variant
- `POST /api/v1/events` - Log user events
- `GET /api/v1/results/{experiment_name}` - Get experiment results

## Project Structure

```
src/
├── api/
│   ├── main.py          # FastAPI app
│   └── routes/          # API endpoints
├── core/
│   ├── assignment.py    # User assignment logic
│   └── stats/           # Statistical analysis
├── models/              # SQLAlchemy models
└── utils/               # Database and logging utilities

scripts/
├── seed.py              # Sample data setup
└── generate_data.py     # Test data generation
```

## Dependencies

<<<<<<< HEAD
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
=======
- FastAPI
- SQLAlchemy
- PostgreSQL
- SciPy/NumPy
- Docker
>>>>>>> 5325f85 (update workfloe.md)
