# --------------------------------------------------
# routes/google_routes.py
# --------------------------------------------------
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from typing import Optional, List
import os
import requests
import sys
import traceback

router = APIRouter()
print("✅ google_routes.py loaded successfully", file=sys.stderr)

from main import google_auth_cache

# Import database helpers from settings_routes
try:
    from routes.settings_routes import get_api_key
except Exception as e:
    print(f"⚠️  Could not import settings helpers: {e}", file=sys.stderr)


@router.get("/ads_summary")
def get_ads_summary(
    customer_id: str = Query("6207912456", description="Google Ads Customer ID"),
    date_range: str = Query("LAST_7_DAYS", description="Date range for report"),
    ad_spend: Optional[float] = Query(None, description="Ad spend for ROI calculation"),
    total_revenue: Optional[float] = Query(None, description="Total revenue from ads")
):
    # --------------------------------------------------
    # Step 1: Verify tokens (memory or DB)
    # --------------------------------------------------
    token = google_auth_cache.get("latest")

    # If memory cache is empty, try to load from DB
    if not token:
        try:
            refresh_token = get_api_key("google_ads_refresh")
            access_token = get_api_key("google_ads_access")

            if refresh_token and access_token:
                token = {"access_token": access_token, "refresh_token": refresh_token}
                google_auth_cache["latest"] = token
                print("✅ Google Ads tokens loaded from DB", file=sys.stderr)
            else:
                return JSONResponse(
                    status_code=401,
                    content={"error": "No Google tokens found. Please authorize first at /auth/login."}
                )
        except Exception as e:
            print(f"⚠️  Error retrieving tokens from DB: {e}", file=sys.stderr)
            return JSONResponse(
                status_code=500,
                content={"error": "Failed to load Google tokens from database."}
            )

    access_token = token.get("access_token")
    if not access_token:
        return JSONResponse(status_code=401, content={"error": "Access token missing or invalid."})

    # --------------------------------------------------
    # Step 2: Prepare API request
    # --------------------------------------------------
    login_customer_id = os.getenv("GOOGLE_MCC_ID", "6207912456")  # your manager ID

    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
        "login-customer-id": login_customer_id,  # <--- key addition
        "Content-Type": "application/json"
    }

    query = {
        "query": f"""
            SELECT
              customer.descriptive_name,
              segments.date,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.conversions
            FROM customer
            WHERE segments.date DURING {date_range}
            ORDER BY segments.date DESC
        """
    }

    # use the CLIENT (child) account id here — not the MCC id
    url = f"https://googleads.googleapis.com/v17/customers/{customer_id}/googleAds:searchStream"


    # --------------------------------------------------
    # Step 3: Parse & Compute Metrics
    # --------------------------------------------------
    data = response.json()
    results: List[dict] = []
    total_impressions = 0
    total_clicks = 0
    total_cost = 0
    total_conversions = 0

    for chunk in data:
        for row in chunk.get("results", []):
            impressions = row["metrics"].get("impressions", 0)
            clicks = row["metrics"].get("clicks", 0)
            cost_micros = row["metrics"].get("cost_micros", 0)
            conversions = row["metrics"].get("conversions", 0)
            spend_usd = round(cost_micros / 1_000_000, 2)
            date = row["segments"].get("date")

            ctr = round((clicks / impressions) * 100, 2) if impressions else 0
            cpc = round((spend_usd / clicks), 2) if clicks else 0
            cpm = round((spend_usd / impressions * 1000), 2) if impressions else 0

            total_impressions += impressions
            total_clicks += clicks
            total_cost += spend_usd
            total_conversions += conversions

            results.append({
                "date": date,
                "impressions": impressions,
                "clicks": clicks,
                "ctr": ctr,
                "cpc": cpc,
                "cpm": cpm,
                "conversions": conversions,
                "spend_usd": spend_usd
            })

    total_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions else 0
    total_cpc = round((total_cost / total_clicks), 2) if total_clicks else 0
    total_cpm = round((total_cost / total_impressions * 1000), 2) if total_impressions else 0
    total_roas = round(total_revenue / ad_spend, 2) if ad_spend and total_revenue and ad_spend > 0 else None

    summary = {
        "impressions": total_impressions,
        "clicks": total_clicks,
        "ctr": total_ctr,
        "cpc": total_cpc,
        "cpm": total_cpm,
        "spend_usd": round(total_cost, 2),
        "conversions": total_conversions,
        "roas": total_roas
    }

    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "summary": summary,
            "records": results[:25],
            "meta": {
                "customer_id": customer_id,
                "date_range": date_range,
                "ad_spend": ad_spend,
                "total_revenue": total_revenue
            }
        }
    )
