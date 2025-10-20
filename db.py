from sqlalchemy import create_engine, Column, Integer, Float, String, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker

Base = declarative_base()

class Activity(Base):
    __tablename__ = "activities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    type = Column(String)
    distance = Column(Float)
    moving_time = Column(Integer)
    elapsed_time = Column(Integer)
    total_elevation_gain = Column(Float)
    start_date = Column(DateTime)
    average_speed = Column(Float)
    max_speed = Column(Float)
    average_heartrate = Column(Float)
    polyline = Column(String)

    # ✅ define relationship after all columns
    segments = relationship("SegmentEffort", back_populates="activity", cascade="all, delete-orphan")

class SegmentEffort(Base):
    __tablename__ = "segment_efforts"

    id = Column(Integer, primary_key=True, index=True)
    effort_id = Column(Integer, unique=True)
    segment_id = Column(Integer)
    segment_name = Column(String)
    distance = Column(Float)
    average_grade = Column(Float)
    elapsed_time = Column(Integer)
    start_date = Column(DateTime)
    pr_rank = Column(Integer)
    is_pr = Column(Boolean, default=False)
    segment_polyline = Column(String)

    activity_id = Column(Integer, ForeignKey("activities.id"))
    activity = relationship("Activity", back_populates="segments")

# ✅ Initialize DB AFTER classes are defined
engine = create_engine("sqlite:///strava.db")
SessionLocal = sessionmaker(bind=engine)
Base.metadata.create_all(bind=engine)
