from sqlmodel import SQLModel, Field
from datetime import datetime


class Rating(SQLModel, table=True):
    user_id: int = Field(primary_key=True)
    movie_id: int = Field(primary_key=True)
    rating: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
