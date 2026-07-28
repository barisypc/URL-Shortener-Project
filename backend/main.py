from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from limiter import limiter
from routers import abuse, admin, auth, stats, tags, urls, users

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

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



@app.exception_handler(RequestValidationError)
async def validation_handler(request, exc):
    first = exc.errors()[0]
    field = first["loc"][-1] if first.get("loc") else "input"
    msg = first["msg"]

    if field == "original_url" and "URL" in msg:
        msg = "Please enter a valid URL, e.g. https://example.com"

    return JSONResponse(status_code=422, content={"detail": f"{field}: {msg}"})


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