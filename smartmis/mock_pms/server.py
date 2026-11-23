"""
FastAPI Mock PMS Server for SmartMIS.
Simulates a live industry Plant Management System (PMS) / MES gateway.
Supports live streaming of batch records, machine telemetry, and shift simulations.
"""
import sys, os
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional
from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Ensure smartmis directory is on path to import data generator
SMARTMIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if SMARTMIS_DIR not in sys.path:
    sys.path.insert(0, SMARTMIS_DIR)

try:
    from data import sample_pms, MACHINES, PRODUCTS, DEFECTS, SHIFTS
except ImportError:
    from smartmis.data import sample_pms, MACHINES, PRODUCTS, DEFECTS, SHIFTS

app = FastAPI(
    title="Sakthi Mock PMS Gateway",
    version="2.0.0",
    description="Live Manufacturing Plant Management System (PMS) API for Foundry & Machine Shop",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage seeded with realistic simulated manufacturing history
_SEED_DF = sample_pms(days=60, seed=888)
# Convert date objects to ISO strings for JSON serialization
_SEED_RECORDS: List[Dict[str, Any]] = []
for r in _SEED_DF.to_dict(orient="records"):
    if isinstance(r.get("date"), (date, datetime)):
        r["date"] = str(r["date"])
    _SEED_RECORDS.append(r)

RECORDS_DB: List[Dict[str, Any]] = list(_SEED_RECORDS)


class PMSRecordCreate(BaseModel):
    date: str = Field(default_factory=lambda: date.today().isoformat())
    department: str
    machine: str
    product: str
    shift: str = "A"
    planned_qty: int = 180
    produced: int
    rejected: int = 0
    scrap: Optional[int] = None
    rework: Optional[int] = None
    defect: str = "None"
    defect_category: Optional[str] = "None"
    customer: Optional[str] = "Brembo"
    heat_no: Optional[str] = "N/A"
    pattern_id: Optional[str] = "PAT-GEN-01"
    downtime_minutes: int = 0
    downtime_reason: str = "None"
    humidity: Optional[float] = 55.0
    temperature: Optional[float] = 30.0


@app.get("/")
def root():
    return {
        "gateway": "Sakthi Mock PMS Gateway",
        "status": "online",
        "documentation": "/docs",
        "endpoints": {
            "health": "/health",
            "records": "/api/pms/records",
            "latest": "/api/pms/latest",
            "machines": "/api/pms/machines",
        },
    }


@app.get("/health")
def health():
    return {
        "status": "online",
        "system": "Sakthi Mock PMS Gateway",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat(),
        "total_records": len(RECORDS_DB),
        "machines_online": sum(len(m) for m in MACHINES.values()),
    }


@app.get("/api/pms/records")
def get_records(
    since: Optional[str] = Query(None, description="Filter records starting from this ISO date (YYYY-MM-DD)"),
    department: Optional[str] = Query(None, description="Foundry or Machine Shop"),
    machine: Optional[str] = Query(None, description="Machine identifier (e.g. CNC-01)"),
    limit: int = Query(500, ge=1, le=5000),
):
    results = RECORDS_DB
    if since:
        results = [r for r in results if r["date"] >= since]
    if department and department != "All":
        results = [r for r in results if r.get("department") == department]
    if machine:
        results = [r for r in results if r.get("machine") == machine]

    # Return up to limit records sorted by date ascending
    sorted_res = sorted(results, key=lambda x: (x["date"], x.get("shift", "A")))
    sliced = sorted_res[-limit:] if len(sorted_res) > limit else sorted_res
    return {
        "count": len(sliced),
        "total_available": len(results),
        "since": since,
        "records": sliced,
    }


@app.get("/api/pms/latest")
def get_latest_batches(limit: int = Query(24, ge=1, le=100)):
    """Return the most recent batch records (e.g. current day shifts)."""
    return {
        "count": min(limit, len(RECORDS_DB)),
        "records": RECORDS_DB[-limit:],
    }


@app.get("/api/pms/machines")
def get_machine_telemetry():
    """Live machine status and telemetry."""
    telemetry = []
    statuses = ["RUNNING", "RUNNING", "RUNNING", "RUNNING", "IDLE", "MAINTENANCE"]
    import random
    rng = random.Random(42)

    for dept, machines in MACHINES.items():
        for i, m in enumerate(machines):
            st = "MAINTENANCE" if m == "CNC-02" and rng.random() < 0.3 else rng.choice(statuses[:4])
            telemetry.append({
                "machine": m,
                "department": dept,
                "status": st,
                "active_shift": "A",
                "active_product": PRODUCTS[dept][i % len(PRODUCTS[dept])],
                "active_heat_no": f"H{date.today().strftime('%y%m')}-10{i}" if dept == "Foundry" else "N/A",
                "uptime_percentage": 94.2 if m != "CNC-02" else 81.5,
            })
    return {"timestamp": datetime.now().isoformat(), "machines": telemetry}


@app.post("/api/pms/record", status_code=status.HTTP_201_CREATED)
def create_record(record: PMSRecordCreate):
    rec_dict = record.model_dump()
    rec_dict["good"] = max(0, rec_dict["produced"] - rec_dict["rejected"])
    if rec_dict.get("scrap") is None:
        rec_dict["scrap"] = rec_dict["rejected"]
    if rec_dict.get("rework") is None:
        rec_dict["rework"] = 0
    RECORDS_DB.append(rec_dict)
    return {"status": "created", "record": rec_dict}


@app.post("/api/pms/simulate-shift")
def simulate_shift():
    """Simulate completed shift across all machines and append live records."""
    today_str = date.today().isoformat()
    new_records = []
    import random
    rng = random.Random()
    for dept, machines in MACHINES.items():
        for m in machines:
            p = rng.choice(PRODUCTS[dept])
            planned = rng.randint(150, 200)
            downtime = rng.choice([0, 0, 0, 25, 45])
            produced = int(planned * (1 - downtime / 480.0) * rng.uniform(0.92, 1.0))
            is_deg = (m == "CNC-02")
            rate = rng.uniform(0.04, 0.08) if is_deg else rng.uniform(0.015, 0.04)
            rej = int(round(produced * rate))
            def_name = rng.choice(DEFECTS[dept]) if rej else "None"
            rec = {
                "date": today_str,
                "department": dept,
                "machine": m,
                "product": p,
                "shift": "A",
                "planned_qty": planned,
                "produced": produced,
                "rejected": rej,
                "scrap": int(rej * 0.75) if dept == "Foundry" else int(rej * 0.4),
                "rework": int(rej * 0.25) if dept == "Foundry" else int(rej * 0.6),
                "good": produced - rej,
                "defect": def_name,
                "defect_category": "Dimensional Defect" if "size" in def_name else "Other",
                "customer": rng.choice(["Brembo", "Mahindra", "Tata Motors"]),
                "heat_no": f"H{date.today().strftime('%y%m')}-999" if dept == "Foundry" else "N/A",
                "pattern_id": f"PAT-{p[:2].upper()}-01",
                "downtime_minutes": downtime,
                "downtime_reason": "Tool Change" if downtime else "None",
                "humidity": 65.0,
                "temperature": 32.0,
            }
            new_records.append(rec)
            RECORDS_DB.append(rec)
    return {"status": "success", "added_records": len(new_records), "records": new_records}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_pms.server:app", host="127.0.0.1", port=8001, reload=True)
