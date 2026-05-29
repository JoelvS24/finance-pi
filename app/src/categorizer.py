"""Apply categorization rules to uncategorized transactions."""
from __future__ import annotations

import re

from src.db import db_session
from src.models import Transaction, Rule


def categorize_uncategorized() -> int:
    """Walk uncategorized transactions and apply the first matching rule.

    Lower priority value = checked first. Returns count updated.
    """
    updated = 0
    with db_session() as s:
        rules = (
            s.query(Rule)
            .filter(Rule.enabled == True)
            .order_by(Rule.priority.asc())
            .all()
        )
        compiled = [
            (
                r,
                re.compile(r.description_re, re.IGNORECASE) if r.description_re else None,
                re.compile(r.counterparty_re, re.IGNORECASE) if r.counterparty_re else None,
            )
            for r in rules
        ]

        txs = s.query(Transaction).filter(Transaction.category_id.is_(None)).all()
        for tx in txs:
            for rule, desc_re, cp_re in compiled:
                if desc_re and not desc_re.search(tx.description or ""):
                    continue
                if cp_re and not cp_re.search(tx.counterparty_name or ""):
                    continue
                if rule.iban_eq and rule.iban_eq != tx.counterparty_iban:
                    continue
                if rule.amount_min is not None and tx.amount < rule.amount_min:
                    continue
                if rule.amount_max is not None and tx.amount > rule.amount_max:
                    continue
                if rule.account_id is not None and rule.account_id != tx.account_id:
                    continue
                tx.category_id = rule.category_id
                tx.rule_id = rule.id
                updated += 1
                break
    return updated
