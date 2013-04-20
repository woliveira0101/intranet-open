from base64 import b64encode, b64decode
from itertools import cycle, izip

from intranet3 import config

def _encrypt(value):
    """ symmetrically encrypts the value using datastore password (using simple XOR) """
    if isinstance(value, unicode):
        value = value.encode('utf-8')
    assert isinstance(value, str), u"Passwords can only be strings"
    DATASTORE_SYMMETRIC_PASSWORD = config['DATASTORE_SYMMETRIC_PASSWORD']
    password = cycle(DATASTORE_SYMMETRIC_PASSWORD)
    return ''.join(chr(ord(v) ^ ord(p)) for v, p in izip(value, password))

_decrypt = _encrypt # we use symmetrical encryption

def encrypt(value):
    encrypted = _encrypt(value)
    result = b64encode(encrypted)
    return result

def decrypt(value):
    decoded = b64decode(value)
    result = _decrypt(decoded)
    return result
