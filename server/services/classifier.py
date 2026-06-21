"""
AI Classification Engine using Claude API.
Rules are checked first (cheaper), then Claude for anything unresolved.
Identical app+title combos are cached in the DB to avoid repeat API calls.
Manual corrections are stored and fed back as few-shot examples.
"""

import hashlib
import json
import re
import logging
from typing import List, Optional

import anthropic
from sqlalchemy.orm import Session

from server.models.database import (
    ActivityRecord, ClassificationRule, ClassificationCache,
    CorrectionLog, CategoryEnum
)

logger = logging.getLogger(__name__)

BUSINESSES = ["Next Level", "Outgrow Media", "Be Rolling Media"]

SYSTEM_PROMPT = """You are a time classification assistant for a media and business team.
The team works across three businesses:
- Next Level: business coaching, growth strategy, client presentations, sales calls, coaching content, webinars, course creation
- Outgrow Media: social media content creation, marketing strategy, brand strategy, copywriting, social scheduling, Outgrow client work
- Be Rolling Media: video production, video editing, filming, camera work, DaVinci Resolve, Premiere Pro, After Effects, CapCut, Be Rolling client work

Additional categories:
- Admin: email, calendar, Slack, Zoom/Teams calls that don't fit above, general communication, project management tools
- Personal: personal browsing, entertainment, YouTube (non-work), social media personal use, shopping
- Unknown: cannot determine from the information given

Classify each activity record into exactly one category.
Return ONLY a valid JSON array where each element has:
  "id": the original id from input
  "category": one of the exact strings above
  "confidence": float 0.0-1.0

Be decisive. When the window title or URL clearly indicates a business, use that.
Video editors working on any project → Be Rolling Media.
Writers researching → likely Outgrow Media or Next Level based on context."""


def _cache_key(app_name: str, window_title: Optional[str], url: Optional[str]) -> str:
    raw = f"{app_name}|{window_title or ''}|{url or ''}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _apply_rules(
    record: dict, rules: List[ClassificationRule]
) -> Optional[str]:
    """Return category string if a rule matches, else None."""
    field_map = {
        "window_title": record.get("window_title") or "",
        "app_name": record.get("app_name") or "",
        "url": record.get("url") or "",
    }
    for rule in sorted(rules, key=lambda r: r.priority):
        value = field_map.get(rule.field, "").lower()
        pattern = rule.pattern.lower()
        if rule.match_type == "contains" and pattern in value:
            return rule.category.value
        elif rule.match_type == "startswith" and value.startswith(pattern):
            return rule.category.value
        elif rule.match_type == "exact" and value == pattern:
            return rule.category.value
        elif rule.match_type == "regex":
            try:
                if re.search(rule.pattern, field_map.get(rule.field, ""), re.IGNORECASE):
                    return rule.category.value
            except re.error:
                pass
    return None


def _get_few_shot_examples(db: Session, limit: int = 10) -> List[dict]:
    """Pull recent manual corrections to use as few-shot examples."""
    corrections = (
        db.query(CorrectionLog)
        .join(ActivityRecord)
        .order_by(CorrectionLog.corrected_at.desc())
        .limit(limit)
        .all()
    )
    examples = []
    for c in corrections:
        rec = c.record
        examples.append({
            "app_name": rec.app_name,
            "window_title": rec.window_title,
            "url": rec.url,
            "category": c.corrected_category.value,
        })
    return examples


def classify_batch(
    records: List[dict],
    db: Session,
    anthropic_api_key: str,
) -> List[dict]:
    """
    records: list of dicts with keys: id, app_name, window_title, url
    Returns the same list with 'category' and 'confidence' added.
    """
    rules = db.query(ClassificationRule).filter(
        ClassificationRule.is_active == True
    ).all()

    results = {}
    needs_ai = []

    for rec in records:
        rec_id = rec["id"]

        # 1. Check rule engine
        cat = _apply_rules(rec, rules)
        if cat:
            results[rec_id] = {"category": cat, "confidence": 1.0, "source": "rule"}
            continue

        # 2. Check cache
        key = _cache_key(rec["app_name"], rec.get("window_title"), rec.get("url"))
        cached = db.query(ClassificationCache).filter(
            ClassificationCache.cache_key == key
        ).first()
        if cached:
            cached.hit_count += 1
            db.commit()
            results[rec_id] = {
                "category": cached.category.value,
                "confidence": cached.confidence,
                "source": "cache",
            }
            continue

        needs_ai.append({**rec, "_cache_key": key})

    # 3. Send uncached records to Claude
    if needs_ai and anthropic_api_key:
        ai_results = _classify_with_claude(needs_ai, db, anthropic_api_key)
        for rec_id, res in ai_results.items():
            results[rec_id] = res
            # Cache the result
            rec = next(r for r in needs_ai if r["id"] == rec_id)
            try:
                cat_enum = CategoryEnum(res["category"])
                cache_entry = ClassificationCache(
                    cache_key=rec["_cache_key"],
                    category=cat_enum,
                    confidence=res["confidence"],
                )
                db.add(cache_entry)
            except ValueError:
                pass
        try:
            db.commit()
        except Exception:
            db.rollback()

    # Merge results back
    for rec in records:
        rec_id = rec["id"]
        if rec_id in results:
            rec["category"] = results[rec_id]["category"]
            rec["confidence"] = results[rec_id]["confidence"]
        else:
            rec["category"] = "Unknown"
            rec["confidence"] = 0.0

    return records


def _classify_with_claude(
    records: List[dict],
    db: Session,
    api_key: str,
) -> dict:
    client = anthropic.Anthropic(api_key=api_key)

    few_shot = _get_few_shot_examples(db)
    few_shot_text = ""
    if few_shot:
        few_shot_text = "\n\nPrevious corrections from this team (use as examples):\n"
        for ex in few_shot:
            few_shot_text += (
                f"- App: {ex['app_name']}, Title: {ex['window_title']}, "
                f"URL: {ex['url']} → {ex['category']}\n"
            )

    payload = [
        {
            "id": r["id"],
            "app_name": r["app_name"],
            "window_title": r.get("window_title"),
            "url": r.get("url"),
        }
        for r in records
    ]

    user_msg = (
        f"Classify these activity records:{few_shot_text}\n\n"
        f"Records:\n{json.dumps(payload, indent=2)}"
    )

    try:
        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        classified = json.loads(raw)
        return {
            item["id"]: {
                "category": item["category"],
                "confidence": item.get("confidence", 0.8),
            }
            for item in classified
        }
    except Exception as e:
        logger.error(f"Claude classification failed: {e}")
        return {r["id"]: {"category": "Unknown", "confidence": 0.0} for r in records}
