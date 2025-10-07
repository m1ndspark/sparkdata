from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "FastAPI is running successfully!"}

from pydantic import BaseModel
from typing import List, Optional

class LeadRecord(BaseModel):
    email: str
    revenue: Optional[float] = 0.0

class AnalyzeRequest(BaseModel):
    ad_spend: float
    leads: List[LeadRecord]

@app.post("/analyze_roi")
def analyze_roi(request: AnalyzeRequest):
    total_revenue = sum(lead.revenue for lead in request.leads)
    roi = total_revenue / request.ad_spend if request.ad_spend > 0 else 0
    return {
        "ad_spend": request.ad_spend,
        "total_revenue": total_revenue,
        "roi": round(roi, 2)
    }
