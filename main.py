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

from difflib import SequenceMatcher

class LeadMatchRequest(BaseModel):
    ads_leads: List[str]
    crm_leads: List[str]

@app.post("/match_leads")
def match_leads(request: LeadMatchRequest):
    matches = []
    for ad_email in request.ads_leads:
        for crm_email in request.crm_leads:
            # Basic fuzzy match for similar emails
            ratio = SequenceMatcher(None, ad_email.lower(), crm_email.lower()).ratio()
            if ratio > 0.8:
                matches.append({"ad_email": ad_email, "crm_email": crm_email, "match_score": round(ratio, 2)})
    return {"matches": matches, "total_matches": len(matches)}
