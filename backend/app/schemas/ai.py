from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime
from app.models.ai_insight import InsightType

class AnomalyResult(BaseModel):
    transaction_id: str
    anomaly_score: float
    is_anomaly: bool
    reasons: list[str]

class AnomalyScanResponse(BaseModel):
    scanned_count: int
    anomalies_detected: int
    anomalies: list[AnomalyResult]

class AIInsightResponse(BaseModel):
    id: str
    organization_id: str
    insight_type: InsightType
    severity: str
    title: str
    summary: str
    evidence: dict[str, Any]
    recommendation: str
    is_acknowledged: bool
    created_at: datetime

    class Config:
        from_attributes = True

class InvestigationExplanationResponse(BaseModel):
    transaction_id: str
    amount: str
    reference: Optional[str] = None
    date: str
    plain_language_explanation: str
    root_cause_hypothesis: str
    evidence_points: list[str]
    suggested_investigator_action: str
    confidence: Optional[float] = None
