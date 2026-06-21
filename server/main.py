import os
import logging
from contextlib import asynccontextmanager
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, status, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import create_engine, func, and_
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime, date, timedelta
import json
import asyncio
from apscheduler.schedulers.background import BackgroundScheduler

from server.models.database import (
    Base, TeamMember, ActivityRecord, ClassificationRule,
    CorrectionLog, DailyInsight, CategoryEnum, RoleEnum
)
from server.schemas.schemas import (
    ActivityBatch, TeamMemberCreate, TeamMemberOut, LoginRequest, TokenResponse,
    ClassificationRuleCreate, ClassificationRuleOut, ManualCorrection,
    ActivityRecordOut, MemberDailySummary, CategoryBreakdown
)
from server.services.auth import (
    hash_password, authenticate_member, create_access_token, decode_token
)
from server.services.classifier import classify_batch
from server.services.insights import generate_daily_insights

# ── Setup ──────────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://tracker:tracker@localhost:5432/timetracker")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        self.active.remove(ws)

    async def broadcast(self, data: dict):
        dead = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.active.remove(ws)

manager = ConnectionManager()


def seed_admin(db: Session):
    existing = db.query(TeamMember).filter(TeamMember.email == "snehapathak752@gmail.com").first()
    if not existing:
        admin = TeamMember(
            name="Sneha",
            email="snehapathak752@gmail.com",
            role=RoleEnum.admin,
            hashed_password=hash_password("changeme123"),
            consent_raw_data=True,
        )
        db.add(admin)
        db.commit()
        logger.info("Seeded admin user: snehapathak752@gmail.com / changeme123")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    with SessionLocal() as db:
        seed_admin(db)

    # Schedule daily insights at 11 PM
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: _run_insights(),
        "cron", hour=23, minute=0
    )
    scheduler.start()
    yield
    scheduler.shutdown()


def _run_insights():
    with SessionLocal() as db:
        generate_daily_insights(db, api_key=ANTHROPIC_API_KEY)


app = FastAPI(title="TimeTracker API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Auth helpers ───────────────────────────────────────────────────────────────

bearer_scheme = HTTPBearer()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_member(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> TeamMember:
    payload = decode_token(credentials.credentials)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    member = db.query(TeamMember).filter(TeamMember.id == payload.get("sub")).first()
    if not member:
        raise HTTPException(status_code=401, detail="User not found")
    return member


def require_admin(member: TeamMember = Depends(get_current_member)) -> TeamMember:
    if member.role != RoleEnum.admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return member


# ── Auth endpoints ─────────────────────────────────────────────────────────────

@app.post("/auth/login", response_model=TokenResponse)
def login(req: LoginRequest, db: Session = Depends(get_db)):
    member = authenticate_member(db, req.email, req.password)
    if not member:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": member.id, "role": member.role.value})
    return TokenResponse(
        access_token=token,
        member=TeamMemberOut.model_validate(member)
    )


# ── Activity ingestion ─────────────────────────────────────────────────────────

@app.post("/activity", status_code=202)
async def ingest_activity(
    batch: ActivityBatch,
    db: Session = Depends(get_db),
):
    member = db.query(TeamMember).filter(TeamMember.id == batch.team_member_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="Team member not found")

    records_for_ai = []
    db_records = []

    for i, rec in enumerate(batch.records):
        db_rec = ActivityRecord(
            member_id=member.id,
            timestamp=rec.timestamp,
            app_name=rec.app_name,
            window_title=rec.window_title,
            url=rec.url,
            duration_seconds=rec.duration_seconds,
            machine_id=rec.machine_id,
            category=CategoryEnum.unknown,
            confidence=0.0,
        )
        db.add(db_rec)
        db.flush()  # get the id
        records_for_ai.append({
            "id": db_rec.id,
            "app_name": rec.app_name,
            "window_title": rec.window_title,
            "url": rec.url,
        })
        db_records.append(db_rec)

    # Classify
    if ANTHROPIC_API_KEY:
        classified = classify_batch(records_for_ai, db, ANTHROPIC_API_KEY)
        for item in classified:
            rec_id = item["id"]
            db_rec = next(r for r in db_records if r.id == rec_id)
            try:
                db_rec.category = CategoryEnum(item["category"])
            except ValueError:
                db_rec.category = CategoryEnum.unknown
            db_rec.confidence = item.get("confidence", 0.0)

    db.commit()

    # Broadcast to WebSocket clients
    await manager.broadcast({
        "type": "new_activity",
        "member_id": member.id,
        "member_name": member.name,
        "count": len(db_records),
    })

    return {"accepted": len(db_records)}


# ── Team management ────────────────────────────────────────────────────────────

@app.post("/team/member", response_model=TeamMemberOut)
def add_team_member(
    req: TeamMemberCreate,
    db: Session = Depends(get_db),
    _: TeamMember = Depends(require_admin),
):
    if db.query(TeamMember).filter(TeamMember.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    member = TeamMember(
        name=req.name,
        email=req.email,
        role=RoleEnum(req.role.value),
        hashed_password=hash_password(req.password),
        consent_raw_data=req.consent_raw_data,
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


@app.get("/team/members", response_model=List[TeamMemberOut])
def list_members(
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    if current.role == RoleEnum.admin:
        return db.query(TeamMember).filter(TeamMember.is_active == True).all()
    return [current]


# ── Reports ────────────────────────────────────────────────────────────────────

@app.get("/report/daily")
def daily_report(
    target_date: Optional[str] = None,
    member_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    if target_date:
        d = date.fromisoformat(target_date)
    else:
        d = date.today()

    start = datetime.combine(d, datetime.min.time())
    end = datetime.combine(d, datetime.max.time())

    query = db.query(ActivityRecord).filter(
        ActivityRecord.timestamp >= start,
        ActivityRecord.timestamp <= end,
    )

    if current.role != RoleEnum.admin:
        query = query.filter(ActivityRecord.member_id == current.id)
    elif member_id:
        query = query.filter(ActivityRecord.member_id == member_id)

    records = query.all()
    members = {m.id: m for m in db.query(TeamMember).all()}

    # Group by member
    by_member: dict = {}
    for rec in records:
        mid = rec.member_id
        if mid not in by_member:
            by_member[mid] = []
        by_member[mid].append(rec)

    summaries = []
    for mid, recs in by_member.items():
        member = members.get(mid)
        if not member:
            continue
        total = sum(r.duration_seconds for r in recs)
        by_cat: dict = {}
        for r in recs:
            cat = r.category.value if r.category else "Unknown"
            by_cat[cat] = by_cat.get(cat, 0) + r.duration_seconds

        breakdown = [
            {"category": cat, "total_seconds": secs, "percentage": round(secs / total * 100, 1) if total else 0}
            for cat, secs in sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        ]

        app_totals: dict = {}
        for r in recs:
            app_totals[r.app_name] = app_totals.get(r.app_name, 0) + r.duration_seconds
        top_apps = sorted(app_totals.items(), key=lambda x: x[1], reverse=True)[:10]

        timeline = []
        for r in sorted(recs, key=lambda x: x.timestamp):
            entry = {
                "timestamp": r.timestamp.isoformat(),
                "app_name": r.app_name,
                "duration_seconds": r.duration_seconds,
                "category": r.category.value if r.category else "Unknown",
                "confidence": r.confidence,
                "id": r.id,
            }
            if current.role == RoleEnum.admin and not member.consent_raw_data:
                entry.pop("app_name", None)
            else:
                entry["window_title"] = r.window_title
                entry["url"] = r.url
            timeline.append(entry)

        summaries.append({
            "member_id": mid,
            "member_name": member.name,
            "date": d.isoformat(),
            "total_seconds": total,
            "breakdown": breakdown,
            "top_apps": [{"app": a, "seconds": s} for a, s in top_apps],
            "timeline": timeline,
        })

    return {"date": d.isoformat(), "members": summaries}


@app.get("/report/weekly")
def weekly_report(
    week_start: Optional[str] = None,
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    if week_start:
        start_date = date.fromisoformat(week_start)
    else:
        today = date.today()
        start_date = today - timedelta(days=today.weekday())

    end_date = start_date + timedelta(days=6)
    start = datetime.combine(start_date, datetime.min.time())
    end = datetime.combine(end_date, datetime.max.time())

    query = db.query(ActivityRecord).filter(
        ActivityRecord.timestamp >= start,
        ActivityRecord.timestamp <= end,
    )
    if current.role != RoleEnum.admin:
        query = query.filter(ActivityRecord.member_id == current.id)

    records = query.all()
    members = {m.id: m for m in db.query(TeamMember).all()}

    # Per day per business totals
    daily_business: dict = {}
    member_totals: dict = {}

    for rec in records:
        day = rec.timestamp.date().isoformat()
        cat = rec.category.value if rec.category else "Unknown"
        mid = rec.member_id

        if day not in daily_business:
            daily_business[day] = {}
        daily_business[day][cat] = daily_business[day].get(cat, 0) + rec.duration_seconds

        if mid not in member_totals:
            member_totals[mid] = {}
        member_totals[mid][cat] = member_totals[mid].get(cat, 0) + rec.duration_seconds

    per_day = [
        {"date": day, "breakdown": cats}
        for day, cats in sorted(daily_business.items())
    ]

    per_member = [
        {
            "member_id": mid,
            "member_name": members[mid].name if mid in members else str(mid),
            "breakdown": cats,
            "total_seconds": sum(cats.values()),
        }
        for mid, cats in member_totals.items()
        if mid in members
    ]

    return {
        "week_start": start_date.isoformat(),
        "week_end": end_date.isoformat(),
        "per_day": per_day,
        "per_member": per_member,
    }


@app.get("/report/projects")
def projects_report(
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    def _aggregate(since: date):
        start = datetime.combine(since, datetime.min.time())
        query = db.query(ActivityRecord).filter(ActivityRecord.timestamp >= start)
        if current.role != RoleEnum.admin:
            query = query.filter(ActivityRecord.member_id == current.id)
        recs = query.all()
        by_cat: dict = {}
        for r in recs:
            cat = r.category.value if r.category else "Unknown"
            by_cat[cat] = by_cat.get(cat, 0) + r.duration_seconds
        total = sum(by_cat.values()) or 1
        return [
            {"category": cat, "seconds": secs, "percentage": round(secs / total * 100, 1)}
            for cat, secs in sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        ]

    return {
        "this_week": _aggregate(week_start),
        "this_month": _aggregate(month_start),
    }


# ── Manual correction ──────────────────────────────────────────────────────────

@app.post("/classify/manual")
def manual_correction(
    req: ManualCorrection,
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    record = db.query(ActivityRecord).filter(ActivityRecord.id == req.record_id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    if current.role != RoleEnum.admin and record.member_id != current.id:
        raise HTTPException(status_code=403)

    log = CorrectionLog(
        record_id=record.id,
        original_category=record.category,
        corrected_category=CategoryEnum(req.corrected_category.value),
        corrected_by=current.id,
    )
    db.add(log)
    record.category = CategoryEnum(req.corrected_category.value)
    record.manually_corrected = True
    db.commit()
    return {"ok": True}


# ── Low-confidence records for review ─────────────────────────────────────────

@app.get("/review/low-confidence")
def low_confidence(
    threshold: float = 0.7,
    limit: int = 50,
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    query = db.query(ActivityRecord).filter(
        ActivityRecord.confidence < threshold,
        ActivityRecord.manually_corrected == False,
    ).order_by(ActivityRecord.timestamp.desc())

    if current.role != RoleEnum.admin:
        query = query.filter(ActivityRecord.member_id == current.id)

    records = query.limit(limit).all()
    members = {m.id: m for m in db.query(TeamMember).all()}

    result = []
    for r in records:
        m = members.get(r.member_id)
        result.append({
            "id": r.id,
            "member_name": m.name if m else "Unknown",
            "timestamp": r.timestamp.isoformat(),
            "app_name": r.app_name,
            "window_title": r.window_title,
            "url": r.url,
            "category": r.category.value if r.category else "Unknown",
            "confidence": r.confidence,
        })
    return result


# ── Classification rules ───────────────────────────────────────────────────────

@app.get("/rules", response_model=List[ClassificationRuleOut])
def list_rules(db: Session = Depends(get_db), _: TeamMember = Depends(require_admin)):
    return db.query(ClassificationRule).order_by(ClassificationRule.priority).all()


@app.post("/rules", response_model=ClassificationRuleOut)
def create_rule(
    req: ClassificationRuleCreate,
    db: Session = Depends(get_db),
    _: TeamMember = Depends(require_admin),
):
    rule = ClassificationRule(
        pattern=req.pattern,
        match_type=req.match_type,
        field=req.field,
        category=CategoryEnum(req.category.value),
        priority=req.priority,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@app.delete("/rules/{rule_id}")
def delete_rule(
    rule_id: int,
    db: Session = Depends(get_db),
    _: TeamMember = Depends(require_admin),
):
    rule = db.query(ClassificationRule).filter(ClassificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404)
    db.delete(rule)
    db.commit()
    return {"ok": True}


# ── Insights ───────────────────────────────────────────────────────────────────

@app.get("/insights/daily")
def get_daily_insights(
    target_date: Optional[str] = None,
    db: Session = Depends(get_db),
    current: TeamMember = Depends(get_current_member),
):
    if target_date:
        d = date.fromisoformat(target_date)
    else:
        d = date.today() - timedelta(days=1)

    start = datetime.combine(d, datetime.min.time())
    insights = db.query(DailyInsight).filter(
        DailyInsight.date >= start,
        DailyInsight.member_id == None,
    ).first()

    if not insights:
        return {"message": "No insights generated yet for this date"}

    return {
        "date": d.isoformat(),
        "summary": insights.summary_text,
        "anomalies": json.loads(insights.anomalies or "[]"),
        "recommendations": json.loads(insights.recommendations or "[]"),
    }


@app.post("/insights/generate")
def trigger_insights(
    target_date: Optional[str] = None,
    db: Session = Depends(get_db),
    _: TeamMember = Depends(require_admin),
):
    d = date.fromisoformat(target_date) if target_date else date.today() - timedelta(days=1)
    result = generate_daily_insights(db, target_date=d, api_key=ANTHROPIC_API_KEY)
    return result


# ── WebSocket ──────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()  # keep alive
    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ── Health ─────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"status": "ok"}
