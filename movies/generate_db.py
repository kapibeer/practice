import pandas as pd
from models.movies import Movie
from models.genres import Genre
from models.stars import Star
from databases.db import engine
from sqlmodel import  Session


def generate_movies():
    db = pd.read_csv("imdb_top_1000.csv")

    with Session(engine) as session:
        for index, row in db.iterrows():
            if row["Released_Year"] == "PG":
                row["Released_Year"] = 1995
            db_movie = Movie(title=row["Series_Title"],
                             year=int(row["Released_Year"]),
                             runtime=int(row["Runtime"][:-4]),
                             rating=float(row["IMDB_Rating"]),
                             director=row["Director"],
                             overview=row["Overview"]
                             )
            session.add(db_movie)
            session.commit()
            session.refresh(db_movie)
            genres = row["Genre"].split(", ")
            for genre in genres:
                db_genre = Genre(movie_id=db_movie.id, name=genre)
                session.add(db_genre)
            for star in [row["Star1"], row["Star2"], row["Star3"], row["Star4"]]:
                db_star = Star(movie_id=db_movie.id, name=star)
                session.add(db_star)
            session.commit()