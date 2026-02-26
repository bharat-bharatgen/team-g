from pydantic import BaseModel


class UserSignup(BaseModel):
    name: str
    phone_number: str
    password: str


class UserSignin(BaseModel):
    phone_number: str
    password: str


class UserResponse(BaseModel):
    id: str
    name: str
    phone_number: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenWithUserResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse

