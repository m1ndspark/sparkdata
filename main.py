from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
from difflib import SequenceMatcher
import pandas as pd
import io

app = FastAPI()

# Temporary in-memory storage for uploaded data
uploaded_data_cache = {}

@app.get("/")
def read_root():
    return {"message": "FastAPI is running successfully!"}


# ROI Analysis
class LeadRecord(BaseModel):
    email: str
    revenue: Optional[float] = 0.0


class AnalyzeRequest(BaseModel):
    ad_spend: float
    leads: List[LeadRecord]


@app.post("/analyze_roi")
def analyze_roi(request: Optional[AnalyzeRequest] = None):
    # If JSON data is provided
    if request:
        total_revenue = sum(lead.revenue for lead in request.leads)
        roi = total_revenue / request.ad_spend if request.ad_spend > 0 else 0
        return {
            "source": "input",
            "ad_spend": request.ad_spend,
            "total_revenue": total_revenue,
            "roi": round(roi, 2)
        }

    # If no JSON data provided, use cached upload
    if "latest" not in uploaded_data_cache:
        return {"error": "No data provided and no cached upload found."}

    df = uploaded_data_cache["latest"]
    if not {"email", "revenue"}.issubset(df.columns):
        return {"error": "Cached data missing required columns: email, revenue."}

    # Use placeholder ad spend until integrated with UI
    ad_spend = 1000.0
    total_revenue = df["revenue"].sum()
    roi = total_revenue / ad_spend if ad_spend > 0 else 0

    return {
        "source": "cache",
        "ad_spend": ad_spend,
        "total_revenue": total_revenue,
        "roi": round(roi, 2)
    }


# Lead Matching
class LeadMatchRequest(BaseModel):
    ads_leads: List[str]
    crm_leads: List[str]


@app.post("/match_leads")
def match_leads(request: LeadMatchRequest):
    matches = []
    for ad_email in request.ads_leads:
        for crm_email in request.crm_leads:
            ratio = SequenceMatcher(None, ad_email.lower(), crm_email.lower()).ratio()
            if ratio > 0.8:
                matches.append({
                    "ad_email": ad_email,
                    "crm_email": crm_email,
                    "match_score": round(ratio, 2)
