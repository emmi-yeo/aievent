from fastapi import APIRouter, Depends, HTTPException, status

from models.schemas import LoginRequest, RegisterRequest, TokenResponse, UserOut
from gcloud.sheets import get_user_by_email, create_user, init_tabs
from auth.utils import hash_password, verify_password, create_access_token, get_current_user

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=201)
async def register(body: RegisterRequest):
    """Register a new consultant account."""
    init_tabs()
    existing = get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    hashed = hash_password(body.password)
    user = create_user(
        email=body.email,
        hashed_password=hashed,
        name=body.name,
        role="consultant",
    )
    return UserOut(**user)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Login for both consultants and clients."""
    user = get_user_by_email(body.email)
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    token = create_access_token({
        "sub": user["id"],
        "role": user["role"],
        "engagement_id": user.get("engagement_id", ""),
    })
    return TokenResponse(
        access_token=token,
        role=user["role"],
        engagement_id=user.get("engagement_id") or None,
    )


@router.get("/me", response_model=UserOut)
async def me(user: dict = Depends(get_current_user)):
    """Return the currently authenticated user."""
    return UserOut(**user)
