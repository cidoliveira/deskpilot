from datetime import datetime
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field, StringConstraints

from app.models.enums import UserRole

Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=120)]
# E-mails are compared and stored in lower case.
Email = Annotated[EmailStr, AfterValidator(str.lower)]
# Length-based policy (NIST SP 800-63B); the upper bound avoids hashing huge payloads.
Password = Annotated[str, Field(min_length=8, max_length=128)]


class UserRegister(BaseModel):
    """Public self-registration. Always creates a USER; extra fields such as `role` are rejected."""

    model_config = ConfigDict(extra="forbid")

    name: Name
    email: Email
    password: Password


class UserCreate(UserRegister):
    """Account created by an admin, who can choose the role."""

    role: UserRole = UserRole.USER


class UserUpdate(BaseModel):
    """Partial update by an admin. Only the fields sent are changed."""

    model_config = ConfigDict(extra="forbid")

    name: Name | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime
