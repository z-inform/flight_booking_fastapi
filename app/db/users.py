from sqlmodel import *
import uuid
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(SQLModel, table=True):
    """Database model for User accounts"""
    __tablename__ = "users"

    id: int = Field(
        default=None, primary_key=True, description="Primary key ID"
    )
    login: str = Field(
        index=True,
        unique=True,
        min_length=3,
        max_length=50,
        description="Unique user login/username",
    )
    email: str = Field(unique=True, index=True, description="User's email address")

    hashed_password: str = Field(min_length=1, description="Hashed password")

    def verify_password(self, plain_password: str) -> bool:
        """Verify a plain password against the stored hash"""
        return pwd_context.verify(plain_password, self.hashed_password)

class OpenUser(SQLModel):
    id: int
    login: str
    email: str

class UserCreate(SQLModel):
    """Model for creating a new user (includes password)"""

    login: str = Field(min_length=3, max_length=50)
    email: str
    password: str = Field(description="Plaintext password to be hashed")

    def create_hashed(self) -> "User":
        """Create a User instance with hashed password"""
        return User(
            login=self.login,
            email=self.email,
            hashed_password=pwd_context.hash(self.password),
        )

class TokenData(SQLModel):
    username: str
