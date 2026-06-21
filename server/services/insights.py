"""
Daily insight engine. Called once per day via scheduler.
Uses Claude claude-opus-4-8 to generate team summaries, anomaly alerts,
productivity scores, and recommendations.
"""

import json
import os
import logging
from datetime import datetime, date, timedelta
from typing import List, Optional

import anthropic
from sqlalchemy.orm import Session
from sqlalchemy import func

from server.models.database import ActivityRecord, TeamMember, DailyInsight, CategoryEnum

logger = logging.getLogger(__name__)

INSIGHT_SYSTEM = """You are an AI productivity analyst for a small creative media team.
The team works across three businesses: Next Level (business coaching),
Outgrow Media (social media & marketing), and Be Rolling Media (video production).

Analyze the day's activity data and return a JSON object with:
{
  "summary": "Plain English paragraph about the team's day",
  "anomalies": ["list of anomaly strings, e.g. 'Sneha spent 2.3h on personal browsing'"],
  "member_scores": {"member_name": score_0_to_100, ...},
  "recommendations": ["list of actionable recommendations for tomorrow"],
  "business_highlights": {"Next Level": "one sentence", "Outgrow Media": "...", "Be Rolling Media": "..."}
}

Productivity score logic:
- 100 = focused work the entire day on business categories
- 0 = no work or entirely personal/unknown
- Deduct points for: long personal blocks, many app switches, admin-heavy days
- Add points for: deep work sessions (30+ min same category), all three businesses covered"""


def _format_member_data(member: TeamMember, records: List[ActivityRecord]) -> dict:
    by_category: dict = {}
    for rec in records:
        cat = rec.category.value if rec.category else "Unknown"
        by_category[cat] = by_category.get(cat, 0) + rec.duration_seconds

    top_apps: dict = {}
    for rec in records:
        top_apps[rec.app_name] = top_apps.get(rec.app_name, 0) + rec.duration_seconds
    top_apps_sorted = sorted(top_apps.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "name": member.name,
        "total_seconds": sum(r.duration_seconds for r in records),
        "by_category": by_category,
        "top_apps": dict(top_apps_sorted),
    }


def generate_daily_insights(
    db: Session,
    target_date: Optional[date] = None,
    api_key: Optional[str] = None,
    send_email: bool = True,
) -> dict:
    if not api_key:
        api_key = os.getenv("ANTHROPIC_API_KEY")
    if not target_date:
        target_date = date.today() - timedelta(days=1)

    start = datetime.combine(target_date, datetime.min.time())
    end = datetime.combine(target_date, datetime.max.time())

    members = db.query(TeamMember).filter(TeamMember.is_active == True).all()
    team_data = []
    for member in members:
        records = (
            db.query(ActivityRecord)
            .filter(
                ActivityRecord.member_id == member.id,
                ActivityRecord.timestamp >= start,
                ActivityRecord.timestamp <= end,
            )
            .all()
        )
        if records:
            team_data.append(_format_member_data(member, records))

    if not team_data:
        logger.info(f"No activity data for {target_date}")
        return {}

    if not api_key:
        logger.warning("No Anthropic API key — skipping insights")
        return {}

    client = anthropic.Anthropic(api_key=api_key)
    user_msg = (
        f"Date: {target_date.isoformat()}\n"
        f"Team activity data:\n{json.dumps(team_data, indent=2)}"
    )

    try:
        response = client.messages.create(
            model="claude-opus-4-8",
            max_tokens=2048,
            system=INSIGHT_SYSTEM,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        insight_data = json.loads(raw)
    except Exception as e:
        logger.error(f"Insight generation failed: {e}")
        return {}

    # Persist team-wide insight
    insight = DailyInsight(
        date=start,
        member_id=None,
        summary_text=insight_data.get("summary", ""),
        anomalies=json.dumps(insight_data.get("anomalies", [])),
        recommendations=json.dumps(insight_data.get("recommendations", [])),
    )
    db.add(insight)

    # Persist per-member productivity scores
    for member in members:
        score = insight_data.get("member_scores", {}).get(member.name)
        if score is not None:
            member_insight = DailyInsight(
                date=start,
                member_id=member.id,
                summary_text=insight_data.get("summary", ""),
                productivity_score=float(score),
            )
            db.add(member_insight)

    db.commit()

    if send_email:
        _send_summary_email(insight_data, target_date)

    return insight_data


def _send_summary_email(data: dict, target_date: date) -> None:
    """Send via SMTP or SendGrid. Configure via env vars."""
    smtp_host = os.getenv("SMTP_HOST")
    smtp_user = os.getenv("SMTP_USER")
    smtp_pass = os.getenv("SMTP_PASS")
    admin_email = os.getenv("ADMIN_EMAIL", "snehapathak752@gmail.com")
    slack_webhook = os.getenv("SLACK_WEBHOOK_URL")

    summary = data.get("summary", "")
    anomalies = "\n".join(f"• {a}" for a in data.get("anomalies", []))
    recs = "\n".join(f"• {r}" for r in data.get("recommendations", []))

    body = f"""Daily Team Summary — {target_date.isoformat()}

{summary}

⚠️  Anomalies:
{anomalies or 'None detected'}

💡 Recommendations for tomorrow:
{recs or 'None'}
"""

    if slack_webhook:
        try:
            import requests
            requests.post(slack_webhook, json={"text": body}, timeout=10)
        except Exception as e:
            logger.error(f"Slack webhook failed: {e}")

    if smtp_host and smtp_user and smtp_pass:
        try:
            import smtplib
            from email.mime.text import MIMEText
            msg = MIMEText(body)
            msg["Subject"] = f"Time Tracker Daily Summary — {target_date.isoformat()}"
            msg["From"] = smtp_user
            msg["To"] = admin_email
            with smtplib.SMTP_SSL(smtp_host, 465) as server:
                server.login(smtp_user, smtp_pass)
                server.sendmail(smtp_user, [admin_email], msg.as_string())
        except Exception as e:
            logger.error(f"Email send failed: {e}")
