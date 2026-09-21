import json
import threading
import unittest
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from server import Handler,ThreadingHTTPServer


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.base='http://127.0.0.1:'+str(cls.server.server_port)
        threading.Thread(target=cls.server.serve_forever,daemon=True).start()

    @classmethod
    def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()

    def status(self,path,body=None,headers=None):
        r=Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers=headers or {})
        try:
            with urlopen(r) as f:return f.status,f.read()
        except HTTPError as e:return e.code,e.read()

    def test_published_data_and_download(self):
        code,raw=self.status('/data/snapshot.json');self.assertEqual(code,200)
        self.assertEqual(json.loads(raw)['dataset']['windows'],448)
        self.assertEqual(self.status('/download/ceiling.csv')[0],200)

    def test_workspace_not_exposed(self):
        for path in ('/../.venv/pyvenv.cfg','/.venv/pyvenv.cfg','/download/../../web/server.py'):
            self.assertEqual(self.status(path)[0],404)

    def test_arbitrary_command_rejected(self):
        self.assertEqual(self.status('/api/run',{'kind':'python arbitrary.py'},{'X-Lab-Request':'1'})[0],400)

    def test_cross_origin_job_rejected(self):
        self.assertEqual(self.status('/api/run',{'kind':'audit'},{'X-Lab-Request':'1','Origin':'https://example.com'})[0],403)
        self.assertEqual(self.status('/api/run',{'kind':'audit'})[0],403)


if __name__=='__main__':unittest.main()
