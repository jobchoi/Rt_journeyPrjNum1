import io
import json
from datetime import datetime

from openpyxl import Workbook
from uuid import uuid4

from test_simple_finance import headers


def test_bank_import_preview_and_confirmation(client):
    auth = headers(client)
    marker = uuid4().hex
    csv = f'날짜,입금,출금,잔액,내용,메모,번호\n2050-01-01T12:30:00,100,,100,{marker},메모,\n2050-01-01T12:30:00,100,,100,{marker},메모,\n2050-01-02,,50,50,출금,,{marker}\n잘못된날짜,1,,1,오류,,\n'
    files = {'file': ('synthetic.csv', csv.encode(), 'text/csv')}
    mapping = json.dumps({'date': 0, 'deposit': 1, 'withdrawal': 2, 'balance': 3, 'description': 4, 'memo': 5, 'reference': 6})
    route = '/api/finance/bank-import/'
    assert client.post(route + 'columns', files=files).status_code == 401
    assert client.post(route + 'columns', headers=auth, files=files).json()['columns'][0] == '날짜'
    def show():
        return client.post(route + 'preview', headers=auth, files=files, data={'mapping': mapping}).json()['rows']
    assert [row['status'] for row in show()] == ['new', 'duplicate', 'new', 'error']
    assert client.post(route + 'confirm', headers=auth, files=files, data={'mapping': mapping, 'selected': '[2,4,5]'}).status_code == 400
    assert client.post(route + 'confirm', headers=auth, files=files, data={'mapping': mapping, 'selected': '[2,4]'}).json() == {'imported': 2}
    assert [row['status'] for row in show()] == ['duplicate', 'duplicate', 'duplicate', 'error']
    assert client.post(route + 'confirm', headers=auth, files=files, data={'mapping': mapping, 'selected': '[4]'}).status_code == 409
    assert client.post(route + 'columns', headers=auth, files={'file': ('x.xlsx', b'fake')}).status_code == 400
    assert client.post(route + 'preview', headers=auth, files=files, data={'mapping': '{}'}).status_code == 400


def test_xlsx_sheet_header_and_confirmation(client):
    book = Workbook()
    first = book.active
    first.title = '안내'
    first.append(['안내'])
    ws = book.create_sheet('거래')
    ws.merge_cells('A1:E1')
    ws['A1'] = '합성 거래내역'
    ws.append([])
    ws.append(['날짜', '입금', '출금', '잔액', '내용'])
    ws.append([datetime(2051, 2, 3, 10, 30), 1200, None, 1200, '합성 입금'])
    ws.append([])
    ws.append([datetime(2051, 2, 4), None, 200, 1000, '합성 출금'])
    stream = io.BytesIO()
    book.save(stream)
    files = {'file': ('synthetic.xlsx', stream.getvalue(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
    auth = headers(client)
    route = '/api/finance/bank-import/'
    result = client.post(route + 'columns', headers=auth, files=files, data={'sheet': '거래'}).json()
    assert result['header_row'] == 3
    assert result['columns'][:5] == ['날짜', '입금', '출금', '잔액', '내용']
    assert result['sheets'] == ['안내', '거래']
    mapping = json.dumps({'date': 0, 'deposit': 1, 'withdrawal': 2, 'balance': 3, 'description': 4})
    data = {'sheet': '거래', 'header_row': '3', 'mapping': mapping}
    rows = client.post(route + 'preview', headers=auth, files=files, data=data).json()['rows']
    assert [(r['row'], r['status'], r['amount']) for r in rows] == [(4, 'new', 1200), (6, 'new', 200)]
    assert rows[0]['date'] == '2051-02-03T10:30:00'
    assert client.post(route + 'confirm', headers=auth, files=files, data={**data, 'selected': '[4,6]'}).json() == {'imported': 2}
    assert client.post(route + 'columns', headers=auth, files=files, data={'sheet': '없는 시트'}).status_code == 400
    assert client.post(route + 'columns', headers=auth, files=files, data={'sheet': '거래', 'header_row': '2'}).status_code == 400


def test_xlsx_formula_rejected(client):
    book = Workbook()
    book.active.append(['날짜', '입금', '내용'])
    book.active.append(['2050-01-01', '=1+1', '합성'])
    stream = io.BytesIO()
    book.save(stream)
    response = client.post('/api/finance/bank-import/columns', headers=headers(client), files={'file': ('synthetic.xlsx', stream.getvalue())})
    assert response.status_code == 400


def test_kakao_preset_synthetic_xlsx(client):
    book = Workbook()
    ws = book.active
    ws.title = '카카오뱅크 거래내역'
    ws.append(['합성 안내'])
    for _ in range(9):
        ws.append([])
    ws.append([None, '거래일시', '구분', '거래금액', '거래 후 잔액', '거래구분', '내용', '메모'])
    ws.append([None, '2051.02.03 10:30:00', '입금', '1,200', '1,200', '이체', '가상 입금', '가상 메모'])
    ws.append([None, '2051.02.04 10:30:00', '출금', '-200', '1,000', '이체', '가상 출금', None])
    ws.append([None, '2051.02.04 10:30:00', '출금', '-200', '1,000', '이체', '가상 출금', None])
    ws.append([None, '2051-02-05 10:30:00', '입금', '-100', '900', '이체', '오류', None])
    stream = io.BytesIO()
    book.save(stream)
    files = {'file': ('synthetic.xlsx', stream.getvalue())}
    route, auth = '/api/finance/bank-import/', headers(client)
    columns = client.post(route + 'columns', headers=auth, files=files).json()
    assert columns['header_row'] == 11
    mapping = columns['preset']
    assert mapping == {'date': 1, 'direction': 2, 'amount': 3, 'balance': 4, 'description': 6, 'memo': 7}
    data = {'mapping': json.dumps(mapping)}
    rows = client.post(route + 'preview', headers=auth, files=files, data=data).json()['rows']
    assert [(r['status'], r.get('type'), r.get('amount')) for r in rows] == [
        ('new', 'income', 1200), ('new', 'expense', 200),
        ('duplicate', 'expense', 200), ('error', None, None)]
    assert client.post(route + 'confirm', headers=auth, files=files, data={**data, 'selected': '[12,13]'}).json() == {'imported': 2}
    assert [r['status'] for r in client.post(route + 'preview', headers=auth, files=files, data=data).json()['rows']] == ['duplicate', 'duplicate', 'duplicate', 'error']


def test_zero_amount_rows_are_skipped_and_cannot_be_confirmed(client):
    auth = headers(client)
    route = '/api/finance/bank-import/'
    cases = [
        ('날짜,입금,출금,내용\n2052-01-01,0,,합성\n2052-01-02,,0,합성\n2052-01-03,,,합성\n',
         {'date': 0, 'deposit': 1, 'withdrawal': 2, 'description': 3}, [2, 3]),
        ('거래일시,구분,거래금액,거래 후 잔액,내용,메모\n2052.01.01 00:00:00,입금,0,0,합성,\n2052.01.02 00:00:00,출금,-0,0,합성,\n',
         {'date': 0, 'direction': 1, 'amount': 2, 'balance': 3, 'description': 4, 'memo': 5}, [2, 3]),
    ]
    for content, mapping, skipped in cases:
        files = {'file': ('synthetic.csv', content.encode(), 'text/csv')}
        data = {'mapping': json.dumps(mapping)}
        rows = client.post(route + 'preview', headers=auth, files=files, data=data).json()['rows']
        assert [r['row'] for r in rows if r['status'] == 'skipped'] == skipped
        assert all(r['reason'] == '건너뜀(금액 0)' for r in rows if r['status'] == 'skipped')
        if len(rows) > len(skipped):
            assert rows[-1]['status'] == 'error'
        response = client.post(route + 'confirm', headers=auth, files=files, data={**data, 'selected': json.dumps(skipped)})
        assert response.status_code == 400


def test_password_encrypted_xlsx_guidance(client):
    auth = headers(client)
    encrypted = b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + bytes(504)
    files = {'file': ('synthetic.xlsx', encrypted)}
    data = {'mapping': json.dumps({'date': 0, 'deposit': 1, 'description': 2}), 'selected': '[2]'}
    for action in ('columns', 'preview', 'confirm'):
        response = client.post('/api/finance/bank-import/' + action,
                               headers=auth, files=files, data=data)
        assert response.status_code == 400
        assert response.json()['detail'] == '암호가 걸린 파일입니다. 은행 앱에서 암호 없이 내보내거나 엑셀에서 암호를 해제한 뒤 올려 주세요.'
    damaged = client.post('/api/finance/bank-import/columns', headers=auth,
                          files={'file': ('damaged.xlsx', b'not an xlsx')})
    assert damaged.status_code == 400
    assert damaged.json()['detail'] == '손상되었거나 지원하지 않는 XLSX 파일입니다.'
