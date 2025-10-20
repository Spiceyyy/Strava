from db import SessionLocal, SegmentEffort
from strava_api import get_segment_polyline
import time

session = SessionLocal()

# Only fetch PRs with missing polylines
prs = session.query(SegmentEffort).filter(
    SegmentEffort.is_pr == True,
    SegmentEffort.segment_polyline == None
).all()

print(f"Found {len(prs)} PR segments missing polylines.")

for seg in prs:
    seg_id = seg.segment_id
    print(f"Fetching segment {seg_id} ({seg.segment_name}) ...")

    poly = None
    try:
        poly = get_segment_polyline(seg_id)
    except Exception as e:
        print(f"⚠️ Error fetching {seg_id}: {e}")
        continue

    if poly:
        seg.segment_polyline = poly
        session.commit()
        print(f"✅ Saved polyline for {seg.segment_name}")
    else:
        print(f"❌ No polyline for {seg.segment_name}")

session.close()
print("🎯 Done fetching missing PR polylines.")
