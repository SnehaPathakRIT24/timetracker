from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, Enum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class CategoryEnum(str, enum.Enum):
    next_level = "Next Level"
    outgrow_media = "Outgrow Media"
    be_rolling_media = "Be Rolling Media"
    admin = "Admin"
    personal = "Personal"
    unknown = "Unknown"


class RoleEnum(str, enum.Enum):
    admin = "admin"
    member = "member"


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    role = Column(Enum(RoleEnum), default=RoleEnum.member, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    consent_raw_data = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    machine_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    activity_records = relationship("ActivityRecord", back_populates="member")
    correction_logs = relationship("CorrectionLog", back_populates="corrected_by_member")


class ActivityRecord(Base):
    __tablename__ = "activity_records"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("team_members.id"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    app_name = Column(String(255), nullable=False)
    window_title = Column(Text, nullable=True)
    url = Column(Text, nullable=True)
    duration_seconds = Column(Integer, nullable=False, default=60)
    category = Column(Enum(CategoryEnum), default=CategoryEnum.unknown)
    confidence = Column(Float, default=0.0)
    manually_corrected = Column(Boolean, default=False)
    machine_id = Column(String(255), nullable=True)
    raw_data_hash = Column(String(64), nullable=True, index=True)  # for dedup + cache
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    member = relationship("TeamMember", back_populates="activity_records")
    correction_logs = relationship("CorrectionLog", back_populates="record")


class ClassificationRule(Base):
    __tablename__ = "classification_rules"

    id = Column(Integer, primary_key=True, index=True)
    pattern = Column(String(500), nullable=False)
    match_type = Column(String(50), nullable=False)  # contains, startswith, regex, exact
    field = Column(String(50), default="window_title")  # window_title, app_name, url
    category = Column(Enum(CategoryEnum), nullable=False)
    priority = Column(Integer, default=100)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class CorrectionLog(Base):
    __tablename__ = "correction_log"

    id = Column(Integer, primary_key=True, index=True)
    record_id = Column(Integer, ForeignKey("activity_records.id"), nullable=False)
    original_category = Column(Enum(CategoryEnum))
    corrected_category = Column(Enum(CategoryEnum), nullable=False)
    corrected_by = Column(Integer, ForeignKey("team_members.id"), nullable=False)
    corrected_at = Column(DateTime(timezone=True), server_default=func.now())

    record = relationship("ActivityRecord", back_populates="correction_logs")
    corrected_by_member = relationship("TeamMember", back_populates="correction_logs")


class DailyInsight(Base):
    __tablename__ = "daily_insights"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    member_id = Column(Integer, ForeignKey("team_members.id"), nullable=True)  # null = team-wide
    summary_text = Column(Text)
    productivity_score = Column(Float, nullable=True)
    anomalies = Column(Text, nullable=True)  # JSON string
    recommendations = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ClassificationCache(Base):
    __tablename__ = "classification_cache"

    id = Column(Integer, primary_key=True, index=True)
    cache_key = Column(String(64), unique=True, nullable=False, index=True)
    category = Column(Enum(CategoryEnum), nullable=False)
    confidence = Column(Float, nullable=False)
    hit_count = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
