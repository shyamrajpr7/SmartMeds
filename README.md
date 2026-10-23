# 💊 SmartMeds

> An intelligent medication management system built with Python.

## 📋 Overview

SmartMeds is a smart medication management application that helps users track prescriptions, set reminders, check drug interactions, and manage their health data effectively.

## ✨ Features

- 📅 **Medication Scheduling** — Set up and manage medication schedules
- ⏰ **Smart Reminders** — Get notified when it's time to take your medication
- 🔍 **Drug Interaction Checker** — Check for potential drug interactions
- 📊 **Health Dashboard** — Track adherence and health metrics
- 💾 **Secure Storage** — Encrypted local storage for sensitive health data
- 🗄️ **Pluggable Storage** — SQLite out of the box, MongoDB when you need it
- 📤 **Export Reports** — Export medication logs and reports

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/shyamrajpr7/SmartMeds.git
cd SmartMeds

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
python -m smartmeds
```

## 💾 Storage Backends

SmartMeds stores medications and dose logs through a small backend interface
(`smartmeds/db/base.py`), so SQLite and MongoDB are fully interchangeable.

| Backend  | Driver            | Default location                    |
| -------- | ----------------- | ----------------------------------- |
| `sqlite` | SQLAlchemy (local)| `~/.smartmeds/smartmeds.db`          |
| `mongodb`| PyMongo (server)  | `mongodb://localhost:27017/smartmeds`|

SQLite is the default and needs no extra setup. Select a backend with the
`--db` flag or with environment variables:

```bash
# Flag (wins over the environment)
python -m smartmeds --db mongodb list

# Environment
export SMARTMEDS_DB_BACKEND=mongodb
export SMARTMEDS_MONGODB_URI="mongodb://localhost:27017"
export SMARTMEDS_MONGODB_DB="smartmeds"
python -m smartmeds list
```

| Variable                  | Default                          | Description                        |
| ------------------------- | -------------------------------- | ---------------------------------- |
| `SMARTMEDS_DB_BACKEND`    | `sqlite`                         | `sqlite` or `mongodb`              |
| `SMARTMEDS_DB_PATH`       | `~/.smartmeds/smartmeds.db`      | SQLite file location               |
| `SMARTMEDS_MONGODB_URI`   | `mongodb://localhost:27017`       | MongoDB connection string          |
| `SMARTMEDS_MONGODB_DB`    | `smartmeds`                      | MongoDB database name              |

`MONGODB_URI` / `MONGO_URI` and `MONGODB_DATABASE` are accepted as aliases for
the two MongoDB variables, so the standard Atlas variable names work as-is.
When the database name is omitted it is taken from the connection string, so
`mongodb+srv://user:pass@cluster.mongodb.net/smartmeds` just works.

If a MongoDB connection string is present and no backend was selected
explicitly, MongoDB is chosen automatically — setting `MONGODB_URI` is enough.

On serverless platforms (Vercel) the filesystem is read-only outside `/tmp`,
so the SQLite fallback is written to `/tmp/smartmeds.db` there.

### Using MongoDB

```bash
# 1. Install the driver (already in requirements.txt)
pip install pymongo

# 2. Run a local server
mongod --dbpath /path/to/data

# ... or point at MongoDB Atlas
export SMARTMEDS_MONGODB_URI="mongodb+srv://user:password@cluster.mongodb.net"

# 3. Use it
python -m smartmeds --db mongodb add --name Metformin --dose 500 --unit mg
python -m smartmeds --db mongodb list
```

Check what the app is talking to:

```bash
python -m smartmeds db info
```

```
       🗄️  Storage Backend
╭─────────────┬───────────────────────────╮
│ Setting     │ Value                     │
├─────────────┼───────────────────────────┤
│ Backend     │ mongodb                   │
│ URI         │ mongodb://127.0.0.1:27018 │
│ Database    │ smartmeds                 │
│ Medications │ 2                         │
│ Dose logs   │ 0                         │
╰─────────────┴───────────────────────────╯
```

## 🌐 HTTP API

The same backend powers a REST API (`smartmeds/api/`), which is what gets
deployed to Vercel:

```bash
# Locally
pip install -r requirements.txt
uvicorn smartmeds.api.app:app --reload

# Interactive docs
open http://127.0.0.1:8000/docs
```

| Method   | Path                       | Description                             |
| -------- | -------------------------- | --------------------------------------- |
| `GET`    | `/health`                  | Liveness + which backend is connected   |
| `GET`    | `/api/medications`         | List medications                        |
| `POST`   | `/api/medications`         | Create a medication                     |
| `GET`    | `/api/medications/{id}`    | Fetch one medication                    |
| `PATCH`  | `/api/medications/{id}`    | Update a medication                     |
| `DELETE` | `/api/medications/{id}`    | Delete a medication                     |
| `GET`    | `/api/schedule?hours=24`   | Upcoming doses                          |
| `GET`    | `/api/dose-logs`           | Dose log history                        |
| `POST`   | `/api/dose-logs`           | Record a dose                           |
| `POST`   | `/api/interactions/check`  | Check a list of drugs for interactions  |

Every endpoint is also available without the `/api` prefix.

Two collections are used: `medications` and `dose_logs`, both indexed on the
fields the app queries.

## 🚀 Deploy to Vercel + MongoDB Atlas

The repository is already set up for this: `app.py` is the Vercel entrypoint,
`vercel.json` configures the function, and the API reads its MongoDB
connection string from the environment.

### 1. Create the Atlas cluster

1. Sign in at [cloud.mongodb.com](https://cloud.mongodb.com) and create a
   **Free** cluster (the tier formerly called **M0**; region: pick the one
   closest to your Vercel function region). Only one Free cluster is allowed
   per project.
2. **Database Access** → *Add New Database User* → choose a username and a
   password, and grant **Read and write to any database** (or restrict it to
   the `smartmeds` database).
3. **Network Access** → *Add IP Address* → **Allow access from anywhere**
   (`0.0.0.0/0`). Vercel functions run in shared infrastructure with dynamic
   egress IPs, so a single IP cannot be allow-listed.
   - If you enable **Static Outbound IPs** for your Vercel project (Fluid
     compute), allow-list those instead and keep the database private.
4. Copy the connection string (*Connect* → *Drivers*) and fill in your
   username and password:

```
mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
```

### 2. Deploy to Vercel

```bash
# Install the CLI (if needed)
npm i -g vercel

# Log in and create/link the project
vercel login
vercel link          # or: import the repo at vercel.com/new

# Set the environment variables (all environments)
vercel env add SMARTMEDS_DB_BACKEND mongodb
vercel env add MONGODB_URI "mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
vercel env add SMARTMEDS_MONGODB_DB smartmeds

# Deploy
vercel --prod
```

`SMARTMEDS_DB_BACKEND` and `SMARTMEDS_MONGODB_DB` are optional — setting
`MONGODB_URI` alone is enough, the backend and database name are detected.

Or set the same variables in the dashboard under
**Project → Settings → Environment Variables**.

Then verify the deployment:

```bash
curl https://<your-project>.vercel.app/health
# {"status":"ok","version":"0.1.0","backend":"mongodb","database":"smartmeds"}

open https://<your-project>.vercel.app/docs   # interactive API docs
```

### 3. Use the deployed API

```bash
curl -X POST https://<your-project>.vercel.app/api/medications \
  -H "Content-Type: application/json" \
  -d '{
        "name": "Metformin",
        "dosage": {"amount": 500, "unit": "mg"},
        "schedule": {"frequency": "daily", "times_per_day": 2,
                     "times": ["08:00:00", "20:00:00"]},
        "pills_remaining": 30
      }'
```

### 4. Point the CLI at the same Atlas cluster

The CLI and the API share the backend, so both can use Atlas:

```bash
export SMARTMEDS_DB_BACKEND=mongodb
export MONGODB_URI="mongodb+srv://<user>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority"
python -m smartmeds list
python -m smartmeds add --name Aspirin --dose 100 --unit mg
```

### Deployment notes

- **Same region.** Deploy the Vercel function in the region closest to your
  Atlas cluster (Project → Settings → Functions → Region).
- **Free tier pauses.** A Free cluster is paused after a long idle period, and
  the first request after that can take a moment while it wakes up. A paid
  Flex or `M10` cluster stays warm.
- **Cold starts.** The MongoDB client is created once per function instance
  and reused across requests, so only the first request pays for the
  connection.
- **Secrets.** Keep the connection string in a Vercel environment variable,
  never in the repository. Rotate it from Atlas if it leaks.
- **No auth yet.** The API is unauthenticated — add your own auth layer
  (Vercel Passport, or a FastAPI dependency) before exposing real health data.

## 🗂️ Project Structure

```
smartmeds/
├── smartmeds/               # Main package
│   ├── __init__.py
│   ├── __main__.py          # Entry point
│   ├── core/                # Core business logic
│   │   ├── __init__.py
│   │   ├── medication.py    # Medication models
│   │   ├── scheduler.py     # Scheduling logic
│   │   └── interactions.py  # Drug interaction checker
│   ├── api/                 # HTTP API (FastAPI, deployed to Vercel)
│   │   ├── __init__.py
│   │   ├── app.py           # Application and routes
│   │   ├── dependencies.py  # Shared database dependency
│   │   └── schemas.py       # Request/response models
│   ├── db/                  # Database layer
│   │   ├── __init__.py
│   │   ├── base.py          # Backend interface (shared by all backends)
│   │   ├── database.py      # SQLite database handler
│   │   ├── mongo_database.py# MongoDB database handler (PyMongo)
│   │   ├── factory.py       # Backend factory (reads the configuration)
│   │   └── mappers.py       # Domain object <-> document conversion
│   ├── utils/               # Utility functions
│   │   ├── __init__.py
│   │   ├── config.py        # Environment-based configuration
│   │   ├── logger.py        # Logging setup
│   │   └── helpers.py       # Helper functions
│   └── cli/                 # CLI interface
│       ├── __init__.py
│       └── commands.py      # CLI commands
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_medication.py
│   ├── test_scheduler.py
│   ├── test_interactions.py
│   ├── test_database.py     # SQLite backend tests
│   ├── test_mongo_database.py # MongoDB backend tests
│   ├── test_api.py          # HTTP API tests
│   └── test_config.py       # Configuration and factory tests
├── app.py                   # Vercel entrypoint (FastAPI app)
├── vercel.json              # Vercel function configuration
├── .python-version          # Python version used on Vercel (3.12)
├── docs/                    # Documentation
├── .github/
│   └── workflows/
│       └── ci.yml           # GitHub Actions CI
├── .gitignore
├── requirements.txt
├── requirements-dev.txt
├── setup.py
├── pyproject.toml
└── README.md
```

## 🛠️ Development

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests (MongoDB tests use mongomock, no server required)
pytest tests/ -v

# Run linter
flake8 smartmeds/

# Format code
black smartmeds/
```

### Adding a new storage backend

1. Implement `DatabaseBackend` (`smartmeds/db/base.py`) in a new module, e.g.
   `smartmeds/db/redis_database.py`.
2. Register it in `create_database()` (`smartmeds/db/factory.py`).
3. Add it to `SUPPORTED_BACKENDS` in `smartmeds/utils/config.py`.

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
