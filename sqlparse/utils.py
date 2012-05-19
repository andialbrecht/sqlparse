'''
Created on 17/05/2012

@author: piranna
'''


def memoize_generator(func):
    """Memoize decorator for generators

    Store `func` results in a cache according to their arguments as 'memoize'
    does but instead this works on decorators instead of regular functions.
    Obviusly, this is only useful if the generator will always return the same
    values for each specific parameters...
    """
    cache = {}

    def wrapped_func(*args, **kwargs):
        params = (args, kwargs)

        # Look if cached
        try:
            cached = cache[params]

        # Not cached, exec and store it
        except KeyError:
            # Reset the cache if we have too much cached entries and start over
            # In the future would be better to use an OrderedDict and drop the
            # Least Recent Used entries
            if len(cache) >= 10:
                cache.clear()

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
