PORT = 80

LOGLEVEL = 'debug'

BUFFSIZE = 4096
SEPARATOR = '\r\n'
PROTOCOL = 'HTTP/1.1'
PREFIX = 'http://'

BAD_REQUEST = 400
FORBIDDEN = 403
BAD_GATEWAY = 502
UNKNOWN_VERSION = 505
INTERNAL_ERROR = 500

HOSTS = {
    'www.lavoz.com.ar': ['200.32.12.132', '200.43.222.4'],
    'staticft.lavozdelinterior.com.ar': ['186.153.134.142', '200.32.12.134'],
    'redesysd': ['127.0.0.1:8000', '127.0.0.1:8001', '127.0.0.1:8002', ],
    'localhost': ['200.16.17.104', '127.0.0.1:9999', ],
    'pastebin.com': ['190.93.240.15', '190.93.241.15', '190.93.242.15',
                     '190.93.243.15', '141.101.112.16'],
    'www.famaf.unc.edu.ar': ['200.16.17.104'],
}
