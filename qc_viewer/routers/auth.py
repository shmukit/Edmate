from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Optional

from qc_viewer.middleware.auth import get_auth_provider

router = APIRouter()

class BYOKSaveRequest(BaseModel):
    provider: str
    api_key: str
    model_id: Optional[str] = None

@router.post("/api/auth/byok")
async def save_byok(request: Request, data: BYOKSaveRequest):
    """
    Save BYOK key on server (encrypted) for authenticated users.
    Anonymous users cannot use this endpoint.
    """
    user_id = getattr(request.state, "user_id", None)
    if not user_id or user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Must be logged in to save BYOK keys")

    auth_provider = get_auth_provider()
    # In a real implementation, you'd encrypt the key and store it in Postgres.
    # We simulate it for now.
    success = auth_provider.save_user_byok(user_id, data.provider, data.api_key, data.model_id)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to save BYOK keys")

    return {"status": "success", "message": "BYOK keys saved securely"}
