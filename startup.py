"""Code that runs on the interpreter for out of band signalling

This code should:
    - notify ui process that running code is done?
    - run autocompletion code in another thread that has access to current scope somehow
    - run module import completion code if necessary (maybe this can happen in UI thread)
"""

import threading

def say_hello_occasionally():
    import socket
    import time
    s = socket.socket()
    s.connect(('localhost', 12345))
    while True:
        s.send('hello!\n')
        time.sleep(10)

t = threading.Thread(target=say_hello_occasionally)
t.daemon = True
t.start()

del threading
del say_hello_occasionally
del t


a = 1


