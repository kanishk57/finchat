"""
Settings API routes module
Handles all settings-related endpoints
"""

from fastapi import APIRouter
from pydantic import BaseModel
from config import (
    DEFAULT_THRESHOLD, DEFAULT_TEMPERATURE, 
    INITIAL_K as CONFIG_INITIAL_K,
    FINAL_TOP_K as CONFIG_FINAL_TOP_K
)

router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

class RAGSettings(BaseModel):
    top_k: int = 5
    threshold: float = 0.05
    temperature: float = 0.2

# Global settings instance
current_settings = RAGSettings(
    top_k=CONFIG_FINAL_TOP_K,
    threshold=DEFAULT_THRESHOLD,
    temperature=DEFAULT_TEMPERATURE
)

@router.get("")
async def get_settings():
    """Get current RAG settings"""
    return current_settings

@router.post("")
async def update_settings(settings: RAGSettings):
    """Update RAG settings"""
    global current_settings
    current_settings = settings
    return {"message": "Protocol parameters updated."}