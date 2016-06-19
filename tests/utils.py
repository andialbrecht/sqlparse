# -*- coding: utf-8 -*-

"""Helpers for testing."""

import io
import os

DIR_PATH = os.path.dirname(__file__)
FILES_DIR = os.path.join(DIR_PATH, 'files')


def load_file(filename, encoding='utf-8'):
    """Opens filename with encoding and return its contents."""
    with io.open(os.path.join(FILES_DIR, filename), encoding=encoding) as f:
        return f.read()
