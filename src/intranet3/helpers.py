import os
import time
import math
import tempfile
import datetime
from dateutil.relativedelta import relativedelta
from urllib import quote_plus
from decimal import Decimal, ROUND_UP

try:
    from PIL import Image
except ImportError:
    import Image
from gdata.spreadsheet import text_db
from gdata.service import RequestError

from intranet3.priorities import PRIORITIES
from intranet3.log import FATAL_LOG, EXCEPTION_LOG, INFO_LOG

LOG = INFO_LOG(__name__)
EXCEPTION = EXCEPTION_LOG(__name__)
FATAL = FATAL_LOG(__name__)


positive_values = (True, 1, 1.0, '1', 'True', 'true', 't')

negative_values = (False, None, 0, 0.0, '0', 'False', 'false', 'f', 'None')


def dates_between(start, end):
    delta = datetime.timedelta(days=1)
    while start <= end:
        yield start
        start += delta

def sorting_by_severity(a, b):
    a_idx = PRIORITIES.get(a.severity.lower(), 5)
    b_idx = PRIORITIES.get(b.severity.lower(), 5)

    compare = cmp(a_idx, b_idx)
    if compare == 0:
        # hack to always keep same order
        a_idx = str(a_idx) + str(a.id)
        b_idx = str(b_idx) + str(b.id)
        compare = cmp(a_idx, b_idx)
    return compare

def sorting_by_priority(a, b):
    a_idx = PRIORITIES.get(a.priority.lower(), 5)
    b_idx = PRIORITIES.get(b.priority.lower(), 5)

    compare = cmp(a_idx, b_idx)
    if compare == 0:
        # hack to always keep same order
        a_idx = str(a_idx) + str(a.id)
        b_idx = str(b_idx) + str(b.id)
        compare = cmp(a_idx, b_idx)
    return compare

class SpreadsheetConnector(object):
    def __init__(self, email, password):
        self.client = text_db.DatabaseClient(email, password)

    def get_worksheet(self, spreadsheet_key, number):
        database = self.client.GetDatabases(spreadsheet_key)[0]
        return database.GetTables()[number]
    
def previous_day(date):
    return day_offset(date, -1)

def next_day(date):
    return day_offset(date, +1)

def day_offset(date, n):
    delta = datetime.timedelta(days=n)
    return date + delta

MONTH_DELTA = relativedelta(months=1)

def previous_month(date):
    return date - MONTH_DELTA
    
def next_month(date):
    return date + MONTH_DELTA

def start_end_month(date=None):
    if not date:
        date = datetime.date.today()
    month_start = datetime.date(date.year, date.month, 1)

    month_ends = previous_day(month_start + MONTH_DELTA)
    return month_start, month_ends


MAX_TRIES = 9
# calculate how many seconds to wait after n-th try
wait_time = lambda n: 10 ** math.floor((n - 1) / 3)

def trier(func, doc=u''):
    """
    Repeats a callback MAX_TRIES times with increasing time intervals (1s, 10s, 100s, 1000s).
    RequestErrors are causing another try to be performed.
    The MAX_TRIES-th unsuccessfull try causes the RequestError to be raised up from the function.
    """
    i = 1
    while True:
        try:
            result = func()
        except (AssertionError, RequestError), e:
            EXCEPTION(u'Error while trying function %s (%s/%s try)' % (doc, i, MAX_TRIES))
            if isinstance(e, RequestError) and e.message.get('status') == 404: # no sense in retrying 404
                raise
            time.sleep(wait_time(i))
            i += 1
            if i > MAX_TRIES:
                FATAL(u'Unable to execute function %s in %s tries' % (doc, MAX_TRIES))
                raise
        except:
            EXCEPTION(u"Unknown exception while trying function %s (%s/%s try)" % (doc, i, MAX_TRIES))
            FATAL(u"Unable to execute function due to unexpected error")
            raise
        else:
            LOG(u'Managed to execute function %s (%s/%s try)' % (doc, i, MAX_TRIES))
            return result
        
def decoded_dict(d, encoding='utf-8'):
    result = {}
    for k, v in d.iteritems():
        result[k] = v.decode(encoding)
    return result

def Converter(**kwargs):
    """
    Returns a function that converts a dictionary by re-assigning keys according
    to the mapping given in the params.
    The mapping can map key -> key or key -> function
    
    For example:
    
    >>> converter = Converter(a='b', b=lambda d: d['e'] + d['f'])
    >>> converter({'a': 1, 'b': 2, 'e': 3, 'f': 4})
    {'a': 2, 'b': 7}
    """
    return lambda d: dict((k, v(d) if callable(v) else d.get(v, '')) for (k, v) in kwargs.iteritems())

# serializes keyword arguments into URL query string
serialize_url = lambda prefix, **kwargs: prefix.encode('utf-8') + '&'.join(
    ('%s=%s' % (k, quote_plus(v.encode('utf-8') if isinstance(v, unicode) else v)))
    if isinstance(v, basestring)
    else ('&'.join('%s=%s' % (k, quote_plus(p.encode('utf-8') if isinstance(p, unicode) else p)) for p in v))
    for (k, v) in kwargs.iteritems()
)

def format_time(value):
    value = Decimal(str(value)).quantize(Decimal('.01'), rounding=ROUND_UP)
    h, m = divmod(value * 60, 60)
    return "%d:%02d" % (h, round(m))

def get_mem_usage():
    """ Get memory usage for current process """
    import os, subprocess
    pid = os.getpid()
    process = subprocess.Popen("ps -orss= %s" % pid, shell=True, stdout=subprocess.PIPE)
    out, _err = process.communicate()
    return int(out)

def image_resize(source,type, width = 100,height = 100):
    s = ImageScaler(source)
    if type == 't':
        return s.thumb(width,height)
    else:
        return s.smart_scale(width,height)
        
class ImageScaler():
    def __init__(self,source):
       self.source = source
       self.out = '';
    
    def _tmp(self):
        _,file = tempfile.mkstemp(prefix='image-')
        with open(file,'w') as f:
            f.write(self.source)
        return file
    
    def _img(self,file):
        return Image.open(file);
    
    def _out(self,file,img):
        out = ''
        if os.path.exists(file):
            img.save(file,'PNG')
            with open(file,'r') as f:
                out = f.read()
            os.remove(file)
        return out
    
    def smart_scale(self,width,height):
        file = self._tmp()
        img = self._img(file)
        
        #img.crop()
        x,y = img.size
        dx = float(x)/float(width)
        dy = float(y)/float(height)
        r = min(dx,dy)
        xr = int(x/r)
        yr = int(y/r)
        
        img = img.resize((xr,yr), Image.ANTIALIAS)
        x1 = max(0,(xr-width)/2)
        y1 = max(0,(yr-height)/2)
        x2 = width+x1
        y2 = height+y1
        img = img.crop((x1,y1,x2,y2))
        return self._out(file,img)
    
    def crop(self,size):
        file = self._tmp()
        img = self._img(file)
        img2 = img.crop(size)
        img2.show()
        return self._out(file,img2)
        
    def thumb(self,width,height):
        file = self._tmp()
        img = self._img(file)
        img.thumbnail((width,height))
        return self._out(file, img)

def make_path(*args):
    return os.path.join(*map(lambda x: str(x).strip('/'), args))

def groupby(a_list, keyfunc=lambda x: x, part=lambda x: x):
    result = {}
    for e in a_list:
        to_append = part(e)
        values = result.setdefault(keyfunc(e), [])
        if to_append is not None:
            values.append(to_append)

    return result

def partition(items, max_count):
    """ Partition a list of items into portions no larger than max_count """
    portions = int(math.ceil(float(len(items)) / max_count))
    for p in xrange(portions):
        yield items[p::portions]

def get_working_days(date_start, date_end):
        from intranet3.models import Holiday
        if date_start > date_end:
            return 0
        holidays = Holiday.all()
        date = date_start
        diff = datetime.timedelta(days=1)
        days = 0
        while date <= date_end:
            if not Holiday.is_holiday(date, holidays=holidays):
                days += 1
            date += diff
        return days
