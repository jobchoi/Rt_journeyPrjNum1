import json
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
    assert client.post(route + 'columns', headers=auth, files={'file': ('x.xlsx', b'fake')}).status_code == 415
    assert client.post(route + 'preview', headers=auth, files=files, data={'mapping': '{}'}).status_code == 400
