import itertools
import re
from collections import OrderedDict, deque
from contextlib import contextmanager


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


def memoize_generator(func):
    """Memoize decorator for generators

    Store `func` results in a cache according to their arguments as 'memoize'
    does but instead this works on decorators instead of regular functions.
    Obviusly, this is only useful if the generator will always return the same
    values for each specific parameters...
    """
    cache = Cache()

    def wrapped_func(*args, **kwargs):
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


# This regular expression replaces the home-cooked parser that was here before.
# It is much faster, but requires an extra post-processing step to get the
# desired results (that are compatible with what you would expect from the
# str.splitlines() method).
#
# It matches groups of characters: newlines, quoted strings, or unquoted text,
# and splits on that basis. The post-processing step puts those back together
# into the actual lines of SQL.
SPLIT_REGEX = re.compile(r"""
(
 (?:                     # Start of non-capturing group
  (?:\r\n|\r|\n)      |  # Match any single newline, or
  [^\r\n'"]+          |  # Match any character series without quotes or
                         # newlines, or
  "(?:[^"\\]|\\.)*"   |  # Match double-quoted strings, or
  '(?:[^'\\]|\\.)*'      # Match single quoted strings
 )
)
""", re.VERBOSE)

LINE_MATCH = re.compile(r'(\r\n|\r|\n)')


def split_unquoted_newlines(text):
    """Split a string on all unquoted newlines.

    Unlike str.splitlines(), this will ignore CR/LF/CR+LF if the requisite
    character is inside of a string."""
    lines = SPLIT_REGEX.split(text)
    outputlines = ['']
    for line in lines:
        if not line:
            continue
        elif LINE_MATCH.match(line):
            outputlines.append('')
        else:
            outputlines[-1] += line
    return outputlines


def remove_quotes(val):
    """Helper that removes surrounding quotes from strings."""
    if val is None:
        return
    if val[0] in ('"', "'") and val[0] == val[-1]:
        val = val[1:-1]
    return val


def recurse(*cls):
    """Function decorator to help with recursion

    :param cls: Classes to not recurse over
    :return: function
    """
    def wrap(f):
        def wrapped_f(tlist):
            for sgroup in tlist.get_sublists():
                if not isinstance(sgroup, cls):
                    wrapped_f(sgroup)
            f(tlist)

        return wrapped_f

    return wrap


def imt(token, i=None, m=None, t=None):
    """Aid function to refactor comparisons for Instance, Match and TokenType
    Aid fun
    :param token:
    :param i: Class or Tuple/List of Classes
    :param m: Tuple of TokenType & Value. Can be list of Tuple for multiple
    :param t: TokenType or Tuple/List of TokenTypes
    :return:  bool
    """
    t = (t,) if t and not isinstance(t, (list, tuple)) else t
    m = (m,) if m and not isinstance(m, (list,)) else m

    if token is None:
        return False
    elif i is not None and isinstance(token, i):
        return True
    elif m is not None and any((token.match(*x) for x in m)):
        return True
    elif t is not None and token.ttype in t:
        return True
    else:
        return False


def find_matching(tlist, token, M1, M2):
    idx = tlist.token_index(token) if not isinstance(token, int) else token
    depth = 0
    for token in tlist.tokens[idx:]:
        if token.match(*M1):
            depth += 1
        elif token.match(*M2):
            depth -= 1
            if depth == 0:
                return token


def consume(iterator, n):
    """Advance the iterator n-steps ahead. If n is none, consume entirely."""
    deque(itertools.islice(iterator, n), maxlen=0)


@contextmanager
def offset(filter_, n=0):
    filter_.offset += n
    yield
    filter_.offset -= n


@contextmanager
def indent(filter_, n=1):
    filter_.indent += n
    yield
    filter_.indent -= n
