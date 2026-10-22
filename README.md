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
│   ├── db/                  # Database layer
│   │   ├── __init__.py
│   │   └── database.py      # SQLite database handler
│   ├── utils/               # Utility functions
│   │   ├── __init__.py
│   │   ├── logger.py        # Logging setup
│   │   └── helpers.py       # Helper functions
│   └── cli/                 # CLI interface
│       ├── __init__.py
│       └── commands.py      # CLI commands
├── tests/                   # Test suite
│   ├── __init__.py
│   ├── test_medication.py
│   ├── test_scheduler.py
│   └── test_interactions.py
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

# Run tests
pytest tests/ -v

# Run linter
flake8 smartmeds/

# Format code
black smartmeds/
```

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.
