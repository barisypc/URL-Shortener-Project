#sets up the connection to the database and creates the tables if they don't exist.
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import redis
import os


DATABASE_URL = os.environ.get("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not given. Please check the .env files.")

engine = create_engine(DATABASE_URL) # Gives the engine the database URL to connect to the database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) # Opens and closes the database
Base = declarative_base() #All our tables will inherit from this.

redis_client = redis.Redis(
    host="redis",
    port=6379,
    db=0,
    password=os.environ.get("REDIS_PASSWORD"),
    decode_responses=True,
)