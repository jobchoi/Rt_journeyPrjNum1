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
