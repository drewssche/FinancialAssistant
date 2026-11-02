import io
import subprocess
from types import SimpleNamespace

import pytest
from PIL import Image
from receipt_ocr.worker import assemble_lines, validate_image
from receipt_ocr import server


def picture(size=(100,100), fmt='PNG'):
    stream=io.BytesIO();Image.new('RGB',size).save(stream,format=fmt);return stream.getvalue()


def test_image_limits_and_real_format_validation():
    validate_image(picture())
    for data in [b'not an image', picture((3700,100)), picture((2100,2100)), picture(fmt='GIF')]:
        with pytest.raises(Exception):validate_image(data)


def test_boxes_preserve_duplicate_rows_and_join_price_quantity_total():
    box=lambda x,y:[[x,y],[x+15,y],[x+15,y+10],[x,y+10]]
    assert assemble_lines([box(50,20),box(0,0),box(0,20),box(0,40)],['x1.000','Товар','3.00','Товар'])=='Товар\n3.00 x1.000\nТовар'


def test_native_failure_and_timeout_are_recoverable(monkeypatch):
    monkeypatch.setattr(server.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=-11,stdout=b''))
    assert server.recognize(b'photo')[0]==503
    def timeout(*args,**kwargs):raise subprocess.TimeoutExpired('worker',45)
    monkeypatch.setattr(server.subprocess,'run',timeout)
    assert server.recognize(b'photo')[0]==504
    monkeypatch.setattr(server.subprocess,'run',lambda *a,**kw:SimpleNamespace(returncode=0,stdout=b'{"text":"ok"}'))
    assert server.recognize(b'photo')==(200,{'text':'ok'})


def test_busy_worker_does_not_block_healthcheck_and_slot_is_released(monkeypatch):
    import threading
    import urllib.request
    import urllib.error
    entered, finish = threading.Event(), threading.Event()
    def work(raw):
        entered.set()
        assert finish.wait(5)
        return 200, {'text':'done'}
    monkeypatch.setattr(server,'recognize',work)
    http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    threading.Thread(target=http.serve_forever,daemon=True).start()
    url=f'http://127.0.0.1:{http.server_port}'
    def post():
        with urllib.request.urlopen(url+'/recognize',data=b'photo',timeout=5) as response:
            assert response.status==200
    task=threading.Thread(target=post);task.start()
    try:
        assert entered.wait(2)
        with urllib.request.urlopen(url+'/ready',timeout=2) as response:assert response.status==200
        with pytest.raises(urllib.error.HTTPError) as error:urllib.request.urlopen(url+'/recognize',data=b'other',timeout=2)
        assert error.value.code==429
    finally:
        finish.set();task.join(5);http.shutdown();http.server_close()
    assert not server.SLOT.locked()
