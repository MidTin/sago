# -*- coding: utf-8 -*-
import asyncio
import inspect


class LazyObject:

    def __init__(self, func, loop):
        self.loop = loop
        self.func = func

    def __call__(self, *args, **kwargs):
        callback = kwargs.pop('callback', None)

        if inspect.isawaitable(self.func):
            ret = self.func
        else:
            ret = self.func(*args, **kwargs)

        if asyncio.iscoroutine(ret):
            future = asyncio.run_coroutine_threadsafe(ret, loop=self.loop)
            if callback:
                future.add_done_callback(callback)
            return future

        return ret

    def __repr__(self):
        return repr(self.func)
