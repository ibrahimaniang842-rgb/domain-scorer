# src/core/models.py
from dataclasses import dataclass, asdict
from typing import Optional, List
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

    def to_dict(self):
        return asdict(self)

@dataclass
class Scores:
    seo: float
    monetization: float

    def to_dict(self):
        return asdict(self)

@dataclass
class Danger:
    level: str
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class Toxicity:
    score: int
    level: str
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class Result:
    domain: str
    raw: RawData
    scores: Scores
    danger: Danger
    toxicity: Toxicity
    explanation: Optional[str] = None

    def to_dict(self):
        return {
            "domain": self.domain,
            "raw": self.raw.to_dict(),
            "scores": self.scores.to_dict(),
            "danger": self.danger.to_dict(),
            "toxicity": self.toxicity.to_dict(),
            "explanation": self.explanation
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str)

    @classmethod
    def from_json(cls, data: str) -> "Result":
        d = json.loads(data)
        return cls(
            domain=d["domain"],
            raw=RawData(**d["raw"]),
            scores=Scores(**d["scores"]),
            danger=Danger(**d["danger"]),
            toxicity=Toxicity(**d["toxicity"]),
            explanation=d.get("explanation")
        )