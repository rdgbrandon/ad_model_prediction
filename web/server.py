"""Local-only experiment runner, Python standard library; no shell execution."""
import json
import mimetypes
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/'web'
COMMANDS={
    'audit':['sases_eval/ceiling_audit.py','sases_eval/consensus_audit.py','sases_eval/mechanism_audit.py','web/export_data.py'],
    'rebuild':['sases_eval/build_dataset.py','sases_eval/ceiling_audit.py','sases_eval/consensus_audit.py','sases_eval/mechanism_audit.py','web/export_data.py'],
    'full':['sases_eval/build_dataset.py','sases_eval/theory_audit.py','sases_eval/report_theory_audit.py',
            'sases_eval/mechanism_audit.py','sases_eval/report_mechanism.py','sases_eval/ceiling_audit.py','sases_eval/consensus_audit.py','web/export_data.py']}
DOWNLOADS={
    'consensus.json':ROOT/'sases_eval/consensus/results.json',
    'consensus-protocol.md':ROOT/'sases_eval/CONSENSUS_PROTOCOL.md',
    'ceiling.csv':ROOT/'sases_eval/ceiling/rows.csv',
    'ceiling.json':ROOT/'sases_eval/ceiling/results.json',
    'mechanism.csv':ROOT/'sases_eval/mechanism/ablations.csv',
    'report.pdf':ROOT/'sases_eval/mechanism/sases_mechanism_checked.pdf',
    'protocol.md':ROOT/'sases_eval/CEILING_PROTOCOL.md'}
LOCK=threading.Lock()
JOB=dict(state='idle',logs=[],step=0,total=0)


def execute(kind,job_id):
    try:
        for i,script in enumerate(COMMANDS[kind]):
            with LOCK:JOB.update(step=i+1,label=script)
            with subprocess.Popen([sys.executable,'-u',str(ROOT/script)],cwd=str(ROOT),
                                  stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                  encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)) as proc:
                timer=threading.Timer(1800,proc.kill);timer.start()
                try:
                    for line in proc.stdout:
                        with LOCK:JOB['logs']=(JOB['logs']+[line.rstrip()])[-500:]
                    code=proc.wait()
                finally:timer.cancel()
                if code:raise RuntimeError(f'{script} exited with code {code}. Last published dashboard retained.')
        with LOCK:JOB.update(state='complete',finished=time.time())
    except Exception as exc:
        with LOCK:JOB.update(state='failed',error=str(exc),finished=time.time())


class Handler(BaseHTTPRequestHandler):
    def reply(self,code,payload):
        raw=json.dumps(payload).encode();self.send_response(code)
        self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(raw)))
        self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(raw)

    def local(self):
        return self.headers.get('Host') in (f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}')

    def do_GET(self):
        if not self.local():return self.reply(403,{'error':'Local host required'})
        path=urlparse(self.path).path
        if path=='/api/status':
            with LOCK:result=dict(JOB)
            return self.reply(200,result)
        static={'/':'index.html','/app.js':'app.js','/styles.css':'styles.css','/data/snapshot.json':'data/snapshot.json'}
        file=WEB/static[path] if path in static else None
        if path.startswith('/download/'):
            file=DOWNLOADS.get(path[len('/download/'):])
        if file is None or not file.is_file():return self.reply(404,{'error':'Not found'})
        raw=file.read_bytes();self.send_response(200)
        self.send_header('Content-Type',mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
        self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'")
        self.end_headers();self.wfile.write(raw)

    def do_POST(self):
        origin=self.headers.get('Origin')
        if not self.local() or origin not in (None,f'http://{self.headers.get("Host")}'):
            return self.reply(403,{'error':'Same-origin local requests only'})
        if self.headers.get('X-Lab-Request')!='1':return self.reply(403,{'error':'Missing request header'})
        if self.path!='/api/run':return self.reply(404,{'error':'Not found'})
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=1024:raise ValueError('Invalid request size')
            kind=json.loads(self.rfile.read(size)).get('kind')
            if kind not in COMMANDS:raise ValueError('Unknown run type')
        except (ValueError,AttributeError,TypeError) as exc:return self.reply(400,{'error':str(exc)})
        with LOCK:
            if JOB['state']=='running':return self.reply(409,{'error':'A run is already in progress'})
            JOB.clear();JOB.update(id=uuid.uuid4().hex,kind=kind,state='running',logs=[],step=0,
                                   total=len(COMMANDS[kind]),started=time.time())
            job_id=JOB['id']
        threading.Thread(target=execute,args=(kind,job_id),daemon=True).start()
        self.reply(202,{'id':job_id})

    def log_message(self,*args):pass


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765);args=parser.parse_args()
    server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
    print(f'Capillary Lab: http://127.0.0.1:{args.port}',flush=True)
    server.serve_forever()
