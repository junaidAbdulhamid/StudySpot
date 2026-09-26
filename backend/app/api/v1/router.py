from fastapi import APIRouter

from app.api.v1 import (
    buildings,
    campuses,
    favorites,
    health,
    locations,
    predictions,
    preferences,
    users,
)

router = APIRouter()
for module in (health, campuses, buildings, locations, predictions, users, favorites, preferences):
    router.include_router(module.router)
