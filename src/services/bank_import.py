"""CSV bank statement parsing; inputs are held in memory only."""
import csv
import hashlib
import io
import json
from datetime import date, datetime

from openpyxl import load_workbook
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import select

from ..models import FinanceTransaction
from ..schemas import FinanceTransactionCreate

FIELDS = {'date', 'deposit', 'withdrawal', 'balance', 'description', 'memo', 'counterparty', 'reference', 'direction', 'amount'}


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



class BankRows(list):
    """Rows plus original worksheet row numbers for preview and confirmation."""
    def __init__(self, rows, numbers, sheets, sheet, header_row):
        super().__init__(rows)
        self.numbers, self.sheets, self.sheet, self.header_row = numbers, sheets, sheet, header_row


def read_xlsx(content, sheet=None, header_row=None):
    try:
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=False, keep_links=False)
        try:
            if sheet and sheet not in book.sheetnames:
                raise HTTPException(400, '선택한 시트를 찾을 수 없습니다.')
            ws = book[sheet] if sheet else book.worksheets[0]
            if ws.max_row > 5001 or ws.max_column > 100:
                raise HTTPException(400, 'XLSX는 최대 5,001개 행, 100개 열을 지원합니다.')
            rows = []
            for number, cells in enumerate(ws.iter_rows(), 1):
                values = []
                for cell in cells:
                    if cell.data_type == 'f':
                        raise HTTPException(400, '수식이 포함된 XLSX는 지원하지 않습니다.')
                    value = cell.value
                    if isinstance(value, (datetime, date)):
                        value = value.isoformat()
                    elif value is None:
                        value = ''
                    else:
                        value = str(value)
                    values.append(value)
                if any(value.strip() for value in values):
                    rows.append((number, values))
            if not rows:
                raise HTTPException(400, '시트가 비어 있습니다.')
            if header_row is None:
                keywords = ('날짜', '일시', '거래일', '입금', '출금', '내용', '적요', 'date', 'deposit', 'withdrawal', 'description')
                def score(item):
                    return sum(any(word in value.strip().lower() for word in keywords) for value in item[1])
                header_row = max(rows[:100], key=score)[0] if any(score(row) for row in rows[:100]) else rows[0][0]
            header = next((values for number, values in rows if number == header_row), None)
            if header is None:
                raise HTTPException(400, '머리글 행을 찾을 수 없습니다.')
            selected = [(number, values) for number, values in rows if number >= header_row]
            return BankRows([values for _, values in selected], [number for number, _ in selected], book.sheetnames, ws.title, header_row)
        finally:
            book.close()
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(400, '손상되었거나 지원하지 않는 XLSX 파일입니다.') from None

def kakao_preset(columns):
    names = {'date': '거래일시', 'direction': '구분', 'amount': '거래금액',
             'balance': '거래 후 잔액', 'description': '내용', 'memo': '메모'}
    if not all(columns.count(name) == 1 for name in names.values()):
        return {}
    return {field: columns.index(name) for field, name in names.items()}


def preview(rows, mapping, db):
    if set(mapping) - FIELDS or any(not isinstance(v, int) or isinstance(v, bool) or v < 0 or v >= len(rows[0]) for v in mapping.values()):
        raise HTTPException(400, '열 매핑이 올바르지 않습니다.')
    if len(set(mapping.values())) != len(mapping) or not {'date', 'description'} <= mapping.keys() or not (({'deposit', 'withdrawal'} & mapping.keys() and not ({'direction', 'amount'} & mapping.keys())) or ({'direction', 'amount'} <= mapping.keys() and not ({'deposit', 'withdrawal'} & mapping.keys()))):
        raise HTTPException(400, '날짜, 내용 및 입금 또는 출금 열을 서로 다르게 지정하세요.')
    result, seen_refs, seen_keys = [], set(), set()
    for index, row in enumerate(rows[1:], 1):
        number = rows.numbers[index] if isinstance(rows, BankRows) else index + 1
        def value(key):
            return row[mapping[key]].strip() if key in mapping else ''
        try:
            date_text = value('date')
            if 'direction' in mapping:
                try:
                    stamp = datetime.strptime(date_text, '%Y.%m.%d %H:%M:%S')
                except ValueError:
                    stamp = datetime.fromisoformat(date_text)
            else:
                stamp = datetime.fromisoformat(date_text)
            if stamp.tzinfo is not None:
                raise ValueError()
            def money(text):
                if not text:
                    return 0
                text = text.replace(',', '')
                if not text.isdecimal():
                    raise ValueError()
                return int(text)
            if 'direction' in mapping:
                direction, raw_amount = value('direction'), value('amount')
                if direction not in ('입금', '출금') or (raw_amount.startswith('-') and direction != '출금'):
                    raise ValueError()
                amount = money(raw_amount.removeprefix('-'))
                deposit, withdrawal = (amount, 0) if direction == '입금' else (0, amount)
            else:
                deposit, withdrawal = money(value('deposit')), money(value('withdrawal'))
            if deposit == 0 and withdrawal == 0 and (value('amount') if 'direction' in mapping else value('deposit') or value('withdrawal')):
                result.append({'row': number, 'status': 'skipped', 'reason': '건너뜀(금액 0)'})
                continue
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
