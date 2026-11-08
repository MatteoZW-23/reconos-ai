from datetime import timedelta
from decimal import Decimal
from typing import Optional
from itertools import combinations

from app.models.transaction import NormalizedTransaction
from app.models.reconciliation import MatchType
from app.utils.decimal_math import is_amount_within_tolerance, to_decimal

class MatchCandidate:
    def __init__(
        self,
        match_type: MatchType,
        primary_txs: list[NormalizedTransaction],
        secondary_txs: list[NormalizedTransaction],
        confidence_score: Decimal,
        notes: str = ""
    ):
        self.match_type = match_type
        self.primary_txs = primary_txs
        self.secondary_txs = secondary_txs
        self.confidence_score = confidence_score
        self.notes = notes

    @property
    def primary_total(self) -> Decimal:
        return sum((to_decimal(tx.amount) for tx in self.primary_txs), Decimal("0.0000"))

    @property
    def secondary_total(self) -> Decimal:
        return sum((to_decimal(tx.amount) for tx in self.secondary_txs), Decimal("0.0000"))

    @property
    def difference(self) -> Decimal:
        return self.primary_total - self.secondary_total


class ReconciliationRules:
    @staticmethod
    def match_exact_references(
        primary_pool: list[NormalizedTransaction],
        secondary_pool: list[NormalizedTransaction]
    ) -> list[MatchCandidate]:
        """
        Stage 1: Match by exact external reference and identical amount.
        Highest confidence deterministic rule.
        """
        matches = []
        sec_by_ref = {}
        for s in secondary_pool:
            if s.external_reference:
                sec_by_ref.setdefault(s.external_reference.strip().upper(), []).append(s)

        matched_p_ids = set()
        matched_s_ids = set()

        for p in primary_pool:
            if not p.external_reference:
                continue
            ref_key = p.external_reference.strip().upper()
            candidates = sec_by_ref.get(ref_key, [])

            # Filter out already matched
            available = [c for c in candidates if c.id not in matched_s_ids]
            for c in available:
                if p.currency == c.currency and p.transaction_type == c.transaction_type and to_decimal(p.amount) == to_decimal(c.amount):
                    equivalent_primary = [other for other in primary_pool if other.external_reference
                        and other.external_reference.strip().upper() == ref_key
                        and other.currency == c.currency and other.transaction_type == c.transaction_type
                        and to_decimal(other.amount) == to_decimal(c.amount)]
                    equivalent_secondary = [other for other in candidates if other.currency == p.currency
                        and other.transaction_type == p.transaction_type and to_decimal(other.amount) == to_decimal(p.amount)]
                    unique = len(equivalent_primary) == 1 and len(equivalent_secondary) == 1
                    matches.append(MatchCandidate(
                        match_type=MatchType.EXACT_REFERENCE,
                        primary_txs=[p],
                        secondary_txs=[c],
                        confidence_score=Decimal("100.00") if unique else Decimal("80.00"),
                        notes=f"{'Exact' if unique else 'Ambiguous'} reference match: {p.external_reference}"
                    ))
                    matched_p_ids.add(p.id)
                    matched_s_ids.add(c.id)
                    break

        return matches

    @staticmethod
    def match_amount_and_date_tolerance(
        primary_pool: list[NormalizedTransaction],
        secondary_pool: list[NormalizedTransaction],
        tolerance_days: int = 2,
        amount_tolerance_percent: Decimal = Decimal("0.00")
    ) -> list[MatchCandidate]:
        """
        Stage 2: Match by identical amount and date within tolerance_days.
        If unique 1-to-1: high confidence (95%).
        If ambiguous (multiple possible candidates): marked for human review.
        """
        matches = []
        matched_p_ids = set()
        matched_s_ids = set()

        # Build candidate pairs
        candidate_pairs: dict[str, list[NormalizedTransaction]] = {}
        
        for p in primary_pool:
            p_amt = to_decimal(p.amount)
            for s in secondary_pool:
                if p.currency != s.currency or p.transaction_type != s.transaction_type:
                    continue
                s_amt = to_decimal(s.amount)
                
                # Check amount tolerance
                if not is_amount_within_tolerance(p_amt, s_amt, percent_tolerance=amount_tolerance_percent):
                    continue
                
                # Check date tolerance
                days_diff = abs((p.transaction_date.date() - s.transaction_date.date()).days)
                if days_diff <= tolerance_days:
                    candidate_pairs.setdefault(p.id, []).append(s)

        # Separate unambiguous 1-to-1 matches from ambiguous candidates
        for p in primary_pool:
            possible_s = candidate_pairs.get(p.id, [])
            available_s = [s for s in possible_s if s.id not in matched_s_ids]

            if len(available_s) == 1:
                s = available_s[0]
                # Check if s is also uniquely pointing to p
                reverse_matches = [other_p for other_p, s_list in candidate_pairs.items() if s in s_list]
                confidence = Decimal("95.00") if len(reverse_matches) == 1 and to_decimal(p.amount) == to_decimal(s.amount) else Decimal("80.00")
                notes = f"Amount & Date match (date delta: {abs((p.transaction_date.date() - s.transaction_date.date()).days)} days)"
                if len(reverse_matches) > 1:
                    notes += " [Ambiguous: candidate shared by multiple records, pending review]"

                matches.append(MatchCandidate(
                    match_type=MatchType.AMOUNT_DATE_TOLERANCE,
                    primary_txs=[p],
                    secondary_txs=[s],
                    confidence_score=confidence,
                    notes=notes
                ))
                matched_p_ids.add(p.id)
                matched_s_ids.add(s.id)

        return matches

    @staticmethod
    def match_one_to_many(
        primary_pool: list[NormalizedTransaction],
        secondary_pool: list[NormalizedTransaction],
        tolerance_days: int = 3,
        max_group_size: int = 4,
        max_candidates: int = 25
    ) -> list[MatchCandidate]:
        """
        Stage 3: One secondary record (e.g. bulk settlement) matches multiple primary transactions.
        """
        matches = []
        matched_p_ids = set()
        matched_s_ids = set()

        for s in secondary_pool:
            s_amt = to_decimal(s.amount)
            # Find primary records close in date
            window_start = s.transaction_date - timedelta(days=tolerance_days)
            window_end = s.transaction_date + timedelta(days=tolerance_days)
            candidates = [
                p for p in primary_pool
                if p.id not in matched_p_ids and p.currency == s.currency
                and p.transaction_type == s.transaction_type and window_start <= p.transaction_date <= window_end
            ]

            # An unbounded combination search can make an import-sized session
            # unusable. Leave large windows unmatched for manual investigation.
            if len(candidates) > max_candidates:
                continue

            found_group = None
            for r in range(2, min(max_group_size + 1, len(candidates) + 1)):
                for group in combinations(candidates, r):
                    group_sum = sum((to_decimal(tx.amount) for tx in group), Decimal("0.0000"))
                    if group_sum == s_amt:
                        found_group = list(group)
                        break
                if found_group:
                    break

            if found_group:
                matches.append(MatchCandidate(
                    match_type=MatchType.MANY_TO_ONE,
                    primary_txs=found_group,
                    secondary_txs=[s],
                    confidence_score=Decimal("90.00"),
                    notes=f"Many-to-one aggregate suggestion ({len(found_group)} primary records sum to one secondary record)"
                ))
                for p in found_group:
                    matched_p_ids.add(p.id)
                matched_s_ids.add(s.id)

        return matches
