from io import StringIO
import time
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer

import platform, subprocess, sys, os
import socket, time
try:
    from urllib.request import urlopen
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
    from urllib2 import urlopen
import argparse

def parse_args():
    """Parse arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Diagnose script for checking the current system.')
    choices = ['python', 'pip', 'mxnet', 'os', 'hardware', 'network']
    for choice in choices:
        parser.add_argument('--' + choice, default=1, type=int,
                            help='Diagnose {}.'.format(choice))
    parser.add_argument('--region', default='', type=str,
                        help="Additional sites in which region(s) to test. \
                        Specify 'cn' for example to test mirror sites in China.")
    parser.add_argument('--timeout', default=10, type=int,
                        help="Connection test timeout threshold, 0 to disable.")
    args = parser.parse_args()
    return args

URLS = {
    'MXNet': 'https://github.com/apache/incubator-mxnet',
    'Gluon Tutorial(en)': 'http://gluon.mxnet.io',
    'Gluon Tutorial(cn)': 'https://zh.gluon.ai',
    'FashionMNIST': 'https://apache-mxnet.s3-accelerate.dualstack.amazonaws.com/gluon/dataset/fashion-mnist/train-labels-idx1-ubyte.gz',
    'PYPI': 'https://pypi.python.org/pypi/pip',
    'Conda': 'https://repo.continuum.io/pkgs/free/',
}
REGIONAL_URLS = {
    'cn': {
        'PYPI(douban)': 'https://pypi.douban.com/',
        'Conda(tsinghua)': 'https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/',
    }
}

def test_connection(name, url, timeout=10):
    """Simple connection test"""
    file_str = StringIO()
    urlinfo = urlparse(url)
    start = time.time()
    try:
        ip = socket.gethostbyname(urlinfo.netloc)
    except Exception as e:
        file_str.write('Error resolving DNS for {}: {}, {}<br>'.format(name, url, e))
        return
    dns_elapsed = time.time() - start
    start = time.time()
    try:
        _ = urlopen(url, timeout=timeout)
    except Exception as e:
        file_str.write("Error open {}: {}, {}, DNS finished in {} sec.<br>".format(name, url, e, dns_elapsed))
        return
    load_elapsed = time.time() - start
    file_str.write("Timing for {}: {}, DNS: {:.4f} sec, LOAD: {:.4f} sec.<br>".format(name, url, dns_elapsed, load_elapsed))
    return file_str.getvalue()

def check_python():
    file_str = StringIO()
    file_str.write('----------Python Info----------<br>')
    file_str.write('Version      : %s<br>' % platform.python_version())
    file_str.write('Compiler     : %s<br>' % platform.python_compiler())
    #file_str.write('Build        : %s' % platform.python_build())
    #file_str.write('Arch         : %s' % platform.architecture())
    return file_str.getvalue()

def check_pip():
    file_str = StringIO()
    file_str.write('------------Pip Info-----------')
    try:
        import pip
        file_str.write('Version      : %r<br>' % pip.__version__)
        file_str.write('Directory    : %r<br>' % os.path.dirname(pip.__file__))
    except ImportError:
        file_str.write('No corresponding pip install for current python.<br>')
    return file_str.getvalue()

def check_mxnet():
    file_str = StringIO()
    file_str.write('----------MXNet Info-----------<br>')
    try:
        import mxnet
        file_str.write('Version      : %r<br>' % mxnet.__version__)
        mx_dir = os.path.dirname(mxnet.__file__)
        file_str.write('Directory    : %r<br>' % mx_dir)
        commit_hash = os.path.join(mx_dir, 'COMMIT_HASH')
        with open(commit_hash, 'r') as f:
            ch = f.read().strip()
            file_str.write('Commit Hash   : %r<br>' % ch)
    except ImportError:
        file_str.write('No MXNet installed.<br>')
    except Exception as e:
        import traceback
        if not isinstance(e, IOError):
            file_str.write("An error occured trying to import mxnet.<br>")
            file_str.write("This is very likely due to missing missing or incompatible library files.<br>")
        file_str.write(traceback.format_exc())
    return file_str.getvalue()

def check_os():
    file_str = StringIO()
    file_str.write('----------System Info----------<br>')
    file_str.write('Platform     : %r<br>' % platform.platform())
    file_str.write('system       : %r<br>' % platform.system())
    file_str.write('node         : %r<br>' % platform.node())
    file_str.write('release      : %r<br>' % platform.release())
    file_str.write('version      : %r<br>' % platform.version())
    return file_str.getvalue()

def check_hardware():
    file_str = StringIO()
    file_str.write('----------Hardware Info----------<br>')
    file_str.write('machine      : %r' % platform.machine())
    file_str.write('processor    : %r' % platform.processor())
    if sys.platform.startswith('darwin'):
        pipe = subprocess.Popen(('sysctl', '-a'), stdout=subprocess.PIPE)
        output = pipe.communicate()[0]
        for line in output.split(b'\n'):
            if 'brand_string' in line or 'features' in line:
                file_str.write(line.strip())
    elif sys.platform.startswith('linux'):
        file_str.write(str(subprocess.check_output(['lscpu'])).replace('\\n', '<br>'))
    elif sys.platform.startswith('win32'):
        subprocess.call(['wmic', 'cpu', 'get', 'name'])
    file_str.write('<br>')
    return file_str.getvalue()

def check_network(args=1):
    file_str = StringIO()
    file_str.write('----------Network Test----------<br>')
    if args.timeout > 0:
        file_str.write('Setting timeout: {}<br>'.format(args.timeout))
        socket.setdefaulttimeout(10)
    for region in args.region.strip().split(','):
        r = region.strip().lower()
        if not r:
            continue
        if r in REGIONAL_URLS:
            URLS.update(REGIONAL_URLS[r])
        else:
            import warnings
            warnings.warn('Region {} do not need specific test, please refer to global sites.<br>'.format(r))
    for name, url in URLS.items():
        test_connection(name, url, args.timeout)
    return file_str.getvalue()

def check_load():
    file_str = StringIO()
    file_str.write('----------Load Test----------<br>')
    file_str.write(subprocess.check_output(['uptime']).decode('utf-8').replace('\\n', '<b>'))
    file_str.write('<br>')
    return file_str.getvalue()

def check_ip():
    file_str = StringIO()
    file_str.write('----------IP Test----------<br>')
    file_str.write(subprocess.check_output(['hostname', '-I']).decode('utf-8').replace('\\n', '<b>'))
    file_str.write('<br>')
    return file_str.getvalue()

def check_time():
    file_str = StringIO()
    file_str.write('----------Time Test----------<br>')
    file_str.write(subprocess.check_output(['date']).decode('utf-8').replace('\\n', '<b>'))
    file_str.write('<br>')
    return file_str.getvalue()

HOST_NAME = '0.0.0.0'
PORT_NUMBER = 9000


class MyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.respond({'status': 200})

    def handle_http(self, status_code, path):
        self.send_response(status_code)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        content = '<meta http-equiv="Refresh" content="1">'
        content += check_python()
        content += check_pip()
        content += check_mxnet()
        content += check_os()
        content += check_hardware()
        #content += check_network()
        content += check_load()
        content += check_ip()
        content += check_time()
        return bytes(content, 'utf-8')

    def respond(self, opts):
        response = self.handle_http(opts['status'], self.path)
        self.wfile.write(response)

    def log_message(self, format, *args):
        return

class HTTPServerV4(HTTPServer):
address_family = socket.AF_INET4

if __name__ == '__main__':
    server_class = HTTPServerV4
    httpd = server_class((HOST_NAME, PORT_NUMBER), MyHandler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
