from fastapi import APIRouter

from app.api.routes import auth, categories, health, users
from app.core.config import API_V1_PREFIX

api_router = APIRouter(prefix=API_V1_PREFIX)
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
