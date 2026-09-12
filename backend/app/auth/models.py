from typing import Literal

from pydantic import BaseModel, EmailStr, Field

Role = Literal["teacher", "student"]


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    name: str = Field(min_length=1)
    role: Role


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: Role


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut
