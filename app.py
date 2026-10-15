"""
app.py — Saath: AI agent for post-bereavement financial paperwork.
Streamlit UI with 6-step flow, agent timeline, masking, human approval.

⚠ DEMO USES SYNTHETIC DATA ONLY — no real persons, no real institutions.
"""
from __future__ import annotations

import io
import logging
import os
import uuid
from datetime import date
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ── Logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── Page config ────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Saath — Financial Paperwork After a Loss",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Imports (after path setup) ─────────────────────────────────────────
from models import (
    CaseState, Language, ApprovalStatus, TaskStatus, TaskPlan
)
from agents.interviewer import run_interviewer
from agents.asset_discovery import run_asset_discovery
from agents.planner import run_planner
from agents.drafter import run_drafter
from agents.tracker import run_tracker
from utils.state_store import save_case, load_case
from utils.masking import mask_all

# ── CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
}

/* ── Demo banner ── */
.demo-banner {
    background: linear-gradient(90deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    color: #e2b96f;
    text-align: center;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.5px;
    border-bottom: 2px solid #e2b96f;
    margin-bottom: 0;
}

/* ── App header ── */
.app-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 16px;
    padding: 32px 40px;
    color: white;
    margin-bottom: 24px;
}
.app-header h1 { margin: 0 0 8px 0; font-size: 2.2rem; font-weight: 700; }
.app-header p  { margin: 0; opacity: 0.85; font-size: 1.05rem; }

/* ── Step cards ── */
.step-card {
    background: white;
    border-radius: 14px;
    padding: 24px;
    box-shadow: 0 2px 20px rgba(0,0,0,0.07);
    border-left: 5px solid #667eea;
    margin-bottom: 20px;
}

/* ── Metric cards ── */
.metric-row {
    display: flex;
    gap: 16px;
    flex-wrap: wrap;
    margin-bottom: 24px;
}
.metric-card {
    flex: 1;
    min-width: 130px;
    background: linear-gradient(135deg, #667eea22, #764ba211);
    border: 1px solid #667eea44;
    border-radius: 12px;
    padding: 16px;
    text-align: center;
}
.metric-card .value {
    font-size: 2rem;
    font-weight: 700;
    color: #667eea;
}
.metric-card .label {
    font-size: 0.8rem;
    color: #666;
    margin-top: 4px;
}

/* ── Finding cards ── */
.finding-card {
    background: #f8f9ff;
    border-radius: 12px;
    padding: 18px;
    border: 1px solid #e0e4f8;
    margin-bottom: 14px;
}
.finding-high   { border-left: 4px solid #10b981; }
.finding-medium { border-left: 4px solid #f59e0b; }
.finding-low    { border-left: 4px solid #ef4444; }
.confidence-badge {
    display: inline-block;
    padding: 2px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.badge-high   { background:#d1fae5; color:#065f46; }
.badge-medium { background:#fef3c7; color:#92400e; }
.badge-low    { background:#fee2e2; color:#991b1b; }

/* ── Legal warning ── */
.legal-warning {
    background: #fff3cd;
    border: 1px solid #ffc107;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 10px 0;
}

/* ── Draft letter box ── */
.draft-box {
    background: #1e1e2e;
    color: #cdd6f4;
    border-radius: 10px;
    padding: 16px;
    font-family: 'Courier New', monospace;
    font-size: 12.5px;
    line-height: 1.6;
    max-height: 320px;
    overflow-y: auto;
    white-space: pre-wrap;
}

/* ── Kanban columns ── */
.kanban-col {
    background: #f3f4f6;
    border-radius: 12px;
    padding: 16px;
    min-height: 120px;
}
.kanban-title {
    font-weight: 700;
    font-size: 0.85rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 12px;
}
.task-card {
    background: white;
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 8px;
    box-shadow: 0 1px 6px rgba(0,0,0,0.07);
    font-size: 13px;
}

/* ── Timeline ── */
.timeline-item {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    padding: 8px 0;
    border-bottom: 1px solid #f0f0f0;
}
.timeline-dot {
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-top: 4px;
    flex-shrink: 0;
}
.dot-done    { background: #10b981; }
.dot-running { background: #667eea; animation: pulse 1.5s infinite; }
.dot-waiting { background: #d1d5db; }

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.4; }
}

/* ── Sidebar ── */
.sidebar-section {
    background: #f8f9ff;
    border-radius: 10px;
    padding: 12px;
    margin-bottom: 12px;
}

/* ── Step progress ── */
.step-progress {
    display: flex;
    gap: 6px;
    margin-bottom: 24px;
    align-items: center;
}
.step-pip {
    width: 32px;
    height: 6px;
    border-radius: 3px;
}
.pip-done    { background: #10b981; }
.pip-active  { background: #667eea; }
.pip-pending { background: #e5e7eb; }

/* Scrollable evidence table */
.evidence-table {
    max-height: 200px;
    overflow-y: auto;
    font-size: 12px;
}
</style>
""", unsafe_allow_html=True)

# ── Demo banner ────────────────────────────────────────────────────────
st.markdown(
    '<div class="demo-banner">🔒 DEMO — All data is entirely synthetic. '
    'No real persons, accounts or institutions. No data is stored or transmitted.</div>',
    unsafe_allow_html=True,
)


# ══════════════════════════════════════════════════════════════════════
# Session state initialisation
# ══════════════════════════════════════════════════════════════════════

def init_session():
    if "case" not in st.session_state:
        st.session_state.case = CaseState(
            case_id=str(uuid.uuid4())[:8],
        )
    if "agent_log" not in st.session_state:
        st.session_state.agent_log = []  # list of (agent_name, status, message)
    if "timer_start" not in st.session_state:
        import time
        st.session_state.timer_start = time.time()


def log_agent(name: str, status: str, msg: str = ""):
    st.session_state.agent_log.append((name, status, msg))


init_session()
case: CaseState = st.session_state.case


# ══════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🤝 Saath")
    st.markdown("*साथ — Together through paperwork*")
    st.divider()

    # Agent Timeline
    st.markdown("### ⏱ Agent Timeline")
    AGENTS = [
        ("💬 Interviewer",     1),
        ("🔍 Asset Discovery", 2),
        ("📋 Planner",         3),
        ("✍️  Drafter",         4),
        ("🔔 Tracker",         5),
    ]
    for agent_label, step_num in AGENTS:
        if case.active_step > step_num:
            dot_cls = "dot-done"
            status_txt = "✅ Done"
        elif case.active_step == step_num:
            dot_cls = "dot-running"
            status_txt = "🔄 Running"
        else:
            dot_cls = "dot-waiting"
            status_txt = "⏳ Waiting"
        st.markdown(
            f'<div class="timeline-item">'
            f'<div class="timeline-dot {dot_cls}"></div>'
            f'<div><b>{agent_label}</b><br><small style="color:#888">{status_txt}</small></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Metrics panel
    st.markdown("### 📊 Metrics")
    n_assets = len(case.discovery.findings) if case.discovery else 0
    n_approved = sum(
        1 for f in (case.discovery.findings if case.discovery else [])
        if f.approval_status == ApprovalStatus.APPROVED
    )
    n_tasks = len(case.plan.tasks) if case.plan else 0
    n_kits = len(case.claim_kits)

    import time
    elapsed = int(time.time() - st.session_state.timer_start)
    elapsed_str = f"{elapsed//60}m {elapsed%60}s"

    for label, val in [
        ("Assets surfaced", n_assets),
        ("Assets approved", n_approved),
        ("Tasks planned", n_tasks),
        ("Claim kits", n_kits),
        ("Session time", elapsed_str),
    ]:
        st.markdown(
            f'<div style="display:flex;justify-content:space-between;padding:4px 0;'
            f'border-bottom:1px solid #eee;font-size:13px">'
            f'<span style="color:#666">{label}</span>'
            f'<span style="font-weight:600;color:#667eea">{val}</span></div>',
            unsafe_allow_html=True,
        )

    st.divider()

    # Load demo data button
    st.markdown("### 🗂 Demo Shortcuts")
    if st.button("📂 Load Sample Case", use_container_width=True):
        sample_txt = Path("sample_data/case_description.txt").read_text()
        st.session_state["prefill_text"] = sample_txt
        st.rerun()

    if st.button("🔄 Start Fresh", use_container_width=True, type="secondary"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    st.divider()
    llm_mode = os.environ.get("LLM_MODE", "mock").upper()
    st.markdown(
        f'<div style="font-size:11px;color:#999;text-align:center">'
        f'LLM mode: <b style="color:#667eea">{llm_mode}</b><br>'
        f'Case ID: <code>{case.case_id}</code></div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════

st.markdown(
    '<div class="app-header">'
    '<h1>🤝 Saath</h1>'
    '<p>AI-guided financial paperwork support after a bereavement — '
    'step by step, in your language, at your pace.</p>'
    '</div>',
    unsafe_allow_html=True,
)

# Step progress bar
step_labels = ["Tell us", "Upload", "What we found", "Your plan", "Claim kits", "Tracker"]
progress_html = '<div class="step-progress">'
for i, label in enumerate(step_labels, 1):
    if i < case.active_step:
        cls = "pip-done"
    elif i == case.active_step:
        cls = "pip-active"
    else:
        cls = "pip-pending"
    progress_html += f'<div class="step-pip {cls}" title="Step {i}: {label}"></div>'
progress_html += (
    f'<span style="font-size:12px;color:#888;margin-left:8px">'
    f'Step {case.active_step} of 6: <b>{step_labels[case.active_step-1]}</b></span>'
)
progress_html += '</div>'
st.markdown(progress_html, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════
# STEP 1 — Tell Us
# ══════════════════════════════════════════════════════════════════════

if case.active_step == 1:
    st.markdown("## Step 1: Tell us what happened")
    st.markdown(
        "_Please describe the situation in your own words — who passed away, "
        "when, which state you are in, and any financial institutions you are aware of. "
        "You do not need to be complete; Saath will ask follow-up questions._"
    )

    col1, col2 = st.columns([3, 1])
    with col2:
        lang_choice = st.selectbox(
            "Output language",
            options=[l.value for l in Language],
            index=0,
        )
        language = Language(lang_choice)
        case.language = language

    with col1:
        prefill = st.session_state.pop("prefill_text", "")
        raw_text = st.text_area(
            "Describe the situation",
            value=prefill,
            height=240,
            placeholder="Example: My father passed away on 10th September in Mumbai. "
                         "He had a savings account at Demo Bank and a life insurance policy...",
            label_visibility="collapsed",
        )

    if st.button("▶  Analyse & continue", type="primary", use_container_width=True):
        if len(raw_text.strip()) < 30:
            st.error("Please provide a bit more detail (at least a sentence or two).")
        else:
            with st.spinner("Interviewer agent is extracting the case profile…"):
                try:
                    profile = run_interviewer(raw_text, language)
                    case.profile = profile
                    case.active_step = 2
                    save_case(case)
                    log_agent("Interviewer", "done", f"Profile extracted for {profile.deceased_name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Interviewer error: {e}")
                    logger.exception("Interviewer failed")

    # If profile exists (back navigation), show it
    if case.profile:
        with st.expander("📋 Extracted profile (click to review)"):
            p = case.profile
            st.json({
                "Deceased": p.deceased_name,
                "Date of death": p.date_of_death,
                "State": p.state,
                "Claimant": f"{p.claimant_name} ({p.claimant_relationship})",
                "Known institutions": p.known_institutions,
                "Nominee known": p.nominee_known,
                "Will present": p.will_present,
            })


# ══════════════════════════════════════════════════════════════════════
# STEP 2 — Upload
# ══════════════════════════════════════════════════════════════════════

elif case.active_step == 2:
    st.markdown("## Step 2: Upload a bank statement")

    if case.profile:
        p = case.profile
        st.success(
            f"✅ Profile saved — **{p.deceased_name}**, {p.claimant_relationship} claimant: "
            f"**{p.claimant_name}**, state: **{p.state}**"
        )

        # Follow-up questions
        if p.follow_up_questions:
            with st.expander("💬 A few follow-up questions (answer if you can, then upload)"):
                for q in p.follow_up_questions:
                    st.markdown(f"- {q}")

    st.markdown(
        "Upload the deceased's bank statement as a **CSV file**. "
        "Saath will scan for recurring transactions that may indicate "
        "insurance premiums, SIPs, or employer credits. "
        "_Identifiers are masked before any analysis._"
    )

    use_demo = st.checkbox("Use the sample statement (Demo)", value=True)

    if use_demo:
        st.info("📄 Using synthetic sample statement: `sample_data/sharma_bank_statement.csv`")
        file_source = "sample_data/sharma_bank_statement.csv"
        can_proceed = True
    else:
        uploaded = st.file_uploader(
            "Upload CSV bank statement",
            type=["csv"],
            help="CSV must have columns: Date, Description, Amount, CR/DR",
        )
        file_source = uploaded
        can_proceed = uploaded is not None

    if can_proceed and st.button("🔍 Scan for possible assets", type="primary", use_container_width=True):
        with st.spinner("Asset Discovery agent is scanning the statement…"):
            try:
                discovery = run_asset_discovery(file_source, case.case_id)
                case.discovery = discovery
                case.active_step = 3
                save_case(case)
                log_agent("Asset Discovery", "done", f"{len(discovery.findings)} findings")
                st.rerun()
            except Exception as e:
                st.error(f"Asset discovery error: {e}")
                logger.exception("Asset discovery failed")

    if st.button("← Back", key="back_2"):
        case.active_step = 1
        st.rerun()


# ══════════════════════════════════════════════════════════════════════
# STEP 3 — What We Found
# ══════════════════════════════════════════════════════════════════════

elif case.active_step == 3:
    st.markdown("## Step 3: What we found — please review each item")
    st.markdown(
        "_Saath has identified **possible** assets from the bank statement. "
        "Please **Approve** findings that seem correct and **Reject** those that "
        "do not apply. Only approved items will appear in your plan and claim kits. "
        "None of these are confirmed — verify with the relevant institution._"
    )

    if not case.discovery or not case.discovery.findings:
        st.warning("No findings yet. Please go back and upload a statement.")
    else:
        d = case.discovery
        st.caption(f"Analysed **{d.rows_analysed}** transactions · "
                   f"Found **{len(d.findings)}** possible assets")

        for idx, finding in enumerate(d.findings):
            conf = finding.confidence.value
            conf_css = f"badge-{conf}"
            card_css = f"finding-{conf}"

            with st.container():
                st.markdown(
                    f'<div class="finding-card {card_css}">',
                    unsafe_allow_html=True,
                )

                col_info, col_actions = st.columns([3, 1])
                with col_info:
                    st.markdown(
                        f'**{finding.label}** &nbsp; '
                        f'<span class="confidence-badge {conf_css}">{conf} confidence</span>',
                        unsafe_allow_html=True,
                    )
                    if finding.monthly_amount:
                        st.markdown(
                            f"💰 Estimated: **₹{finding.monthly_amount:,.0f}/month** "
                            f"(≈ ₹{finding.annual_amount:,.0f}/year)"
                        )
                    st.markdown(f"🔎 *Verify via:* {finding.confirm_via}")

                    with st.expander("📄 Evidence rows"):
                        for ev in finding.evidence_rows[:6]:
                            st.markdown(
                                f"`{ev.date}` | {ev.description} | "
                                f"**₹{ev.amount:,.2f}** {ev.credit_debit}",
                            )
                        if len(finding.evidence_rows) > 6:
                            st.caption(f"…and {len(finding.evidence_rows)-6} more rows")

                with col_actions:
                    status = finding.approval_status
                    if status == ApprovalStatus.APPROVED:
                        st.success("✅ Approved")
                    elif status == ApprovalStatus.REJECTED:
                        st.error("❌ Rejected")
                    else:
                        st.markdown("**Awaiting review**")

                    col_a, col_r = st.columns(2)
                    with col_a:
                        if st.button(
                            "✅", key=f"approve_{idx}",
                            help="Approve this finding",
                            use_container_width=True
                        ):
                            case.discovery.findings[idx].approval_status = ApprovalStatus.APPROVED
                            save_case(case)
                            st.rerun()
                    with col_r:
                        if st.button(
                            "❌", key=f"reject_{idx}",
                            help="Reject this finding",
                            use_container_width=True
                        ):
                            case.discovery.findings[idx].approval_status = ApprovalStatus.REJECTED
                            save_case(case)
                            st.rerun()

                st.markdown("</div>", unsafe_allow_html=True)

        # Could not tell section
        st.markdown("### ❓ What Saath could not tell from the statement")
        for note in d.could_not_tell:
            st.markdown(f"- {note}")

        st.divider()
        n_pending = sum(
            1 for f in d.findings if f.approval_status == ApprovalStatus.PENDING
        )
        if n_pending > 0:
            st.info(f"ℹ️  {n_pending} item(s) still pending review. "
                    "You can proceed — pending items will be included in the plan for now.")

        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Back", use_container_width=True):
                case.active_step = 2
                st.rerun()
        with col_next:
            if st.button("📋 Build My Plan →", type="primary", use_container_width=True):
                with st.spinner("Planner agent is building your task graph…"):
                    try:
                        plan = run_planner(case.profile, case.discovery)
                        case.plan = plan
                        case.active_step = 4
                        save_case(case)
                        log_agent("Planner", "done", f"{len(plan.tasks)} tasks")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Planner error: {e}")
                        logger.exception("Planner failed")


# ══════════════════════════════════════════════════════════════════════
# STEP 4 — Your Plan (Kanban + Dependency view)
# ══════════════════════════════════════════════════════════════════════

elif case.active_step == 4:
    st.markdown("## Step 4: Your personalised task plan")
    st.markdown(
        "_Each task below comes from a verified procedure card. "
        "Tasks marked ⚠️ involve legal or inheritance questions — "
        "please consult a lawyer. Approve tasks to include them in your claim kits._"
    )

    if not case.plan or not case.plan.tasks:
        st.warning("No plan yet. Please go back.")
    else:
        plan = case.plan
        tasks = plan.tasks

        # Tabs: Kanban | All tasks | Dependencies
        tab1, tab2, tab3 = st.tabs(["🗂 Kanban", "📋 All Tasks", "🔗 Dependencies"])

        with tab1:
            # Kanban view
            k_blocked = [t for t in tasks if t.status == TaskStatus.BLOCKED]
            k_ready   = [t for t in tasks if t.status in (TaskStatus.READY, TaskStatus.APPROVED)]
            k_done    = [t for t in tasks if t.status == TaskStatus.DONE]

            c1, c2, c3 = st.columns(3)
            for col, task_list, title, color in [
                (c1, k_blocked, "⛔ Blocked",  "#ef4444"),
                (c2, k_ready,   "✅ Ready",     "#10b981"),
                (c3, k_done,    "🏁 Done",      "#667eea"),
            ]:
                with col:
                    st.markdown(
                        f'<div style="background:#f3f4f6;border-radius:12px;padding:16px;">'
                        f'<div style="font-weight:700;font-size:0.85rem;color:{color};'
                        f'text-transform:uppercase;letter-spacing:1px;margin-bottom:12px">'
                        f'{title} ({len(task_list)})</div>',
                        unsafe_allow_html=True,
                    )
                    for t in task_list:
                        st.markdown(
                            f'<div class="task-card">'
                            f'<b style="font-size:13px">{t.title}</b><br>'
                            f'<small style="color:#888">{t.institution}</small>'
                            f'{"<br><small style=color:#f59e0b>🏛 Legal check needed</small>" if "lawyer" in t.description.lower() else ""}'
                            f'</div>',
                            unsafe_allow_html=True,
                        )
                    st.markdown("</div>", unsafe_allow_html=True)

        with tab2:
            # All tasks with approve/reject
            sorted_tasks = sorted(tasks, key=lambda t: t.priority)
            for idx, task in enumerate(sorted_tasks):
                is_legal = "lawyer" in task.description.lower() or "legal" in task.title.lower()

                with st.expander(
                    f"{'⚠️ ' if is_legal else ''}Priority {task.priority} — {task.title}"
                        + (f" 🔒 [Approved]" if task.approval_status == ApprovalStatus.APPROVED else ""),
                    expanded=(idx == 0),
                ):
                    if is_legal:
                        st.warning(
                            "⚠️ **Needs a lawyer or legal-aid check** — "
                            "this step involves inheritance or succession rights. "
                            "Saath cannot advise on legal matters."
                        )

                    st.markdown(task.description)

                    if task.source:
                        verified_badge = "✅ Verified" if task.source.verified else "⚠️ Unverified"
                        st.markdown(
                            f"📚 **Source:** {task.source.title} — "
                            f"{verified_badge} · [View source]({task.source.source_url})"
                        )

                    if task.deadline_date:
                        st.markdown(f"📅 **Target date:** {task.deadline_date}")

                    if task.depends_on:
                        st.markdown(f"🔗 **Depends on:** {', '.join(task.depends_on)}")

                    if task.required_documents:
                        st.markdown("**Documents needed:**")
                        for doc in task.required_documents:
                            st.markdown(f"  - {doc}")

                    col_a, col_r, col_d = st.columns(3)
                    with col_a:
                        if st.button(
                            "✅ Approve task",
                            key=f"tapprove_{idx}",
                            use_container_width=True,
                            type="primary",
                        ):
                            task_obj = case.plan.tasks[
                                next(i for i, t in enumerate(case.plan.tasks) if t.task_id == task.task_id)
                            ]
                            task_obj.approval_status = ApprovalStatus.APPROVED
                            task_obj.status = TaskStatus.APPROVED
                            save_case(case)
                            st.rerun()
                    with col_r:
                        if st.button(
                            "❌ Reject task",
                            key=f"treject_{idx}",
                            use_container_width=True,
                        ):
                            task_obj = case.plan.tasks[
                                next(i for i, t in enumerate(case.plan.tasks) if t.task_id == task.task_id)
                            ]
                            task_obj.approval_status = ApprovalStatus.REJECTED
                            task_obj.status = TaskStatus.BLOCKED
                            save_case(case)
                            st.rerun()
                    with col_d:
                        if st.button(
                            "🏁 Mark Done",
                            key=f"tdone_{idx}",
                            use_container_width=True,
                        ):
                            task_obj = case.plan.tasks[
                                next(i for i, t in enumerate(case.plan.tasks) if t.task_id == task.task_id)
                            ]
                            task_obj.status = TaskStatus.DONE
                            save_case(case)
                            st.rerun()

        with tab3:
            st.markdown("**Task dependency graph** (text view — first-48-hours tasks first)")
            for task in sorted_tasks:
                prefix = "↳" if task.depends_on else "◉"
                deps_str = (
                    " ← depends on: " + ", ".join(task.depends_on)
                    if task.depends_on else ""
                )
                st.markdown(
                    f"`{prefix}` **{task.task_id}** {task.title}{deps_str}"
                )

        st.divider()
        col_back, col_next = st.columns(2)
        with col_back:
            if st.button("← Back", use_container_width=True):
                case.active_step = 3
                st.rerun()
        with col_next:
            if st.button("✍️  Generate Claim Kits →", type="primary", use_container_width=True):
                with st.spinner("Drafter agent is preparing claim letters…"):
                    try:
                        approved_tasks = [
                            t for t in case.plan.tasks
                            if t.approval_status in (ApprovalStatus.APPROVED, ApprovalStatus.PENDING)
                        ]
                        kits = run_drafter(case.profile, approved_tasks)
                        case.claim_kits = kits
                        case.active_step = 5
                        save_case(case)
                        log_agent("Drafter", "done", f"{len(kits)} kits")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Drafter error: {e}")
                        logger.exception("Drafter failed")


# ══════════════════════════════════════════════════════════════════════
# STEP 5 — Claim Kits
# ══════════════════════════════════════════════════════════════════════

elif case.active_step == 5:
    st.markdown("## Step 5: Claim kits — review before use")
    st.markdown(
        "🔴 **These are DRAFT letters only. Review and edit every detail before "
        "submitting to any institution. Saath does not send or file anything on your behalf.**"
    )

    if not case.claim_kits:
        st.warning("No claim kits generated. Please go back and approve tasks.")
    else:
        for idx, kit in enumerate(case.claim_kits):
            approved_badge = "✅ Approved" if kit.approval_status == ApprovalStatus.APPROVED else ""
            with st.expander(
                f"📁 {kit.institution}  {approved_badge}",
                expanded=(idx == 0),
            ):
                assert not kit.sent, "Invariant violated: kit.sent must always be False"

                col_l, col_r = st.columns([3, 2])
                with col_l:
                    st.markdown("**📝 Draft Letter**")
                    st.markdown(
                        f'<div class="draft-box">{kit.letter_text}</div>',
                        unsafe_allow_html=True,
                    )
                    # Download .docx
                    docx_path = os.path.join("output", kit.letter_filename)
                    if os.path.exists(docx_path):
                        with open(docx_path, "rb") as f:
                            st.download_button(
                                label="📥 Download .docx",
                                data=f.read(),
                                file_name=kit.letter_filename,
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                key=f"dl_docx_{idx}",
                            )

                with col_r:
                    st.markdown("**📋 Document Checklist**")
                    for doc in kit.checklist.items:
                        st.checkbox(doc, key=f"doc_{idx}_{doc[:20]}")
                    if kit.checklist.optional_items:
                        st.markdown("*Optional:*")
                        for doc in kit.checklist.optional_items:
                            st.checkbox(f"(Optional) {doc}", key=f"optdoc_{idx}_{doc[:20]}")

                    st.divider()
                    col_a, col_r2 = st.columns(2)
                    with col_a:
                        if st.button("✅ Approve kit", key=f"kapprove_{idx}", type="primary", use_container_width=True):
                            case.claim_kits[idx].approval_status = ApprovalStatus.APPROVED
                            save_case(case)
                            st.rerun()
                    with col_r2:
                        if st.button("❌ Reject kit", key=f"kreject_{idx}", use_container_width=True):
                            case.claim_kits[idx].approval_status = ApprovalStatus.REJECTED
                            save_case(case)
                            st.rerun()

    st.divider()
    col_back, col_next = st.columns(2)
    with col_back:
        if st.button("← Back", use_container_width=True):
            case.active_step = 4
            st.rerun()
    with col_next:
        if st.button("🔔 Set up Tracker & Reminders →", type="primary", use_container_width=True):
            with st.spinner("Tracker agent is setting up reminders…"):
                try:
                    tracker = run_tracker(case.plan, case.profile)
                    case.tracker = tracker
                    case.active_step = 6
                    save_case(case)
                    log_agent("Tracker", "done", f"{len(tracker.reminders)} reminders")
                    st.rerun()
                except Exception as e:
                    st.error(f"Tracker error: {e}")
                    logger.exception("Tracker failed")


# ══════════════════════════════════════════════════════════════════════
# STEP 6 — Tracker
# ══════════════════════════════════════════════════════════════════════

elif case.active_step == 6:
    st.markdown("## Step 6: Deadlines & follow-ups")
    st.markdown(
        "Below are suggested follow-up dates and draft reminder letters. "
        "Download the calendar file to add deadlines to your calendar. "
        "**Saath does not send or schedule anything — all action is yours to take.**"
    )

    if not case.tracker:
        st.warning("No tracker data. Please go back.")
    else:
        tracker = case.tracker

        # ICS download
        if tracker.ics_filename:
            ics_path = os.path.join("output", tracker.ics_filename)
            if os.path.exists(ics_path):
                with open(ics_path, "rb") as f:
                    st.download_button(
                        label="📅 Download Calendar (.ics)",
                        data=f.read(),
                        file_name=tracker.ics_filename,
                        mime="text/calendar",
                        type="primary",
                    )

        st.divider()
        for rem in tracker.reminders:
            with st.expander(f"🔔 {rem.title} — due: {rem.due_date}"):
                st.markdown(f"**Task ID:** `{rem.task_id}`")
                st.markdown(f"**Suggested follow-up date:** {rem.due_date}")
                st.markdown("**Draft follow-up letter:**")
                st.markdown(
                    f'<div class="draft-box">{rem.follow_up_draft}</div>',
                    unsafe_allow_html=True,
                )
                # Download this follow-up as txt
                st.download_button(
                    label="📥 Download follow-up draft",
                    data=rem.follow_up_draft.encode(),
                    file_name=f"followup_{rem.reminder_id}.txt",
                    mime="text/plain",
                    key=f"dl_fu_{rem.reminder_id}",
                )

        st.divider()
        st.success(
            "🎉 **All steps complete!** Saath has prepared your findings, plan, "
            "claim kits and reminders. Remember:\n\n"
            "- ✅ Review every document before sending\n"
            "- ⚠️ Legal / succession questions need a lawyer\n"
            "- 🔍 Verify all procedure details with the relevant institution\n"
            "- 📞 Follow up regularly using the draft letters above"
        )

        if st.button("← Back to Claim Kits", use_container_width=True):
            case.active_step = 5
            st.rerun()
