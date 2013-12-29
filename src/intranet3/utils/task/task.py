from uuid import uuid4

class Task(object):
    def __init__(self, url, payload=None, name='default'):
        self.id = uuid4()
        self.name = name
        self.url = url
        self.payload = payload

    def __str__(self):
        return "Task(name='%s', id='%s')" % (self.name, self.id)