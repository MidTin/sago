# -*- coding: utf-8 -*-
import asyncio
import random
import string


class AsyncObject:

    def __init__(self, func, loop):
        self.loop = loop
        self.func = func

    def __call__(self, *args, **kwargs):
        callback = kwargs.pop('callback', None)

        if asyncio.iscoroutinefunction(self.func):
            self.func = self.func(*args, **kwargs)

        future = asyncio.run_coroutine_threadsafe(self.func, loop=self.loop)
        if callback:
            future.add_done_callback(callback)
        return future

    def __repr__(self):
        return repr(self.func)


def random_str(length=10):
    return ''.join([random.choice(string.ascii_letters + string.digits)
                    for _ in range(length)])


def random_num(length=10):
    return ''.join([random.choice(string.digits) for _ in range(length)])
