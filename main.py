from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel
from typing import List, Optional
from difflib import SequenceMatcher
import pandas as pd
import io
import os
from openai import OpenAI
from fastapi.responses import RedirectResponse, JSONResponse
from requests_oauthlib import OAuth2Session
import requests
import sys, traceback

app = FastAPI()

# --- Settings Routes Import (with diagnostic logging) ---
try:
    from routes import settings_routes
    print("✅ settings_routes imported successfully", file=sys.stderr)
    app.include_router(
        settings_routes.router,
        prefix="/settings",
        tags=["Settings"]
    )
except Exception as e:
    print("⚠️  SETTINGS ROUTE IMPORT FAILED:", e, file=sys.stderr)
    traceback.print_exc()

# --- In-Memory Storage ---
uploaded_data_cache = {}  # For uploaded files
google_auth_cache = {}    # For Google OAuth tokens

# --- Initialize OpenAI ---
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --- Root Endpoint ---
@app.get("/")
def read_root():
    return {"message": "FastAPI is running successfully!"}


# --- ROI Analysis ---
class LeadRecord(BaseModel):
    email: str
    revenue: Optional[float] = 0.0


class AnalyzeRequest(BaseModel):
    ad_spend: float
    leads: List[LeadRecord]


@app.post("/analyze_roi")
def analyze_roi(request: Optional[AnalyzeRequest] = None):
    if request:
        total_revenue = sum(lead.revenue for lead in request.leads)
        roi = total_revenue / request.ad_spend if request.ad_spend > 0 else 0
        return {
            "source": "input",
            "ad_spend": request.ad_spend,
            "total_revenue": total_revenue,
            "roi": round(roi, 2)
        }

    if "latest" not in uploaded_data_cache:
        return {"error": "No data provided and no cached upload found."}

    df = uploaded_data_cache["latest"]
    if not {"email", "revenue"}.issubset(df.columns):
        return {"error": "Cached data missing required columns: email, revenue."}

    ad_spend = 1000.0
    total_revenue = df["revenue"].sum()
    roi = total_revenue / ad_spend if ad_spend > 0 else 0

    return {
        "source": "cache",
        "ad_spend": ad_spend,
        "total_revenue": total_revenue,
        "roi": round(roi, 2)
    }


# --- Lead Matching ---
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
                })
    return {"matches": matches, "total_matches": len(matches)}


# --- ROI Reporting ---
@app.get("/report")
def get_report(ad_spend: float, total_revenue: float):
    if ad_spend <= 0:
        return {"error": "Ad spend must be greater than zero."}
    roi = total_revenue / ad_spend
    summary = f"Your total revenue of ${total_revenue:,.2f} generated an ROI of {roi:.2f}x based on an ad spend of ${ad_spend:,.2f}."
    return {
        "ad_spend": ad_spend,
        "total_revenue": total_revenue,
        "roi": round(roi, 2),
        "summary": summary
    }


# --- File Upload + Cache ---
@app.post("/upload_data")
async def upload_data(file: UploadFile = File(...)):
    filename = file.filename.lower()

    if filename.endswith(".csv"):
        df = pd.read_csv(io.BytesIO(await file.read()))
    elif filename.endswith((".xls", ".xlsx")):
        df = pd.read_excel(io.BytesIO(await file.read()))
    elif filename.endswith(".json"):
        df = pd.read_json(io.BytesIO(await file.read()))
    else:
        return {"error": "Unsupported file type. Please upload CSV, Excel, or JSON."}

    uploaded_data_cache["latest"] = df

    return {
        "filename": filename,
        "rows": len(df),
        "columns": list(df.columns),
        "message": "File uploaded and cached successfully."
    }


@app.get("/cache_status")
def cache_status():
    if "latest" not in uploaded_data_cache:
        return {"cached": False, "message": "No data currently cached."}

    df = uploaded_data_cache["latest"]
    return {
        "cached": True,
        "rows": len(df),
        "columns": list(df.columns)
    }


# --- AI Summary Generation (OpenAI) ---
@app.get("/generate_summary")
def generate_summary(ad_spend: float = 0.0, total_revenue: float = 0.0):
    if ad_spend <= 0 or total_revenue <= 0:
        return {"error": "Both ad_spend and total_revenue must be greater than zero."}

    roi = total_revenue / ad_spend
    gain = total_revenue - ad_spend

    prompt = (
        f"You are a marketing analytics assistant. Write a professional one-paragraph summary "
        f"explaining campaign performance based on these metrics:\n"
        f"- Ad Spend: ${ad_spend:,.2f}\n"
        f"- Revenue: ${total_revenue:,.2f}\n"
        f"- ROI: {roi:.2f}x\n"
        f"- Profit: ${gain:,.2f}\n"
        f"Use a confident, client-friendly tone with clear business insight."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a marketing performance analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7
        )
        ai_summary = response.choices[0].message.content.strip()
    except Exception as e:
        return {"error": str(e)}

    return {
        "ad_spend": ad_spend,
        "total_revenue": total_revenue,
        "roi": round(roi, 2),
        "profit": round(gain, 2),
        "summary": ai_summary
    }


# --- Google OAuth Configuration ---
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
REDIRECT_URI = "https://sparkdata-app-mceg3.ondigitalocean.app/auth/callback"

AUTHORIZATION_BASE_URL = "https://accounts.google.com/o/oauth2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"

SCOPE = [
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/analytics.readonly"
]


@app.get("/auth/login")
def google_login():
    """Redirect user to Google for authorization"""
    oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=REDIRECT_URI, scope=SCOPE)
    authorization_url, state = oauth.authorization_url(
        AUTHORIZATION_BASE_URL,
        access_type="offline",
        prompt="consent"
    )
    return RedirectResponse(authorization_url)


@app.get("/auth/callback")
def google_callback(code: str):
    """Handle the OAuth redirect from Google and cache tokens"""
    oauth = OAuth2Session(GOOGLE_CLIENT_ID, redirect_uri=REDIRECT_URI)
    token = oauth.fetch_token(
        TOKEN_URL,
        client_secret=GOOGLE_CLIENT_SECRET,
        code=code
    )

    google_auth_cache["latest"] = token

    safe_token = {
        "access_token": token.get("access_token", "")[:12] + "...",
        "refresh_token": token.get("refresh_token", "")[:12] + "...",
        "scope": token.get("scope"),
        "expires_in": token.get("expires_in"),
        "token_type": token.get("token_type"),
    }

    return JSONResponse({
        "status": "success",
        "message": "Google authorization complete. Tokens cached in memory.",
        "token_preview": safe_token
    })


@app.get("/google/account_info")
def get_google_account_info():
    """Fetch and display connected Google account details"""
    if "latest" not in google_auth_cache:
        return {"error": "No Google tokens found. Please authorize first at /auth/login."}

    token = google_auth_cache["latest"]
    access_token = token.get("access_token")

    if not access_token:
        return {"error": "Access token missing or invalid."}

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get("https://www.googleapis.com/oauth2/v2/userinfo", headers=headers)

    if response.status_code != 200:
        return {"error": "Failed to retrieve account info.", "details": response.text}

    user_info = response.json()

    return {
        "status": "success",
        "account": {
            "name": user_info.get("name"),
            "email": user_info.get("email"),
            "verified_email": user_info.get("verified_email"),
            "picture": user_info.get("picture")
        }
    }


@app.get("/google/ads_summary")
def get_ads_summary(customer_id: str = "6207912456"):
    """Fetch recent ad spend summary from Google Ads API"""
    if "latest" not in google_auth_cache:
        return {"error": "No Google tokens found. Please authorize first at /auth/login."}

    token = google_auth_cache["latest"]
    access_token = token.get("access_token")
    if not access_token:
        return {"error": "Access token missing or invalid."}

    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "Content-Type": "application/json"
    }

    query = {
        "query": """
            SELECT
              customer.descriptive_name,
              segments.date,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros
            FROM customer
            WHERE segments.date DURING LAST_7_DAYS
            ORDER BY segments.date DESC
        """
    }

    url = f"https://googleads.googleapis.com/v17/customers/{customer_id}/googleAds:searchStream"
    response = requests.post(url, headers=headers, json=query)

    if response.status_code != 200:
        return {"error": "Failed to retrieve Ads data.", "details": response.text}

    data = response.json()

    results = []
    for chunk in data:
        for row in chunk.get("results", []):
            results.append({
                "date": row["segments"]["date"],
                "impressions": row["metrics"]["impressions"],
                "clicks": row["metrics"]["clicks"],
                "spend_usd": round(row["metrics"]["cost_micros"] / 1_000_000, 2)
            })

    return {"status": "success", "records": results[:10]}
