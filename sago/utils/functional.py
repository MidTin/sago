# -*- coding: utf-8 -*-
import asyncio
import random
import string


class AsyncObject:

    def __init__(self, coroutine_func, loop):
        if not asyncio.iscoroutinefunction(coroutine_func):
            raise ValueError('func should be a coroutine function')

        self.c_func = coroutine_func
        self.loop = loop

    def __call__(self, *args, **kwargs):
        callback = kwargs.pop('callback', None)
        nowait = kwargs.pop('nowait', True)

        future = asyncio.run_coroutine_threadsafe(
            self.c_func(*args, **kwargs), loop=self.loop)

        if callback:
            future.add_done_callback(callback)

        if not nowait:
            return future.result()

        return future

    def __repr__(self):
        return repr(self.c_func)


def random_str(length=10):
    return ''.join([random.choice(string.ascii_letters + string.digits)
                    for _ in range(length)])


def random_num(length=10):
    return ''.join([random.choice(string.digits) for _ in range(length)])
