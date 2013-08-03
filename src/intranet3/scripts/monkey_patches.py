import os
import sys
from twisted.python import logfile, syslog, log

class DailyLogFile(logfile.DailyLogFile):


    def suffix(self, tupledate):
        """Return the suffix given a (year, month, day) tuple or unixtime"""
        try:
            return '-'.join(map(str, tupledate))
        except:
            # try taking a float unixtime
            return '-'.join(map(str, self.toDate(tupledate)))

def _openLogFile(self, path):
    return DailyLogFile(os.path.basename(path), os.path.dirname(path))


def _getLogObserver(self):
    """
    Create and return a suitable log observer for the given configuration.

    The observer will go to syslog using the prefix C{_syslogPrefix} if
    C{_syslog} is true.  Otherwise, it will go to the file named
    C{_logfilename} or, if C{_nodaemon} is true and C{_logfilename} is
    C{"-"}, to stdout.

    @return: An object suitable to be passed to C{log.addObserver}.
    """
    if self._syslog:
        return syslog.SyslogObserver(self._syslogPrefix).emit

    if self._logfilename == '-':
        if not self._nodaemon:
            sys.exit('Daemons cannot log to stdout, exiting!')
        logFile = sys.stdout
    elif self._nodaemon and not self._logfilename:
        logFile = sys.stdout
    else:
        if not self._logfilename:
            self._logfilename = 'twistd.log'
        logFile = DailyLogFile.fromFullPath(self._logfilename)
        try:
            import signal
        except ImportError:
            pass
        else:
            # Override if signal is set to None or SIG_DFL (0)
            if not signal.getsignal(signal.SIGUSR1):
                def rotateLog(signal, frame):
                    from twisted.internet import reactor
                    reactor.callFromThread(logFile.rotate)
                signal.signal(signal.SIGUSR1, rotateLog)
    return log.FileLogObserver(logFile).emit
