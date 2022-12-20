import os
import sys
from time import time

import psutil


def memory_usage_psutil():
    process = psutil.Process(os.getpid())
    mem = process.memory_full_info().rss / float(2**20)
    return mem


def log_memory(name=''):
    usage = memory_usage_psutil()
    prefix = f'{name}: ' if name else ''
    print(f'{prefix}Memory usage: {usage:.2f} MB; time: {time():.3f}', file=sys.stderr)
