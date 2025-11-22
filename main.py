from fastapi import FastAPI, Depends
from db import SessionLocal, Activity, SegmentEffort, get_db
from strava_api import get_all_activities, get_activity_details
from datetime import datetime
import time
from polyline import decode
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session



app = FastAPI(title="Strava Database API")

@app.get("/", response_class=HTMLResponse)
def root():
    with open("templates/index.html", encoding="utf-8") as f:
        return f.read()

@app.api_route("/sync", methods=["GET", "POST"])
def sync_activities(limit: int = 100):
    session = SessionLocal()
    inserted_activities = 0
    inserted_segments = 0

    try:
        activities = get_all_activities(limit=limit)
        print(f"Fetched {len(activities)} activities")

        for act in activities:
            if session.query(Activity).filter(Activity.id == act["id"]).first():
                continue  # skip existing activities

            # Create new activity
            new_act = Activity(
                id=act["id"],
                name=act.get("name"),
                type=act.get("type"),
                distance=act.get("distance"),
                moving_time=act.get("moving_time"),
                elapsed_time=act.get("elapsed_time"),
                total_elevation_gain=act.get("total_elevation_gain"),
                start_date=datetime.fromisoformat(act["start_date"].replace("Z", "+00:00")),
                average_speed=act.get("average_speed"),
                max_speed=act.get("max_speed"),
                average_heartrate=act.get("average_heartrate"),
                polyline=act.get("map", {}).get("summary_polyline"),
            )
            session.add(new_act)
            inserted_activities += 1

            # Get detailed activity to extract segments
            details = get_activity_details(act["id"])
            time.sleep(1.5)  # to avoid rate limit

            for effort in details.get("segment_efforts", []):
                seg = effort["segment"]
                seg_id = seg["id"]
                seg_name = seg["name"]
                pr_rank = effort.get("pr_rank")

                segment_effort = SegmentEffort(
                    effort_id=effort["id"],
                    segment_id=seg_id,
                    segment_name=seg_name,
                    distance=seg.get("distance"),
                    average_grade=seg.get("average_grade"),
                    elapsed_time=effort.get("elapsed_time"),
                    start_date=datetime.fromisoformat(effort["start_date"].replace("Z", "+00:00")),
                    pr_rank=pr_rank,
                    is_pr=(pr_rank == 1),
                    activity=new_act,
                )
                session.add(segment_effort)
                inserted_segments += 1

        session.commit()
        return {
            "inserted_activities": inserted_activities,
            "inserted_segments": inserted_segments,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    finally:
        session.close()

@app.get("/activities")
def list_activities():
    session = SessionLocal()
    acts = session.query(Activity).order_by(Activity.start_date.desc()).all()
    return [
        {
            "id": a.id,
            "name": a.name,
            "distance_km": round(a.distance / 1000, 2),
            "start_date": a.start_date,
        }
        for a in acts
    ]

@app.get("/latest")
def get_latest_activity():
    """Fetch your most recent Strava activity directly from the API."""
    try:
        from strava_api import get_all_activities
        activities = get_all_activities(limit=1)
        print("DEBUG: Strava response ->", activities)  # 👈 print full JSON

        # if the response is a dict with an error
        if isinstance(activities, dict) and "message" in activities:
            return {"error": activities}

        if not isinstance(activities, list) or len(activities) == 0:
            return {"message": "No activities found or invalid response."}

        latest = activities[0]
        return {
            "id": latest.get("id"),
            "name": latest.get("name"),
            "type": latest.get("type"),
            "distance_km": round(latest.get("distance", 0) / 1000, 2),
            "moving_time_min": round(latest.get("moving_time", 0) / 60, 1),
            "start_date": latest.get("start_date"),
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}
    
@app.get("/prs")
def get_all_prs():
    session = SessionLocal()
    prs = session.query(SegmentEffort).filter(SegmentEffort.is_pr == True).all()

    results = []
    for pr in prs:
        results.append({
            "segment_name": pr.segment_name,
            "distance_km": round(pr.distance / 1000, 2) if pr.distance else None,
            "elapsed_time_s": pr.elapsed_time,
            "activity_id": pr.activity_id,
            "start_date": pr.start_date,
        })

    session.close()
    return results

# @app.get("/prs_geojson")
# def get_all_pr_segments():
#     """
#     Returns all PR segment polylines (is_pr == True) as a GeoJSON FeatureCollection.
#     """
#     session = SessionLocal()

#     prs = (
#         session.query(SegmentEffort)
#         .filter(SegmentEffort.is_pr == True, SegmentEffort.segment_polyline != None)
#         .all()
#     )

#     features = []
#     for seg in prs:
#         try:
#             coords = decode(seg.segment_polyline)
#         except Exception:
#             continue

#         features.append({
#             "type": "Feature",
#             "geometry": {
#                 "type": "LineString",
#                 "coordinates": [[lon, lat] for lat, lon in coords],
#             },
#             "properties": {
#                 "segment_name": seg.segment_name,
#                 "distance_km": round(seg.distance / 1000, 2) if seg.distance else None,
#                 "avg_grade": seg.average_grade,
#                 "elapsed_time_s": seg.elapsed_time,
#                 "start_date": str(seg.start_date),
#             },
#         })

#     session.close()
#     return JSONResponse(content={"type": "FeatureCollection", "features": features})

@app.get("/prs_table")
def prs_table():
    session = SessionLocal()
    best_prs = (
        session.query(
            SegmentEffort.segment_id,
            SegmentEffort.segment_name,
            func.min(SegmentEffort.elapsed_time).label("best_time"),
            func.max(SegmentEffort.start_date).label("last_date"),
            SegmentEffort.segment_polyline,
        )
        .filter(SegmentEffort.is_pr == True, SegmentEffort.segment_polyline != None)
        .group_by(SegmentEffort.segment_id, SegmentEffort.segment_name, SegmentEffort.segment_polyline)
        .all()
    )
    session.close()
    return [dict(row._mapping) for row in best_prs]

@app.get("/segment/{segment_id}/progress")
def get_segment_progress(segment_id: int, db: Session = Depends(get_db)):
    """
    Return all efforts for a given segment, sorted by date.
    Each entry includes date, elapsed_time, and average_speed (if available).
    """
    efforts = (
        db.query(SegmentEffort)
        .filter(SegmentEffort.segment_id == segment_id)
        .order_by(SegmentEffort.start_date)
        .all()
    )

    if not efforts:
        return {"message": f"No efforts found for segment {segment_id}", "data": []}

    return {
        "segment_id": segment_id,
        "segment_name": efforts[0].segment_name if efforts[0].segment_name else None,
        "data": [
            {
                "date": e.start_date.isoformat() if isinstance(e.start_date, datetime) else e.start_date,
                "elapsed_time": e.elapsed_time,
                # "distance": e.distance,
                # "average_speed": (e.distance / e.elapsed_time) if e.elapsed_time and e.distance else None,
                # "is_pr": e.is_pr,
            }
            for e in efforts
        ],
    }