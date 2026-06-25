# src/core/models.py
from dataclasses import dataclass, asdict
from typing import Optional, List
import json

@dataclass
class RawData:
    domain: str
    whois_age_days: Optional[int] = None
    ahrefs_dr: Optional[float] = None
    archive_snapshot_count: Optional[int] = None
    blacklist_status: Optional[str] = None      # "SAFE", "MALWARE", "SOCIAL_ENGINEERING", "UNKNOWN"
    blacklist_reason: Optional[str] = None       # Explication si blacklisté

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
    level: str          # "GREEN", "YELLOW", "RED"
    reasons: List[str]

    def to_dict(self):
        return asdict(self)

@dataclass
class Result:
    domain: str
    raw: RawData
    scores: Scores
    danger: Danger
    explanation: Optional[str] = None

    def to_dict(self):
        return {
            "domain": self.domain,
            "raw": self.raw.to_dict(),
            "scores": self.scores.to_dict(),
            "danger": self.danger.to_dict(),
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
            explanation=d.get("explanation")
        )