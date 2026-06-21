from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class CategoryEnum(str, Enum):
    next_level = "Next Level"
    outgrow_media = "Outgrow Media"
    be_rolling_media = "Be Rolling Media"
    admin = "Admin"
    personal = "Personal"
    unknown = "Unknown"


class RoleEnum(str, Enum):
    admin = "admin"
    member = "member"


# ── Activity ──────────────────────────────────────────────────────────────────

class ActivityRecordIn(BaseModel):
    timestamp: datetime
    app_name: str
    window_title: Optional[str] = None
    url: Optional[str] = None
    duration_seconds: int = 60
    machine_id: Optional[str] = None


class ActivityBatch(BaseModel):
    team_member_id: int
    records: List[ActivityRecordIn]


class ActivityRecordOut(BaseModel):
    id: int
    member_id: int
    timestamp: datetime
    app_name: str
    window_title: Optional[str] = None
    url: Optional[str] = None
    duration_seconds: int
    category: CategoryEnum
    confidence: float
    manually_corrected: bool

    class Config:
        from_attributes = True


# ── Team members ──────────────────────────────────────────────────────────────

class TeamMemberCreate(BaseModel):
    name: str
    email: EmailStr
    role: RoleEnum = RoleEnum.member
    password: str
    consent_raw_data: bool = False


class TeamMemberOut(BaseModel):
    id: int
    name: str
    email: str
    role: RoleEnum
    consent_raw_data: bool
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    member: TeamMemberOut


# ── Classification rules ──────────────────────────────────────────────────────

class ClassificationRuleCreate(BaseModel):
    pattern: str
    match_type: str  # contains | startswith | regex | exact
    field: str = "window_title"
    category: CategoryEnum
    priority: int = 100


class ClassificationRuleOut(ClassificationRuleCreate):
    id: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


# ── Manual correction ─────────────────────────────────────────────────────────

class ManualCorrection(BaseModel):
    record_id: int
    corrected_category: CategoryEnum


# ── Reports ───────────────────────────────────────────────────────────────────

class CategoryBreakdown(BaseModel):
    category: str
    total_seconds: int
    percentage: float


class MemberDailySummary(BaseModel):
    member_id: int
    member_name: str
    date: str
    total_seconds: int
    breakdown: List[CategoryBreakdown]
    top_apps: List[dict]


class WeeklySummary(BaseModel):
    week_start: str
    week_end: str
    per_business: List[dict]
    per_member: List[dict]


# ── Dashboard ─────────────────────────────────────────────────────────────────

class DashboardData(BaseModel):
    today_summaries: List[MemberDailySummary]
    low_confidence_count: int
    active_members: int
