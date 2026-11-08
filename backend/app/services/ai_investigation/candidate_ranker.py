import difflib
from decimal import Decimal
from app.models.transaction import NormalizedTransaction
from app.utils.decimal_math import to_decimal

class CandidateRanker:
    @staticmethod
    def rank_candidates(
        target_tx: NormalizedTransaction,
        candidates: list[NormalizedTransaction]
    ) -> list[dict]:
        """
        Ranks candidate transactions using a weighted multi-signal scoring model:
        1. Reference token similarity (40%)
        2. Amount proximity (30%)
        3. Date proximity (20%)
        4. Description/counterparty text similarity (10%)
        """
        ranked = []
        target_amt = to_decimal(target_tx.amount)

        for cand in candidates:
            cand_amt = to_decimal(cand.amount)
            
            # Amount score
            amt_diff = abs(target_amt - cand_amt)
            if target_amt > Decimal("0.0000"):
                amt_score = max(0.0, 1.0 - float(amt_diff / target_amt))
            else:
                amt_score = 1.0 if amt_diff == 0 else 0.0

            # Date score (1.0 = same day, decays over 7 days)
            days_diff = abs((target_tx.transaction_date.date() - cand.transaction_date.date()).days)
            date_score = max(0.0, 1.0 - (days_diff / 7.0))

            # Reference score
            ref_score = 0.0
            if target_tx.external_reference and cand.external_reference:
                ref1 = target_tx.external_reference.strip().upper()
                ref2 = cand.external_reference.strip().upper()
                ref_score = difflib.SequenceMatcher(None, ref1, ref2).ratio()
            
            # Description score
            desc_score = 0.0
            desc1 = (target_tx.description or target_tx.counterparty_name or "").lower()
            desc2 = (cand.description or cand.counterparty_name or "").lower()
            if desc1 and desc2:
                desc_score = difflib.SequenceMatcher(None, desc1, desc2).ratio()

            total_score = round(
                (0.40 * ref_score) +
                (0.30 * amt_score) +
                (0.20 * date_score) +
                (0.10 * desc_score),
                4
            )

            ranked.append({
                "candidate_id": cand.id,
                "amount": str(cand.amount),
                "currency": cand.currency,
                "date": cand.transaction_date.strftime("%Y-%m-%d"),
                "reference": cand.external_reference,
                "description": cand.description,
                "overall_similarity_score": total_score,
                "score_breakdown": {
                    "reference_similarity": round(ref_score, 2),
                    "amount_match": round(amt_score, 2),
                    "temporal_proximity": round(date_score, 2),
                    "narrative_similarity": round(desc_score, 2)
                }
            })

        ranked.sort(key=lambda x: x["overall_similarity_score"], reverse=True)
        return ranked
