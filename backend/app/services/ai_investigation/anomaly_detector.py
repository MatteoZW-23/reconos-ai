import numpy as np
from sklearn.ensemble import IsolationForest
from decimal import Decimal
from sqlalchemy.orm import Session
from app.models.transaction import NormalizedTransaction
from app.schemas.ai import AnomalyResult
from app.utils.decimal_math import to_decimal

class AnomalyDetector:
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination

    def scan_transactions(self, db: Session, organization_id: str, batch_id: str | None = None) -> list[AnomalyResult]:
        query = db.query(NormalizedTransaction).filter(
            NormalizedTransaction.organization_id == organization_id
        )
        if batch_id:
            query = query.filter(NormalizedTransaction.batch_id == batch_id)

        transactions = query.all()
        groups = {}
        for tx in transactions:
            groups.setdefault((tx.financial_account_id, tx.currency), []).append(tx)
        results = []
        for group in groups.values():
            results.extend(self._scan_group(group))
        db.commit()
        return results

    def _scan_group(self, transactions: list[NormalizedTransaction]) -> list[AnomalyResult]:
        # Compare amounts only within the same account and currency.
        # If very few transactions, use purely statistical heuristic
        if len(transactions) < 5:
            results = []
            amounts = [float(tx.amount) for tx in transactions]
            mean_amt = np.mean(amounts) if amounts else 0.0
            std_amt = np.std(amounts) if len(amounts) > 1 else 1.0

            for tx in transactions:
                amt = float(tx.amount)
                reasons = []
                score = 0.0
                if std_amt > 0 and (amt - mean_amt) / std_amt > 2.0:
                    reasons.append("Amount significantly above average for this account")
                    score = min(0.9, 0.5 + float((amt - mean_amt) / (3 * std_amt)))

                if tx.transaction_date.hour < 6 or tx.transaction_date.hour > 21:
                    reasons.append(f"Off-hours transaction recorded at {tx.transaction_date.strftime('%H:%M')}")
                    score = max(score, 0.6)

                is_anom = score >= 0.5
                tx.anomaly_score = score
                tx.anomaly_flag = is_anom
                tx.anomaly_reasons = reasons
                results.append(AnomalyResult(
                    transaction_id=tx.id,
                    anomaly_score=score,
                    is_anomaly=is_anom,
                    reasons=reasons
                ))
            return results

        # Multi-feature vector extraction
        # Features: [log(amount + 1), hour, day_of_week, fee_ratio]
        feature_matrix = []
        for tx in transactions:
            amt = max(0.01, float(tx.amount))
            fee = float(tx.fee_amount) if tx.fee_amount else 0.0
            fee_ratio = fee / amt if amt > 0 else 0.0
            feature_matrix.append([
                np.log1p(amt),
                tx.transaction_date.hour,
                tx.transaction_date.weekday(),
                fee_ratio
            ])

        X = np.array(feature_matrix)

        # Fit Isolation Forest
        model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100
        )
        model.fit(X)
        decision_scores = model.decision_function(X) # lower means more anomalous

        # Normalize score to 0.0 - 1.0 (1.0 = highly anomalous)
        min_s = float(decision_scores.min())
        max_s = float(decision_scores.max())
        span = (max_s - min_s) if max_s != min_s else 1.0

        results = []
        amounts = [float(tx.amount) for tx in transactions]
        mean_amt = float(np.mean(amounts))
        std_amt = float(np.std(amounts)) if len(amounts) > 1 else 1.0

        for idx, tx in enumerate(transactions):
            raw_s = float(decision_scores[idx])
            # Invert so higher = more anomalous
            norm_score = round(1.0 - ((raw_s - min_s) / span), 4)

            reasons = []
            amt = float(tx.amount)

            if std_amt > 0 and (amt - mean_amt) / std_amt >= 2.5:
                reasons.append(f"Statistical outlier: Amount {tx.currency} {amt:,.2f} is > 2.5 standard deviations above mean ({tx.currency} {mean_amt:,.2f})")

            if tx.transaction_date.hour < 5 or tx.transaction_date.hour > 22:
                reasons.append(f"Unusual timestamp: processed at {tx.transaction_date.strftime('%H:%M')} outside normal operating hours")

            fee = float(tx.fee_amount) if tx.fee_amount else 0.0
            if amt > 0 and (fee / amt) > 0.08:
                reasons.append(f"High fee proportion: fee of {tx.currency} {fee:,.2f} represents {((fee/amt)*100):.1f}% of transaction value")

            if norm_score >= 0.70 and not reasons:
                reasons.append("Multi-factor structural irregularity detected by isolation tree analysis")

            is_anomaly = norm_score >= 0.70 or len(reasons) >= 2

            tx.anomaly_score = norm_score
            tx.anomaly_flag = is_anomaly
            tx.anomaly_reasons = reasons

            results.append(AnomalyResult(
                transaction_id=tx.id,
                anomaly_score=norm_score,
                is_anomaly=is_anomaly,
                reasons=reasons
            ))

        return results
