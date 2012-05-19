'''
Created on 17/05/2012

@author: piranna
'''

try:
    from collections import OrderedDict
except ImportError:
    OrderedDict = None


if OrderedDict:
    class Cache(OrderedDict):
        """Cache with LRU algorithm using an OrderedDict as basis
        """
        def __init__(self, maxsize=100):
            OrderedDict.__init__(self)

            self._maxsize = maxsize

        def __getitem__(self, key, *args, **kwargs):
            # Get the key and remove it from the cache, or raise KeyError
            value = OrderedDict.__getitem__(self, key)
            del self[key]

            # Insert the (key, value) pair on the front of the cache
            OrderedDict.__setitem__(self, key, value)

            # Return the value from the cache
            return value

        def __setitem__(self, key, value, *args, **kwargs):
            # Key was inserted before, remove it so we put it at front later
            if key in self:
                del self[key]

            # Too much items on the cache, remove the least recent used
            elif len(self) >= self._maxsize:
                self.popitem(False)

            # Insert the (key, value) pair on the front of the cache
            OrderedDict.__setitem__(self, key, value, *args, **kwargs)

else:
    class Cache(dict):
        """Cache that reset when gets full
        """
        def __init__(self, maxsize=100):
            dict.__init__(self)

            self._maxsize = maxsize

        def __setitem__(self, key, value, *args, **kwargs):
            # Reset the cache if we have too much cached entries and start over
            if len(self) >= self._maxsize:
                self.clear()

            # Insert the (key, value) pair on the front of the cache
            dict.__setitem__(self, key, value, *args, **kwargs)


def memoize_generator(func):
    """Memoize decorator for generators

    Store `func` results in a cache according to their arguments as 'memoize'
    does but instead this works on decorators instead of regular functions.
    Obviusly, this is only useful if the generator will always return the same
    values for each specific parameters...
    """
    cache = Cache()

    def wrapped_func(*args, **kwargs):
#        params = (args, kwargs)
        params = (args, tuple(sorted(kwargs.items())))

        # Look if cached
        try:
            cached = cache[params]

        # Not cached, exec and store it
        except KeyError:
            cached = []

            for item in func(*args, **kwargs):
                cached.append(item)
                yield item

            cache[params] = cached

        # Cached, yield its items
        else:
            for item in cached:
                yield item

    return wrapped_func
