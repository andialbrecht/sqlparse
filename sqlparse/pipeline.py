# Copyright (C) 2011 Jesus Leganes "piranna", piranna@gmail.com
#
# This module is part of python-sqlparse and is released under
# the BSD License: http://www.opensource.org/licenses/bsd-license.php.

from types import GeneratorType


class Pipeline(list):
    """Pipeline to process filters sequentially"""

    def __call__(self, stream):
        """Run the pipeline

        Return a static (non generator) version of the result
        """

        # Run the stream over all the filters on the pipeline
        for filter in self:
            # Functions and callable objects (objects with '__call__' method)
            if callable(filter):
                stream = filter(stream)

            # Normal filters (objects with 'process' method)
            else:
                stream = filter.process(None, stream)

        # If last filter return a generator, staticalize it inside a list
        if isinstance(stream, GeneratorType):
            return list(stream)
        return stream
