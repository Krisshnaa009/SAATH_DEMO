"""
agents/tracker.py — Reminders, follow-up drafts, and .ics calendar export.
Saath NEVER sends anything. All output is for review only.
"""
from __future__ import annotations
import logging
import os
import uuid
from datetime import date, datetime, timedelta, timezone

from icalendar import Calendar, Event

from models import TaskItem, TaskPlan, Reminder, TrackerState, CaseProfile

logger = logging.getLogger(__name__)

OUTPUT_DIR = "output"


def _ensure_output_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def _follow_up_draft(task: TaskItem, profile: CaseProfile) -> str:
    """Generate a follow-up letter draft for a task."""
    return f"""[DRAFT FOLLOW-UP LETTER — REVIEW BEFORE USE — DO NOT SEND AS-IS]

Date: [Today's Date]

To,
The Manager / Claims Department
{task.institution}
[Branch Address — Please fill in]

Subject: Follow-up on claim / application for late {profile.deceased_name}
         Reference: [Claim Reference Number — fill in]

Dear Sir / Madam,

I, {profile.claimant_name}, {profile.claimant_relationship} of the late
{profile.deceased_name}, previously submitted documents for the above claim
on [Date of Submission — fill in].

I am writing to follow up on the status of this application. Could you
kindly advise on:
  1. The current status of the claim / application.
  2. Any additional documents or steps required from my side.
  3. The expected timeline for resolution.

I can be reached at [Phone — fill in] or [Email — fill in].

Thank you for your assistance.

Yours sincerely,
{profile.claimant_name}
[Signature]
[Date]
"""


def _build_ics(reminders: list[Reminder], filename: str) -> str:
    """Write reminders to an .ics calendar file and return the path."""
    _ensure_output_dir()
    path = os.path.join(OUTPUT_DIR, filename)

    cal = Calendar()
    cal.add("prodid", "-//Saath Demo//saath.demo//EN")
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "Saath Claim Deadlines (Demo)")

    for rem in reminders:
        event = Event()
        event.add("summary", f"[Saath] {rem.title}")
        try:
            due = date.fromisoformat(rem.due_date)
        except ValueError:
            due = date.today() + timedelta(days=30)
        event.add("dtstart", due)
        event.add("dtend", due + timedelta(days=1))
        event.add(
            "description",
            f"Task ID: {rem.task_id}\n"
            f"Suggested follow-up date: {(due - timedelta(days=3)).isoformat()}\n"
            "Note: Saath does not send anything. Review before acting."
        )
        event.add("uid", f"{rem.reminder_id}@saath.demo")
        cal.add_component(event)

    with open(path, "wb") as f:
        f.write(cal.to_ical())

    return path


def run_tracker(plan: TaskPlan, profile: CaseProfile) -> TrackerState:
    """Build reminders for all tasks with deadlines and export .ics."""
    reminders: list[Reminder] = []

    for task in plan.tasks:
        if not task.deadline_date:
            # Suggest a default follow-up in 30 days
            follow_up_date = (date.today() + timedelta(days=30)).isoformat()
        else:
            follow_up_date = task.deadline_date

        reminder = Reminder(
            reminder_id=f"REM_{uuid.uuid4().hex[:6].upper()}",
            task_id=task.task_id,
            title=task.title,
            due_date=follow_up_date,
            follow_up_draft=_follow_up_draft(task, profile),
            exported_ics=False,
        )
        reminders.append(reminder)

    # Build ICS
    ics_filename = f"saath_deadlines_{uuid.uuid4().hex[:8]}.ics"
    try:
        _build_ics(reminders, ics_filename)
        for rem in reminders:
            rem.exported_ics = True
        logger.info("Tracker: ICS written to output/%s", ics_filename)
    except Exception as e:
        logger.error("Tracker: failed to write ICS: %s", e)
        ics_filename = None

    return TrackerState(
        reminders=reminders,
        ics_filename=ics_filename,
    )
