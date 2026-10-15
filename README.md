# 🤝 Saath — AI Agent for Post-Bereavement Financial Paperwork

> **साथ** (Saath) means "together" in Hindi.
> Saath helps Indian families navigate the financial paperwork after a death — step by step, in their language, at their pace.

---

> **⚠️ DEMO — All data is entirely synthetic. No real persons, accounts or institutions. No data is stored or transmitted.**

---

## Table of Contents
1. [What is Saath?](#what-is-saath)
2. [Setup](#setup)
3. [Architecture](#architecture)
4. [3-Minute Demo Script](#3-minute-demo-script)
5. [Project Structure](#project-structure)
6. [Running Tests](#running-tests)
7. [Live Mode (Gemini)](#live-mode-gemini)
8. [Items Needing Your Verification](#items-needing-your-verification)
9. [Hard Rules & Compliance](#hard-rules--compliance)

---

## What is Saath?

Saath is a **stateful workflow agent** (not a chatbot) that:

1. **Interviews** the family — extracts a structured case profile from free-text or voice input in English, Hindi or Marathi.
2. **Discovers possible hidden assets** — scans a bank statement CSV for recurring patterns that hint at insurance premiums, SIPs, employer salary / EPF, FD interest, and loan EMIs.
3. **Builds a personalised task plan** — dependency-aware task graph with Kanban view (Blocked / Ready / Done), sourced exclusively from knowledge-base procedure cards.
4. **Prepares draft claim kits** — editable `.docx` letters marked **DRAFT**, plus document checklists, per institution.
5. **Tracks deadlines** — follow-up draft letters and a downloadable `.ics` calendar file.

**Every finding, task and draft requires explicit human approval before appearing in the workflow. Saath never files, sends or decides anything.**

---

## Setup

### Prerequisites
- Python 3.11+
- pip

### Installation

```bash
# 1. Clone / navigate to the project
cd SAATH_DEMO

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy env file
cp .env.example .env
# Edit .env if needed (default is LLM_MODE=mock, no key required)

# 4. Generate synthetic bank statement
python3 sample_data/generate_statement.py

# 5. Run the app
streamlit run app.py
```

The app opens at **http://localhost:8501**.

---

## Architecture

```mermaid
flowchart TB
    subgraph UI["Streamlit UI (app.py)"]
        S1[Step 1: Tell us]
        S2[Step 2: Upload]
        S3[Step 3: Findings]
        S4[Step 4: Plan]
        S5[Step 5: Claim Kits]
        S6[Step 6: Tracker]
    end

    subgraph Agents["Agent Modules (agents/)"]
        A1[Interviewer\nExtract case profile]
        A2[AssetDiscovery\nParse statement]
        A3[Planner\nBuild task graph]
        A4[Drafter\nGenerate DRAFT letters]
        A5[Tracker\nReminders + .ics]
    end

    subgraph KB["Knowledge Base (procedures/)"]
        K1[death_certificate.yaml]
        K2[bank_account_claim.yaml]
        K3[life_insurance_claim.yaml]
        K4[epf_pension_claim.yaml]
        K5[mutual_fund_transmission.yaml]
        K6[shares_demat_transmission.yaml]
        K7[legal_heir_succession.yaml ⚠️]
        K8[unclaimed_deposit_search.yaml]
    end

    subgraph State["Persistence"]
        DB[(SQLite\ncase state)]
    end

    subgraph LLM["LLM Provider (llm_provider.py)"]
        LM[Mock mode\nfixtures] -- LLM_MODE=mock --> LLM
        LG[Gemini 2.0 Flash\nvia google-genai] -- LLM_MODE=live --> LLM
    end

    subgraph Utils["Utilities"]
        M[masking.py\nAadhaar / PAN / Phone / Account]
        KL[kb_loader.py\nYAML card loader]
        SS[state_store.py\nSQLite CRUD]
    end

    S1 --> A1 --> DB
    S2 --> A2 --> DB
    S3 --> A3 --> DB
    S4 --> A4 --> DB
    S5 --> A5 --> DB

    A1 -. uses .-> LLM
    A2 -. uses .-> M
    A3 -. reads .-> KB
    A4 -. reads .-> KB

    DB -. persists .-> State
```

### Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Stateful per-case SQLite** | Families need to resume across sessions |
| **Rules engine first, LLM second** | Deterministic asset detection; LLM only for interview parsing |
| **KB cards as sole procedure source** | Prevents invention of fees, deadlines, form numbers |
| **Mock mode default** | Full demo without any API key |
| **Masking before LLM** | Sensitive identifiers never reach the LLM |
| **`is_draft=True` / `sent=False` invariants** | Tested and enforced; Saath never files anything |

---

## 3-Minute Demo Script

### 1 — The Problem (45 seconds)
> "When someone dies in India, the family faces a maze of institutions — banks, insurers, EPFO, AMCs, SEBI. Each has different forms, deadlines and procedures. Most families don't know what they even have, let alone what to do first. At the worst possible time, they're drowning in paperwork."

### 2 — The Demo (90 seconds)
1. Open the app. Point out the **synthetic data banner** — "everything here is fictional."
2. Click **Load Sample Case** → a fictional widow describes her situation. Click **Analyse & continue**.
3. On Step 2, click **Scan for possible assets** — Saath analyses 163 bank rows in seconds and surfaces 3 **possible** assets: an insurance premium, a SIP, and employer salary credits (with the EPF implication).
4. Point out the confidence badges and the **"could not tell"** section — "Saath is honest about what it doesn't know."
5. Approve the findings → click **Build My Plan**. The Kanban shows 6 tasks with dependencies. Priority 1 is death certificate.
6. Click **Generate Claim Kits**. Show the DRAFT letter with the red banner. Download the `.docx`.
7. Click **Set up Tracker**. Download the `.ics` calendar file.

### 3 — Human Approval Step (30 seconds)
> "At every step Saath asks for explicit approval. It never sends a letter, never files a claim, never states anything as definite. It says 'possible', 'likely', 'verify with the institution'. Legal and succession questions are flagged as 'needs a lawyer.'"

### 4 — Impact (15 seconds)
> "Millions of Indian families face this every year. Saath turns weeks of confusion into a guided, step-by-step process — in their own language, on their phone."

---

## Project Structure

```
SAATH_DEMO/
├── app.py                    # Streamlit UI — 6-step flow
├── models.py                 # Pydantic models for all data structures
├── llm_provider.py           # LLM interface (mock | live Gemini)
├── requirements.txt
├── .env.example              # Template — copy to .env
├── .gitignore
│
├── agents/
│   ├── interviewer.py        # Extract case profile from free text
│   ├── asset_discovery.py    # Rules + LLM bank statement analysis
│   ├── planner.py            # Dependency-aware task graph builder
│   ├── drafter.py            # DRAFT .docx letters + checklists
│   └── tracker.py            # Reminders + .ics calendar export
│
├── procedures/               # Knowledge-base YAML cards (8 topics)
│   ├── death_certificate.yaml
│   ├── bank_account_claim.yaml
│   ├── life_insurance_claim.yaml
│   ├── epf_pension_claim.yaml
│   ├── mutual_fund_transmission.yaml
│   ├── shares_demat_transmission.yaml
│   ├── legal_heir_succession_certificate.yaml
│   └── unclaimed_deposit_search.yaml
│
├── sample_data/
│   ├── generate_statement.py # Generates synthetic 163-row CSV
│   ├── sharma_bank_statement.csv  # Fictional bank statement
│   ├── family_profile.json   # Fictional Sharma family
│   └── case_description.txt  # Sample free-text input
│
├── utils/
│   ├── masking.py            # Aadhaar / PAN / Phone / Account masking
│   ├── kb_loader.py          # YAML card loader
│   └── state_store.py        # SQLite persistence
│
├── tests/
│   ├── test_asset_discovery.py  # 3 planted assets found, decoys safe
│   ├── test_masking.py          # Masking unit tests
│   └── test_drafter.py          # is_draft=True, sent=False invariants
│
└── output/                   # Generated .docx and .ics files (gitignored)
```

---

## Running Tests

```bash
python3 -m pytest tests/ -v
```

All 30 tests should pass. Key assertions:
- ✅ All 3 planted assets detected (insurance, SIP, salary)
- ✅ All 4 decoy types correctly excluded from findings
- ✅ No finding label uses "definitely", "confirmed", "entitled"
- ✅ `is_draft = True` always (invariant)
- ✅ `sent = False` always (invariant — Saath never sends)
- ✅ Masking removes Aadhaar prefix, PAN prefix, phone middle digits, account prefix

---

## Live Mode (Gemini)

When you are ready to test with a real LLM:

1. Get your key from https://aistudio.google.com/
2. Edit `.env`:
   ```env
   LLM_MODE=live
   GEMINI_API_KEY=your_actual_key_here
   ```
3. Restart the app: `streamlit run app.py`

In live mode, the Interviewer agent calls **Gemini 2.0 Flash** with structured JSON output. All other agents use rule-based logic and are unaffected.

**Never commit `.env` to git.** It is in `.gitignore`.

---

## Items Needing Your Verification

The following 8 knowledge-base cards are marked `verified: false` and need manual review before production use. Each is in `procedures/`.

| Card | Source URL | What to verify |
|------|-----------|----------------|
| `death_certificate.yaml` | https://crsorgi.gov.in/ | State-wise forms, fees, timeline |
| `bank_account_claim.yaml` | https://www.rbi.org.in/ | Current threshold for simplified settlement without succession certificate |
| `life_insurance_claim.yaml` | https://www.irdai.gov.in/ | Current settlement timeline mandate under IRDAI regulation |
| `epf_pension_claim.yaml` | https://www.epfindia.gov.in/ | Current form numbers (Form 20, 10-D) — may have changed |
| `mutual_fund_transmission.yaml` | https://www.amfiindia.com/ | Current TRF formats per major AMC/RTA |
| `shares_demat_transmission.yaml` | https://www.sebi.gov.in/ | Current thresholds for no-succession-certificate route |
| `legal_heir_succession_certificate.yaml` | TODO | Source URL needed; state-wise variation is significant |
| `unclaimed_deposit_search.yaml` | https://udgam.rbi.org.in/ | Which banks are currently live on UDGAM |

> None of the cards contain invented fees, deadlines or form numbers — those fields are left `null`. All steps use general language such as "verify at the branch."

---

## Hard Rules Compliance

| Rule | Implementation |
|------|---------------|
| Synthetic data only | `sample_data/` — fictional family/institutions; demo banner always shown |
| Masking | `utils/masking.py` — applied before display and before any LLM call |
| Human approval | Every finding, task and kit has `ApprovalStatus.PENDING` default; explicit approve/reject buttons |
| No filing/sending | `is_draft=True` and `sent=False` are invariants tested by `test_drafter.py` |
| Hedged language | All labels use "possible", "likely", "may"; tested in `test_no_finding_claims_certainty` |
| Legal questions flagged | `legal_flag: true` in KB card; UI shows ⚠️ with lawyer advisory |
| Procedures from KB only | Planner reads `procedures/*.yaml`; no inline procedure text |
| Source + verified badge | Every task shows source card title, URL, and ✅/⚠️ verified badge |
| No API key in code | Key only in `.env`; `.gitignore` excludes it |
