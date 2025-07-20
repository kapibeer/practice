from fastapi import FastAPI, HTTPException, Query
from databases.db import wait_for_db, SessionDep
from generate_db import generate_movies
from models.movies import Movie
from sqlmodel import SQLModel, select
from models.genres import Genre
from models.stars import Star

app = FastAPI()


@app.on_event("startup")
def on_startup():
    wait_for_db()
    generate_movies()


@app.get("/movies/filter",
         description="Фильтрация фильмов по одному или нескольким параметрам: режиссёр, год, актёр или жанр. "
                     "Поддерживаются множественные значения (например, ?director=...&director=...). "
                     "Если параметры не указаны — возвращаются все фильмы.")
def filter_movies(
        session: SessionDep,
        director: list[str] = Query(default=None),
        year: list[str] = Query(default=None),
        star: list[str] = Query(default=None),
        genre: list[str] = Query(default=None),
):
    query = select(Movie)

    if director:
        query = query.where(Movie.director.in_(director))
    if year:
        query = query.where(Movie.year.in_(year))
    if star:
        query = query.where(
            Movie.id.in_(
                select(Star.movie_id).where(Star.name.in_(star))
            )
        )
    if genre:
        query = query.where(
            Movie.id.in_(
                select(Genre.movie_id).where(Genre.name.in_(genre))
            )
        )
    results = session.exec(query).all()
    return [m.title for m in results]


@app.get("/movies/{movie_id}", description="Возвращает информацию о фильме по его уникальному идентификатору")
async def read_movie(movie_id: int, session: SessionDep) -> Movie:
    movie = session.get(Movie, movie_id)
    if not movie:
        raise HTTPException(status_code=404, detail="Movie not found")
    return movie


@app.get("/movies/{movie_id}/genres",
         description="Возвращает информацию о жанрах фильма по его уникальному идентификатору")
def get_movie_genres(movie_id: int, session: SessionDep):
    genres = session.exec(select(Genre.name).where(Genre.movie_id == movie_id)).all()
    return genres


@app.get("/movies/{movie_id}/stars",
         description="Возвращает информацию об актерах фильма по его уникальному идентификатору")
def get_movie_genres(movie_id: int, session: SessionDep):
    stars = session.exec(select(Star.name).where(Star.movie_id == movie_id)).all()
    return stars


@app.get(
    "/movies/get_movie_id/{movie_title}",
    description="Возвращает список ID фильмов по названию"
)
async def find_movies(movie_title: str, session: SessionDep):
    movies = session.exec(
        select(Movie).where(Movie.title == movie_title)
    ).all()
    if not movies:
        raise HTTPException(status_code=404, detail="Movies not found")
    return {"ids": [movie.id for movie in movies]}


class MovieCreate(SQLModel):
    title: str
    year: int | None = None
    runtime: int = 0
    director: str | None = None
    rating: float | None = None
    overview: str | None = None


@app.post("/movies/create_movie",  description="Добавление фильма в базу данных")
async def create_movie(session: SessionDep,
                       movie: MovieCreate,
                       genres: list[str] = Query(default=None),
                       stars: list[str] = Query(default=None)):
    db_movie = Movie.from_orm(movie)
    session.add(db_movie)
    session.commit()
    session.refresh(db_movie)
    for genre in genres:
        db_genre = Genre(movie_id=db_movie.id, name=genre)
        session.add(db_genre)
    for star in stars:
        db_star = Star(movie_id=db_movie.id, name=star)
        session.add(db_star)
    session.commit()
    return {"message": "Movie is added"}
