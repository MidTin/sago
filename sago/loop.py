# -*- coding: utf-8 -*-
import asyncio
import threading

from .utils.decorators import singleton


def run_event_loop(loop):
    thread = threading.Thread(target=loop.run_forever)
    thread.daemon = True
    thread.start()


class EventLoop:

    @singleton
    def __new__(cls, **kwags):
        loop = asyncio.get_event_loop()
        run_event_loop(loop)
        # cls._loop_instance.set_debug(True)
        return loop
