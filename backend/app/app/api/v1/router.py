from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    cases,
    documents,
    mer,
    pathology,
    risk,
    face_match,
    location_check,
    test_verification,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(documents.router, prefix="/cases", tags=["documents"])
api_router.include_router(mer.router, prefix="/cases", tags=["mer"])
api_router.include_router(pathology.router, prefix="/cases", tags=["pathology"])
api_router.include_router(risk.router, prefix="/cases", tags=["risk"])
api_router.include_router(face_match.router, prefix="/cases", tags=["face_match"])
api_router.include_router(location_check.router, prefix="/cases", tags=["location_check"])
api_router.include_router(test_verification.router, prefix="/cases", tags=["test_verification"])
