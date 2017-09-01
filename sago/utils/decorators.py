# -*- coding: utf-8 -*-
import functools
import threading


_lock = threading.RLock()


def singleton(func):

    @functools.wraps(func)
    def wrapper(cls, *args, **kwargs):
        if func.__name__ != '__new__':
            raise ValueError(
                'The decorated method should be the __new__ of class.')

        _lock.acquire()

        instance = getattr(cls, '__instance', None)
        if not instance:
            cls.__instance = instance = func(cls, *args, **kwargs)

        _lock.release()
        return instance

    return wrapper
