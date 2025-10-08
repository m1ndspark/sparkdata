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

# --------------------------------------------------
# Router Initialization
# --------------------------------------------------
router = APIRouter()
print("✅ google_routes.py loaded successfully", file=sys.stderr)

# --------------------------------------------------
# In-memory Google Token Cache (imported from main.py)
# --------------------------------------------------
from main import google_auth_cache


# --------------------------------------------------
# Google Ads Summary Endpoint
# --------------------------------------------------
@router.get("/ads_summary")
def get_ads_summary(
    customer_id: str = Query("6207912456", description="Google Ads Customer ID"),
    date_range: str = Query("LAST_7_DAYS", description="Date range for report (e.g., TODAY, YESTERDAY, LAST_30_DAYS)"),
    ad_spend: Optional[float] = Query(None, description="Ad spend for ROI calculation"),
    total_revenue: Optional[float] = Query(None, description="Revenue generated from ads")
):
    """
    Retrieves and summarizes Google Ads performance data.
    Optional query params: customer_id, date_range, ad_spend, total_revenue.
    Returns key metrics (CTR, CPC, CPM, ROAS) with a unified JSON summary.
    """

    # --------------------------------------------------
    # Step 1: Verify Tokens
    # --------------------------------------------------
    if "latest" not in google_auth_cache:
        return JSONResponse(
            status_code=401,
            content={"error": "No Google tokens found. Please authorize first at /auth/login."}
        )

    token = google_auth_cache["latest"]
    access_token = token.get("access_token")
    if not access_token:
        return JSONResponse(
            status_code=401,
            content={"error": "Access token missing or invalid."}
        )

    # --------------------------------------------------
    # Step 2: Prepare Request
    # --------------------------------------------------
    headers = {
        "Authorization": f"Bearer {access_token}",
        "developer-token": os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN"),
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

    url = f"https://googleads.googleapis.com/v17/customers/{customer_id}/googleAds:searchStream"

    # --------------------------------------------------
    # Step 3: Execute Request
    # --------------------------------------------------
    try:
        response = requests.post(url, headers=headers, json=query)
    except Exception as e:
        traceback.print_exc()
        return JSONResponse(
            status_code=500,
            content={"error": f"Request failed: {str(e)}"}
        )

    if response.status_code != 200:
        return JSONResponse(
            status_code=response.status_code,
            content={"error": "Failed to retrieve Ads data.", "details": response.text}
        )

    # --------------------------------------------------
    # Step 4: Parse & Compute Metrics
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

    # --------------------------------------------------
    # Step 5: Unified Summary JSON (Now with ROAS)
    # --------------------------------------------------
    total_ctr = round((total_clicks / total_impressions) * 100, 2) if total_impressions else 0
    total_cpc = round((total_cost / total_clicks), 2) if total_clicks else 0
    total_cpm = round((total_cost / total_impressions * 1000), 2) if total_impressions else 0

    # If both ad_spend and total_revenue provided, compute real ROAS
    total_roas = (
        round(total_revenue / ad_spend, 2)
        if ad_spend and total_revenue and ad_spend > 0
        else None
    )

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

    # --------------------------------------------------
    # Step 6: Response
    # --------------------------------------------------
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
