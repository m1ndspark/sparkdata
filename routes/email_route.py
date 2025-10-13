from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from services.email_service import send_recap_email

router = APIRouter()

class RecapRequest(BaseModel):
    to_email: str
    first_name: str
    recap_body: str

@router.post("/send-recap")
def send_recap(request: RecapRequest):
    """
    Trigger a recap email using SendGrid.
    """
    try:
        send_recap_email(
            to_email=request.to_email,
            first_name=request.first_name,
            recap_body=request.recap_body
        )
        return {"status": "success", "message": "Recap email sent successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
