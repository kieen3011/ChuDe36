"""Simulation endpoint dung request-scoped service."""

from fastapi import APIRouter, Request, Response

from web_api.schemas import (
    CanonicalErrorResponse,
    SimulationRunRequest,
    SimulationRunResponse,
)
from web_api.services.simulation_service import SimulationService


router = APIRouter(prefix="/api/simulations")


@router.post(
    "/run",
    response_model=SimulationRunResponse,
    responses={
        400: {"model": CanonicalErrorResponse},
        413: {"model": CanonicalErrorResponse},
        422: {"model": CanonicalErrorResponse},
        500: {"model": CanonicalErrorResponse},
    },
)
def run_simulation_endpoint(
    payload: SimulationRunRequest,
    request: Request,
    response: Response,
) -> dict:
    """Chay synchronous core trong worker thread cua FastAPI."""
    response.headers["Cache-Control"] = "no-store"
    return SimulationService().run(payload, request.state.request_id)
