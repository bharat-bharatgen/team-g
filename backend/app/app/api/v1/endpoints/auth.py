from fastapi import APIRouter, HTTPException, status
from app.api.v1.schemas.user import UserSignup, UserSignin, UserResponse, TokenResponse, TokenWithUserResponse
from app.models.user import UserModel
from app.core.security import hash_password, verify_password, create_access_token
from app.dependencies import get_database

router = APIRouter()


@router.post("/signup", response_model=TokenResponse)
async def signup(body: UserSignup):
    db = await get_database()

    existing = await db.users.find_one({"phone_number": body.phone_number})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Phone number already registered")

    user = UserModel(
        name=body.name,
        phone_number=body.phone_number,
        hashed_password=hash_password(body.password),
    )
    result = await db.users.insert_one(user.model_dump())
    token = create_access_token(str(result.inserted_id))
    return TokenResponse(access_token=token)


@router.post("/signin", response_model=TokenWithUserResponse)
async def signin(body: UserSignin):
    db = await get_database()

    user = await db.users.find_one({"phone_number": body.phone_number})
    if not user or not verify_password(body.password, user["hashed_password"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid phone number or password")

    token = create_access_token(str(user["_id"]))
    user_response = UserResponse(
        id=str(user["_id"]),
        name=user["name"],
        phone_number=user["phone_number"],
    )
    return TokenWithUserResponse(access_token=token, user=user_response)

