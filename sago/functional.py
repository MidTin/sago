# -*- coding: utf-8 -*-
import asyncio


class LazyObject:

    def __init__(self, func, loop):
        self.loop = loop
        self.func = func

    def __call__(self, *args, **kwargs):
        callback = kwargs.pop('callback', None)

        result = self.func(*args, **kwargs)
        if asyncio.iscoroutine(result):
            future = asyncio.run_coroutine_threadsafe(result, loop=self.loop)
            if callback:
                future.add_done_callback(callback)
            return future

        return result

    def __repr__(self):
        return repr(self.func)
