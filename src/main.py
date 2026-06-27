# src/main.py
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import re
from urllib.parse import urlparse
from src.pipeline.orchestrator import score_domain

app = FastAPI(title="Domain Scorer MVP", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def is_valid_domain(domain: str) -> bool:
    pattern = r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$"
    return bool(re.match(pattern, domain.strip().lower()))

def normalize_domain(domain: str) -> str:
    domain = domain.strip().lower()
    if domain.startswith(("http://", "https://")):
        domain = urlparse(domain).netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

class ScoreResponse(BaseModel):
    domain: str
    seo_score: float
    monetization_score: float
    danger_level: str
    danger_reasons: List[str]
    toxicity: dict
    raw_data: dict

class BatchRequest(BaseModel):
    domains: List[str]

@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0"}

@app.get("/score", response_model=ScoreResponse)
async def get_score(domain: str):
    domain = normalize_domain(domain)
    if not is_valid_domain(domain):
        raise HTTPException(status_code=400, detail="Domaine invalide")
    try:
        result = await score_domain(domain)
        return ScoreResponse(
            domain=result.domain,
            seo_score=result.scores.seo,
            monetization_score=result.scores.monetization,
            danger_level=result.danger.level,
            danger_reasons=result.danger.reasons,
            toxicity=result.toxicity.to_dict(),
            raw_data=result.raw.to_dict()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur interne: {str(e)}")

@app.post("/batch-score")
async def batch_score(request: BatchRequest, deep_scan: bool = False):
    results = []
    for domain in request.domains:
        try:
            domain = normalize_domain(domain)
            if not is_valid_domain(domain):
                results.append({
                    "domain": domain,
                    "seo_score": None,
                    "monetization_score": None,
                    "danger_level": "ERROR",
                    "danger_reasons": ["Domaine invalide"],
                    "toxicity": {"score": 0, "level": "UNKNOWN", "reasons": []},
                    "raw_data": {}
                })
                continue
            result = await score_domain(domain, use_archive=deep_scan)
            results.append({
                "domain": result.domain,
                "seo_score": result.scores.seo,
                "monetization_score": result.scores.monetization,
                "danger_level": result.danger.level,
                "danger_reasons": result.danger.reasons,
                "toxicity": result.toxicity.to_dict(),
                "raw_data": result.raw.to_dict()
            })
        except Exception as e:
            results.append({
                "domain": domain,
                "seo_score": None,
                "monetization_score": None,
                "danger_level": "ERROR",
                "danger_reasons": [str(e)],
                "toxicity": {"score": 0, "level": "UNKNOWN", "reasons": []},
                "raw_data": {}
            })
    return {"results": results}