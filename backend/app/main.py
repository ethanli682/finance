import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import router
from .config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

if "example.com" in settings.sec_user_agent:
    logging.getLogger(__name__).warning(
        "SEC_USER_AGENT is still the placeholder. Set it to 'YourApp you@yourdomain.com' "
        "or SEC may block requests."
    )

app = FastAPI(title="Finance API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.include_router(router)
