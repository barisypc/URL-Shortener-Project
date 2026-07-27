from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from limiter import limiter
from routers import abuse, admin, auth, stats, tags, urls, users

Base.metadata.create_all(bind=engine)
app = FastAPI()

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(tags.router)
app.include_router(stats.router)
app.include_router(abuse.router)
app.include_router(admin.router)

# urls.router is included last: it owns the catch-all "GET /{short_code}"
# redirect route, which must never get a chance to shadow a more specific
# route registered above it.
app.include_router(urls.router)