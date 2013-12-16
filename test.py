from subprocess import Popen, PIPE
import socket
import pty
import os
from select import select
import sys
import tty
import termios
from contextlib import contextmanager
import time

startup_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'startup.py')

class Repl():
    def __init__(self, python):
        """on_line is a callback for a completed line, which is passed without the newline character"""

        self.current_input_line = ''
        self.display_lines = []
        self.continued = False

        self.python = python
        #self.python.stdout_line_receiver.on_line = lambda line: self.display_lines.append(line)
        #self.python.stderr_line_receiver.on_line = lambda line: self.display_lines.append('ERR: '+line)

    def loop(self):
        rs, ws, es = select(self.python.readers + [sys.stdin], [], [])
        for r in rs:
            print r, 'is ready for read'
            time.sleep(.01)
            if r is sys.stdin:
                self.process_keypress(r.read(1))
            else:
                r.on_read()
        #self.render()

    def loop_forever(self):
        while True:
            self.loop()

    def process_keypress(self, char):
        if char == '':
            self.current_input_line = self.current_input_line[:-1]
        elif char == '\n':
            self.python.send(self.current_input_line+'\n')
            self.display_lines.append(self.current_line)
            self.current_input_line = ''
        else:
            self.current_input_line += char

    @property
    def current_line(self):
        return '>>> '+self.current_input_line

    def render(self):
        #CLEAR_SCREEN = "[2J"
        #print CLEAR_SCREEN
        for line in self.display_lines:
            print line
        print self.current_line + u'\u2588'.encode('utf8')

class PythonSubprocess(object):

    def __init__(self):

        def on_stdout_line(line): sys.stdout.write('*OUT*%s\n' % line); sys.stdout.flush()
        def on_stderr_line(line): sys.stdout.write('*ERR*%s\n' % line); sys.stdout.flush()
        def on_meta_line(line): sys.stdout.write('*META*%s\n' % line); sys.stdout.flush()

        #listener = socket.socket()
        #listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #listener.bind(('localhost', 12345))
        #listener.listen(5)

        master, slave = pty.openpty()
        environ = os.environ.copy()
        #environ['PYTHONSTARTUP'] = startup_script
        self.p = Popen([sys.executable], stdin=slave, stdout=PIPE, stderr=PIPE, env=environ)
        self.pin = os.fdopen(master, 'w')
        #s, addr = listener.accept()

        #self.meta_line_receiver = PythonMeta(s, on_line=on_meta_line)
        self.stdout_line_receiver = PythonOut(self.p.stdout, on_line=on_stdout_line)
        self.stderr_line_receiver = PythonError(self.p.stderr, on_line=on_stderr_line)

    @property
    def readers(self):
        return [self.stdout_line_receiver, self.stderr_line_receiver,] #self.meta_line_receiver]

    def send(self, msg):
        self.pin.write(msg)

    def kill(self):
        self.p.kill()

class PythonMeta(object):
    """Channel for metadata about interpreter, out of band signal"""
    def __init__(self, connection, on_line=lambda line: None):
        self.s = connection
        self.buffer = ''
        self.on_line = on_line

    def fileno(self):
        return self.s.fileno()

    def on_read(self):
        self.buffer += self.s.recv(10000)
        print 'out got', repr(self.buffer)
        while '\n' in self.buffer:
            msg, self.buffer = self.buffer.split('\n', 1)
            self.on_line(msg)

class PythonError(object):
    #TODO error messages should be extracted from normal stderr stream,
    # probably via __excepthook__ and some out-of-band signalling
    def __init__(self, pipe, on_line=lambda x: None):
        self.pipe = pipe
        self.msg = ''
        self.on_line = on_line

    def fileno(self):
        return self.pipe.fileno()

    def on_read(self):
        c = self.pipe.read(1)
        print 'err got', repr(c)
        if c == '\n':
            self.on_line(self.msg)
            self.msg = ''
        else:
            self.msg += c

class PythonOut(object):
    def __init__(self, pipe, on_line=lambda x: None):
        self.pipe = pipe
        self.msg = ''
        self.on_line = on_line
    def fileno(self):
        return self.pipe.fileno()
    def on_read(self):
        c = self.pipe.read(1)
        print 'out got', repr(c)
        if c == '\n':
            self.on_line(self.msg)
            self.msg = ''
        else:
            self.msg += c

@contextmanager
def cbreak():
    original_stty = termios.tcgetattr(sys.stdin)
    tty.setcbreak(sys.stdin)
    yield
    termios.tcsetattr(sys.stdin, termios.TCSANOW, original_stty)

@contextmanager
def python_subprocess():
    p = PythonSubprocess()
    yield p
    p.kill()

@contextmanager
def hide_cursor():
    HIDE_CURSOR = "[?25l"
    SHOW_CURSOR = "[?25h"
    print HIDE_CURSOR
    yield
    print SHOW_CURSOR

if __name__ == '__main__':
    with hide_cursor():
        with python_subprocess() as p:
            with cbreak():
                r = Repl(p)
                r.loop_forever()
