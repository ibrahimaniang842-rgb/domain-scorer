import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.pipeline.cache import clear_cache
from src.pipeline.orchestrator import score_domain

logger = logging.getLogger(__name__)

DOMAIN_PATTERN = re.compile(
    r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
)

app = FastAPI(title="Domain Scorer", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def normalize_domain(domain: str) -> str:
    value = domain.strip().lower()
    if value.startswith(("http://", "https://")):
        value = urlparse(value).netloc
    if value.startswith("www."):
        value = value[4:]
    return value.rstrip("/.")


def is_valid_domain(domain: str) -> bool:
    return bool(DOMAIN_PATTERN.match(domain))


class ToxicityResponse(BaseModel):
    score: int = Field(ge=0, le=100)
    level: str
    reasons: List[str]


class NicheShiftResponse(BaseModel):
    history: List[Dict[str, Any]] = Field(default_factory=list)
    shift_detected: bool = False
    shift_message: str = ""
    confidence: int = Field(default=0, ge=0, le=100)
    analysis_status: str = "UNKNOWN"


class ScoreResponse(BaseModel):
    domain: str
    seo_score: float = Field(ge=0, le=100)
    monetization_score: float = Field(ge=0, le=100)
    danger_level: str
    danger_reasons: List[str]
    toxicity: ToxicityResponse
    niche_shift: Optional[NicheShiftResponse] = None
    data_quality: str = "COMPLETE"
    fetch_errors: Dict[str, str] = Field(default_factory=dict)
    raw_data: Dict[str, Any]


class BatchRequest(BaseModel):
    domains: List[str] = Field(..., min_length=1, max_length=50)

    @field_validator("domains")
    @classmethod
    def validate_domains_not_empty(cls, values: List[str]) -> List[str]:
        cleaned = [d.strip() for d in values if d and d.strip()]
        if not cleaned:
            raise ValueError("La liste de domaines ne peut pas être vide")
        return cleaned


class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    domain: Optional[str] = None


class BatchResultItem(BaseModel):
    domain: str
    seo_score: Optional[float] = None
    monetization_score: Optional[float] = None
    danger_level: str
    danger_reasons: List[str]
    toxicity: ToxicityResponse
    niche_shift: Optional[NicheShiftResponse] = None
    data_quality: str = "FAILED"
    fetch_errors: Dict[str, str] = Field(default_factory=dict)
    raw_data: Dict[str, Any] = Field(default_factory=dict)


class BatchResponse(BaseModel):
    results: List[BatchResultItem]


def _build_score_response(result) -> ScoreResponse:
    niche = result.raw.niche_shift or {}
    return ScoreResponse(
        domain=result.domain,
        seo_score=result.scores.seo,
        monetization_score=result.scores.monetization,
        danger_level=result.danger.level,
        danger_reasons=result.danger.reasons,
        toxicity=ToxicityResponse(**result.toxicity.to_dict()),
        niche_shift=NicheShiftResponse(**niche) if niche else None,
        data_quality=result.raw.data_quality,
        fetch_errors=result.raw.fetch_errors,
        raw_data=result.raw.to_dict(),
    )


def _error_batch_item(domain: str, reason: str) -> BatchResultItem:
    return BatchResultItem(
        domain=domain,
        seo_score=None,
        monetization_score=None,
        danger_level="ERROR",
        danger_reasons=[reason],
        toxicity=ToxicityResponse(score=0, level="UNKNOWN", reasons=[]),
        niche_shift=None,
        data_quality="FAILED",
        fetch_errors={"pipeline": reason},
        raw_data={},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content=ErrorResponse(
            error="validation_error",
            detail=str(exc.errors()),
        ).model_dump(),
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(error="http_error", detail=str(exc.detail)).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error on %s: %s", request.url.path, exc)
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="service_unavailable",
            detail="Une erreur temporaire est survenue. Réessayez dans quelques instants.",
        ).model_dump(),
    )


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0"}


@app.delete("/cache")
async def purge_cache(domain: Optional[str] = Query(default=None)):
    await clear_cache(domain)
    return {"status": "ok", "cleared": domain or "all"}


@app.get("/score", response_model=ScoreResponse)
async def get_score(domain: str = Query(..., min_length=1, max_length=253)):
    normalized = normalize_domain(domain)
    if not is_valid_domain(normalized):
        raise HTTPException(status_code=400, detail="Domaine invalide")

    try:
        result = await score_domain(normalized)
        return _build_score_response(result)
    except Exception as exc:
        logger.exception("Score failed for %s", normalized)
        return JSONResponse(
            status_code=503,
            content=ErrorResponse(
                error="score_failed",
                detail=str(exc),
                domain=normalized,
            ).model_dump(),
        )


@app.post("/batch-score", response_model=BatchResponse)
async def batch_score(request: BatchRequest, deep_scan: bool = False):
    results: List[BatchResultItem] = []

    for raw_domain in request.domains:
        normalized = normalize_domain(raw_domain)
        if not is_valid_domain(normalized):
            results.append(_error_batch_item(normalized, "Domaine invalide"))
            continue

        try:
            result = await score_domain(normalized, use_archive=deep_scan)
            payload = _build_score_response(result)
            results.append(
                BatchResultItem(
                    domain=payload.domain,
                    seo_score=payload.seo_score,
                    monetization_score=payload.monetization_score,
                    danger_level=payload.danger_level,
                    danger_reasons=payload.danger_reasons,
                    toxicity=payload.toxicity,
                    niche_shift=payload.niche_shift,
                    data_quality=payload.data_quality,
                    fetch_errors=payload.fetch_errors,
                    raw_data=payload.raw_data,
                )
            )
        except Exception as exc:
            logger.exception("Batch score failed for %s", normalized)
            results.append(_error_batch_item(normalized, str(exc)))

    return BatchResponse(results=results)
