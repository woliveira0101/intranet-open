import redis as redis_orig
import cPickle as pickle

class Redis(redis_orig.StrictRedis):

    def set(self, name, value, **kwargs):
        value = pickle.dumps(value)
        super(Redis, self).set(name, value, **kwargs)

    def get(self, name):
        result = super(Redis, self).get(name)
        if result is not None:
            return pickle.loads(result)

    def rpop(self, name):
        result = super(Redis, self).rpop(name)
        if result is not None:
            return pickle.loads(result)

    def lpush(self, name, *values):
        values = [pickle.dumps(v) for v in values]
        super(Redis, self).lpush(name, *values)