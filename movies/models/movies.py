from sqlmodel import SQLModel, Field


class Movie(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str = Field(index=True)
    year: int | None = Field(default=None)
    runtime: int = Field(default=0)
    rating: float | None = Field(default=None)
    director: str = Field(index=True)
    overview: str | None = Field(default=None)
