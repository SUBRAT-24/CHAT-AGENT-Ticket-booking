"""Authentication API router."""

from fastapi import APIRouter, HTTPException, status
from app.models.schemas import UserCreate, UserLogin, UserInDB, UserResponse, TokenResponse, UserRole
from app.core.security import get_password_hash, verify_password, create_access_token
from app.database.connection import get_collection

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse)
async def register(user_data: UserCreate):
    """Register a new user."""
    users_col = get_collection("users")

    # Check if email already exists
    existing = await users_col.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = UserInDB(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
    )

    await users_col.insert_one(user.dict())

    # Generate token
    access_token = create_access_token(
        data={"sub": user.user_id, "role": user.role.value}
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            user_id=user.user_id,
            email=user.email,
            full_name=user.full_name,
            phone=user.phone,
            role=user.role.value,
            preferred_language=user.preferred_language,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """Login with email and password."""
    users_col = get_collection("users")

    user = await users_col.find_one({"email": credentials.email})
    if not user or not verify_password(credentials.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    access_token = create_access_token(
        data={"sub": user["user_id"], "role": user.get("role", "user")}
    )

    return TokenResponse(
        access_token=access_token,
        user=UserResponse(
            user_id=user["user_id"],
            email=user["email"],
            full_name=user["full_name"],
            phone=user.get("phone"),
            role=user.get("role", "user"),
            preferred_language=user.get("preferred_language", "en"),
        ),
    )


@router.post("/admin/create")
async def create_admin(user_data: UserCreate):
    """Create an admin user (should be protected in production)."""
    users_col = get_collection("users")

    existing = await users_col.find_one({"email": user_data.email})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = UserInDB(
        email=user_data.email,
        hashed_password=get_password_hash(user_data.password),
        full_name=user_data.full_name,
        phone=user_data.phone,
        role=UserRole.ADMIN,
    )

    await users_col.insert_one(user.dict())

    return {"message": "Admin user created successfully", "user_id": user.user_id}
