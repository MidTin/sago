# -*- coding: utf-8 -*-

import asyncio
import threading


_lock = threading.RLock()


def run_event_loop(loop):
    thread = threading.Thread(target=loop.run_forever)
    thread.daemon = True
    thread.start()


class EventLoop:

    _loop_instance = None

    def __new__(cls, **kwags):
        _lock.acquire()
        if not cls._loop_instance:
            cls._loop_instance = asyncio.get_event_loop()
            run_event_loop(cls._loop_instance)

        _lock.release()
        return cls._loop_instance
