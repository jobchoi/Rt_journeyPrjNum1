"""CSV bank statement parsing; inputs are held in memory only."""
import csv
import hashlib
import io
import json
from datetime import datetime
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from ..models import FinanceTransaction
from ..schemas import FinanceTransactionCreate

FIELDS = {'date', 'deposit', 'withdrawal', 'balance', 'description', 'memo', 'counterparty', 'reference'}


def read_csv(content):
    try:
        rows = list(csv.reader(io.StringIO(content.decode('utf-8-sig')), strict=True))
    except (UnicodeDecodeError, csv.Error):
        raise HTTPException(400, 'UTF-8 CSV 형식을 확인하세요.') from None
    if not rows or not rows[0] or len(rows) > 5001 or len(rows[0]) > 100:
        raise HTTPException(400, 'CSV는 헤더와 최대 5,000개 행, 100개 열이 필요합니다.')
    if any(len(row) != len(rows[0]) for row in rows[1:]):
        raise HTTPException(400, 'CSV 행의 열 개수가 일치하지 않습니다.')
    return rows


def preview(rows, mapping, db):
    if set(mapping) - FIELDS or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >= len(rows[0]) for v in mapping.values()):
        raise HTTPException(400, '열 매핑이 올바르지 않습니다.')
    if len(set(mapping.values())) != len(mapping) or not {'date', 'description'} <= mapping.keys() or not ({'deposit', 'withdrawal'} & mapping.keys()):
        raise HTTPException(400, '날짜, 내용 및 입금 또는 출금 열을 서로 다르게 지정하세요.')
    result, seen_refs, seen_keys = [], set(), set()
    for number, row in enumerate(rows[1:], 2):
        def value(key):
            return row[mapping[key]].strip() if key in mapping else ''
        try:
            stamp = datetime.fromisoformat(value('date'))
            if stamp.tzinfo is not None:
                raise ValueError()
            def money(text):
                if not text:
                    return 0
                text = text.replace(',', '')
                if not text.isdecimal():
                    raise ValueError()
                return int(text)
            deposit, withdrawal = money(value('deposit')), money(value('withdrawal'))
            if (deposit > 0) == (withdrawal > 0):
                raise ValueError()
            balance = value('balance')
            if balance:
                balance = str(money(balance))
            description = value('description')
            memo = value('memo')
            combined = description + (' / ' + memo if memo else '')
            reference = value('reference')
            kind, amount = ('income', deposit) if deposit else ('expense', withdrawal)
            FinanceTransactionCreate(transaction_date=stamp.date(), transaction_type=kind, amount=amount,
                counterparty=value('counterparty') or '기존 내역 (미기재)', description=combined,
                external_reference=reference or None)
            key = hashlib.sha256(json.dumps([stamp.isoformat(), kind, amount, balance, description], ensure_ascii=False).encode()).hexdigest()
            prefix = 'bank-' + key + '-'
            matches = list(db.scalars(select(FinanceTransaction).where(
                (FinanceTransaction.external_reference == reference) if reference else
                (FinanceTransaction.external_reference.startswith(prefix)))))
            # Existing manual records do not carry a bank balance: show possible matches conservatively.
            if not reference:
                matches += list(db.scalars(select(FinanceTransaction).where(
                    FinanceTransaction.transaction_date == stamp, FinanceTransaction.transaction_type == kind,
                    FinanceTransaction.amount == amount, FinanceTransaction.description == combined,
                    ~FinanceTransaction.external_reference.startswith('bank-'))))
            duplicate = bool(matches) or (reference in seen_refs if reference else key in seen_keys)
            result.append({'row': number, 'status': 'duplicate' if duplicate else 'new', 'date': stamp.isoformat(),
                'type': kind, 'amount': amount, 'balance': balance, 'description': combined,
                'counterparty': value('counterparty'), 'reference': reference, 'key': key,
                'reason': '거래번호 또는 거래 조건이 일치하는 후보가 있습니다.' if duplicate else ''})
            if reference: seen_refs.add(reference)
            else: seen_keys.add(key)
        except (ValueError, ValidationError, OverflowError):
            result.append({'row': number, 'status': 'error', 'reason': '날짜, 입출금, 잔액 또는 내용 형식을 확인하세요.'})
    return result
