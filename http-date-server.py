import os
import sys
import shlex
import urllib
import pathlib
import requests
import subprocess
import tornado.web
import tornado.gen
import tornado.ioloop
from pwd import getpwnam

listen_port = os.environ["WGET_DATE_SERVER_PORT"]

pathlib.Path("smallenv/bin").mkdir(parents=True, exist_ok=True)

if not os.path.isfile("smallenv/bin/ash"):
    r = requests.get("https://www.busybox.net/downloads/binaries/1.30.0-i686/busybox")
    with open('smallenv/busybox', 'wb') as f:
        f.write(r.content)
    os.chmod("smallenv/busybox", 0o755)
    subprocess.Popen(['smallenv/busybox', '--install', "smallenv/bin"], stdout=subprocess.PIPE)

def get_date(params):
    r_out, w_out = os.pipe()
    r_err, w_err = os.pipe()
    pid = os.fork()
    if pid:
        # this is the parent process... do whatever needs to be done as the parent
        os.close(w_out)
        os.close(w_err)
        r1 = os.fdopen(r_out,encoding="utf8")
        r2 = os.fdopen(r_err,encoding="utf8")
        exit_status = os.waitpid(pid,0)
        out = r1.read()
        err = r2.read()
        code = 200 if exit_status[1] == 0 else 400
        if err != "":
            code = 400
        return code ,  out + err
    else:
        if os.getuid() == 0:
            nuid,ngid = getpwnam('nobody')[2:4]
            os.chdir("smallenv")
            os.chroot(".")
            os.chdir("/")
            os.setgid(nuid) # Important! Set GID first! See comments for details.
            os.setuid(ngid)
        w1 = os.fdopen(w_out, "w",encoding="utf8")
        w2 = os.fdopen(w_err, "w",encoding="utf8")
        sys.stdout = w1
        sys.stderr = w2
        sparams = shlex.split(params)
        if sparams == None:
            sparams = []
        os.dup2(w_out,1)
        os.dup2(w_err,2)
        os.execv("/bin/date" ,["date"]+ sparams)
        #subprocess.Popen(["/bin/date"] + sparams , stdin=subprocess.PIPE,stdout=w1,stderr=w2).communicate()
        #sys.exit(0)

date_args=[
	"%%",
	"%a",
	"%A",
	"%b",
	"%B",
	"%c",
	"%C",
	"%d",
	"%D",
	"%e",
	"%F",
	"%g",
	"%G",
	"%h",
	"%H",
	"%I",
	"%j",
	"%k",
	"%l",
	"%m",
	"%M",
	"%n",
	"%N",
	"%p",
	"%P",
	"%q",
	"%r",
	"%R",
	"%s",
	"%S",
	"%t",
	"%T",
	"%u",
	"%U",
	"%V",
	"%w",
	"%W",
	"%x",
	"%X",
	"%y",
	"%Y",
	"%z",
	"%:",
	"%Z"
]
        
class actionHandler(tornado.web.RequestHandler):
    def __init__(self, *args, **kwargs):
        super(actionHandler, self).__init__(*args, **kwargs)
    def initialize(self):
        for a in date_args:
            if a in self.request.uri:
                print(self.request.uri)
                self.request.uri = self.request.uri.replace(a,a.replace("%","%25"))
    def prepare(self):
        self.set_header("Content-Type", "text/plain")
    def set_default_headers(self, *args, **kwargs):
        return
    async def head(self, *args, **kwargs):
        self.write("")
    async def get(self, *args, **kwargs):
        params = urllib.parse.unquote(self.request.uri[1:])
        code, ret = get_date(params)
        self.set_status(200)
        self.write(ret)
        self.finish()

if __name__ == '__main__':
    app = tornado.web.Application(handlers=[
        (r"(.*)", actionHandler),
    ])
    server = tornado.httpserver.HTTPServer(app, ssl_options=None)
    server.listen(listen_port,"0.0.0.0")
    print("Done. Start serving http(s) on " + "0.0.0.0"+ ":" + str(listen_port))
    tornado.ioloop.IOLoop.current().start()
