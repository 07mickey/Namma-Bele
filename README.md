# NAMMA BELE (ನಮ್ಮ ಬೆಳೆ)
## Agricultural Soil Testing & Operational Farm Management Network

An open-source, multi-contributor agricultural management platform uniting soil diagnostic laboratories, agricultural extension officers, field workers, and farmers into a single coordinated network.

---

## 1. Repository Structure

```text
Namma-Bele/
├── soil-testing-portal/    # Authoritative production application (Flask, SQLAlchemy, Pytest)
├── manya/                  # Farmer portal UI/UX prototype & design system
├── sidhan/                 # Architecture specifications, QA reports & prototypes
├── adapters/               # AI prompt adapters (Claude, Gemini, GPT-OSS)
├── scripts/                # Repository validation & management tooling
├── .agent/                 # Multi-wave GSD workflows
├── .agents/                # Custom agents and execution skills
├── .gemini/                # Gemini CLI workspace context
├── .gsd/                   # GSD planning templates and examples
├── GSD-STYLE.md            # Coding standards & style guidelines
├── PROJECT_RULES.md        # Architecture boundaries & contribution protocols
├── VERSION                 # Current release version
└── model_capabilities.yaml # Agent capability mapping
```

---

## 2. Component Overview

### `soil-testing-portal/`
The authoritative operational backend and application engine:
- **Core Technology:** Python 3.10+, Flask 3.x, SQLAlchemy ORM, SQLite.
- **Relational Data Engine:** 18 relational models supporting complete sample tracking, lab assays, farmer registration, expert consultations, and dispatch logistics.
- **REST Endpoints:** 60 fully tested API routes.
- **Role Workspaces:** Dedicated operational interfaces for Farmer, Field Worker, Laboratory Technician, Sample Collection Operator, Agricultural Advisor, and System Administrator.
- **Automated Verification:** 187 unit and integration tests passing (`pytest tests/`).

### `manya/`
Frontend prototype authored by Person 2:
- High-fidelity farmer web portal with complete UI design tokens and responsive layouts.
- Bilingual Kannada (`kn`) and English (`en`) interface localization.
- Automated screenshot and documentation generation pipeline.

### `sidhan/`
QA and architectural contribution by Person 3:
- Independent security audit reviews, integration handovers, and UI wireframes.

---

## 3. Quick Start & Verification

### Running the Operational Application
```bash
cd soil-testing-portal
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

### Running the Automated Test Suite
```bash
cd soil-testing-portal
pytest tests/
```

---

## 4. License
This project is open-source software licensed under the [MIT License](LICENSE).
