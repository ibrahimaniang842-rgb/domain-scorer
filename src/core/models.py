from dataclasses import dataclass, asdict, field
from typing import Any, Dict, List, Optional
import copy
import json


@dataclass
class RawData:
    domain: str
    whois_age_days: Optional[int] = None
    ahrefs_dr: Optional[float] = None
    archive_exists: Optional[bool] = None
    archive_first_date: Optional[str] = None
    archive_last_date: Optional[str] = None
    archive_status: Optional[str] = None
    blacklist_status: Optional[str] = None
    blacklist_reason: Optional[str] = None
    niche_history: Optional[list] = None
    niche_shift: Optional[dict] = None
    fetch_errors: Dict[str, str] = field(default_factory=dict)
    data_quality: str = "COMPLETE"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Scores:
    seo: float
    monetization: float

    def to_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class Danger:
    level: str
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Toxicity:
    score: int
    level: str
    reasons: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Result:
    domain: str
    raw: RawData
    scores: Scores
    danger: Danger
    toxicity: Toxicity
    explanation: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "domain": self.domain,
            "raw": self.raw.to_dict(),
            "scores": self.scores.to_dict(),
            "danger": self.danger.to_dict(),
            "toxicity": self.toxicity.to_dict(),
            "explanation": self.explanation,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, data: str) -> "Result":
        payload = json.loads(data)
        raw_payload = payload["raw"]
        fetch_errors = raw_payload.pop("fetch_errors", {})
        data_quality = raw_payload.pop("data_quality", "COMPLETE")
        return cls(
            domain=payload["domain"],
            raw=RawData(**raw_payload, fetch_errors=fetch_errors, data_quality=data_quality),
            scores=Scores(**payload["scores"]),
            danger=Danger(**payload["danger"]),
            toxicity=Toxicity(**payload["toxicity"]),
            explanation=payload.get("explanation"),
        )


def clone_result(result: Result) -> Result:
    return copy.deepcopy(result)
