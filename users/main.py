from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

from sqlmodel import select
import requests

from jose import jwt, JWTError
from passlib.hash import bcrypt
from datetime import datetime, timedelta

from databases.db import wait_for_db, SessionDep
from models.users import User
from models.ratings import Rating

from collections import defaultdict

app = FastAPI()

SECRET_KEY = "spiderman"
ALGORITHM = "HS256"


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=30)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")


@app.on_event("startup")
def on_startup():
    wait_for_db()


@app.post("/register",  description="Регистрация пользователя")
async def register(username: str, password: str, session: SessionDep):
    user = session.exec(select(User).where(User.username == username)).first()
    if user:
        raise HTTPException(status_code=400, detail="Username already exists")
    hashed_password = bcrypt.hash(password)
    new_user = User(username=username, password_hash=hashed_password)
    session.add(new_user)
    session.commit()
    return {"message": "User is created"}


@app.post("/token", description="Токен пользователя")
async def token(session: SessionDep, form_data: OAuth2PasswordRequestForm = Depends()):
    user = session.exec(select(User).where(User.username == form_data.username)).first()
    if not user or not bcrypt.verify(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/rate", description="Оценить фильм по названию по 10 балльной шкале")
async def rate_movie(movie_title: str, rating: int, session: SessionDep, current_user: str = Depends(get_current_user)):
    user_id = session.exec(select(User).where(User.username == current_user)).first().id
    movie_id = requests.get(f"http://movies:8000/movies/get_movie_id/{movie_title}").json()["id"]
    existing_rating = session.exec(select(Rating).where(Rating.user_id == user_id, Rating.movie_id == movie_id)).first()
    if existing_rating:
        existing_rating.rating = rating
        existing_rating.created_at = datetime.utcnow()
    else:
        new_rating = Rating(
            user_id=user_id,
            movie_id=movie_id,
            rating=rating
        )
        session.add(new_rating)
    session.commit()

    return {"message": f"Rating is saved for '{movie_title}' by {current_user}."}


@app.get("/scored_genres", description="Средние оценки по жанрам")
async def get_genres(session: SessionDep, current_user: str = Depends(get_current_user)):
    user_id = session.exec(select(User.id).where(User.username == current_user)).first()
    ratings = session.exec(select(Rating).where(Rating.user_id == user_id)).all()

    genres_ratings = defaultdict(list)
    for rating in ratings:
        movie_id = rating.movie_id
        score = rating.rating
        movie_genres = requests.get(f"http://movies:8000/movies/{movie_id}/genres").json()
        for genre in movie_genres:
            genres_ratings[genre].append(score)
    genre_avg = {genre: sum(scores) / len(scores) for genre, scores in genres_ratings.items()}
    return defaultdict(lambda: 0, genre_avg)


@app.get("/scored_stars", description="Средние оценки по актёрам")
async def get_stars(session: SessionDep, current_user: str = Depends(get_current_user)):
    user_id = session.exec(select(User.id).where(User.username == current_user)).first()
    ratings = session.exec(select(Rating).where(Rating.user_id == user_id)).all()

    stars_ratings = defaultdict(list)
    for rating in ratings:
        movie_id = rating.movie_id
        score = rating.rating
        movie_stars = requests.get(f"http://movies:8000/movies/{movie_id}/stars").json()
        for star in movie_stars:
            stars_ratings[star].append(score)
    star_avg = {star: sum(scores) / len(scores) for star, scores in stars_ratings.items()}
    return defaultdict(lambda: 0, star_avg)


@app.get("/scored_directors", description="Средние оценки по режиссерам")
async def get_directors(session: SessionDep, current_user: str = Depends(get_current_user)):
    user_id = session.exec(select(User.id).where(User.username == current_user)).first()
    ratings = session.exec(select(Rating).where(Rating.user_id == user_id)).all()

    directors_ratings = defaultdict(list)
    for rating in ratings:
        movie_id = rating.movie_id
        score = rating.rating
        movie_director = requests.get(f"http://movies:8000/movies/{movie_id}").json()["director"]
        directors_ratings[movie_director].append(score)
    director_avg = {director: sum(scores) / len(scores) for director, scores in directors_ratings.items()}
    return defaultdict(lambda: 0, director_avg)


@app.get("/recommendations", description="Получить рекомендации, основанные на просмотренных фильмах")
async def get_recommendations(session: SessionDep, N: int = 5,  current_user: str = Depends(get_current_user)):
    user_id = session.exec(select(User).where(User.username == current_user)).first().id
    directors = await get_directors(session, current_user)
    stars = await get_stars(session, current_user)
    genres = await get_genres(session, current_user)

    cnt = len(requests.get(f"http://movies:8000/movies/filter").json())
    ratings = session.exec(select(Rating).where(Rating.user_id == user_id)).all()
    rated_movies_id = session.exec(select(Rating.movie_id).where(Rating.user_id == user_id)).all()

    scores = [r.rating for r in ratings]
    mean = sum(scores) / len(scores)

    scored_movies = []

    for movie_id in range(1, cnt + 1):
        if movie_id in rated_movies_id:
            continue
        score = 0
        movie_info = requests.get(f"http://movies:8000/movies/{movie_id}").json()
        movie_stars = requests.get(f"http://movies:8000/movies/{movie_id}/stars").json()
        movie_genres = requests.get(f"http://movies:8000/movies/{movie_id}/genres").json()
        score += directors[movie_info["director"]] - mean
        for movie_star in movie_stars:
            score += stars[movie_star] - mean
        for movie_genre in movie_genres:
            score += genres[movie_genre] - mean
        scored_movies.append((movie_info["title"], score))

    scored_movies.sort(key=lambda x: x[1], reverse=True)
    rec_movies = [movie[0] for movie in scored_movies[:N]]
    return rec_movies
