from pydantic import BaseModel, EmailStr
from typing import Optional, List, Any
from datetime import datetime


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    engagement_id: Optional[str] = None

class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    engagement_id: Optional[str] = None
    created_at: str


# ── Engagements ───────────────────────────────────────────────────────────────

class EngagementCreate(BaseModel):
    client_name: str
    client_email: EmailStr
    company: str
    industry: str
    deadline: str  # ISO date string YYYY-MM-DD

class EngagementOut(BaseModel):
    id: str
    consultant_id: str
    client_id: str
    client_name: str
    client_email: str
    company: str
    industry: str
    deadline: str
    onboarding_complete: bool
    status: str  # pending | analysing | complete
    brief_json: Optional[str] = None
    created_at: str
    temp_password: Optional[str] = None   # returned once on creation if email failed
    email_sent: Optional[bool] = None

class EngagementListItem(BaseModel):
    id: str
    company: str
    client_name: str
    industry: str
    deadline: str
    onboarding_complete: bool
    status: str
    upload_summary: dict  # {category: bool}


# ── Onboarding ────────────────────────────────────────────────────────────────

class OnboardingChatMessage(BaseModel):
    message: str

class OnboardingChatResponse(BaseModel):
    reply: str
    is_complete: bool
    next_question: Optional[str] = None

class OnboardingStatusResponse(BaseModel):
    is_complete: bool
    answers_count: int


# ── Uploads ───────────────────────────────────────────────────────────────────

DOCUMENT_CATEGORIES = [
    "financial_report",
    "business_plan",
    "market_view",
    "fact_finding",
    "value_proposition",
    "pricing_structure",
    "market_research",
]

CATEGORY_LABELS = {
    "financial_report": "Financial Report",
    "business_plan": "Business Plan",
    "market_view": "Market View",
    "fact_finding": "Fact Finding",
    "value_proposition": "Value Proposition",
    "pricing_structure": "Pricing Structure",
    "market_research": "Market Research",
}

class UploadOut(BaseModel):
    id: str
    engagement_id: str
    category: str
    filename: str
    drive_file_id: str
    status: str  # processing | ready | error
    uploaded_at: str

class ChecklistStatus(BaseModel):
    engagement_id: str
    categories: dict  # {category: {uploaded: bool, files: list}}
    all_complete: bool


# ── Analysis ──────────────────────────────────────────────────────────────────

class BriefSection(BaseModel):
    title: str
    content: str
    sources: List[str] = []

class AnalysedSummary(BaseModel):
    engagement_id: str
    executive_summary: str
    sections: List[BriefSection]
    strategic_recommendations: str
    generated_at: str
