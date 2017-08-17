# -*- coding: utf-8 -*-
import functools
import inspect
import logging
import re
import time

import aiohttp

from loop import EventLoop
from functional import LazyObject

logger = logging.getLogger('sago')

APPID = 'wx782c26e4c19acffb'
LANG = 'zh_CN'

UUID_URL = r'https://login.weixin.qq.com/jslogin'
LOGIN_PAGE_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'


class Core:

    def __init__(self, lang=LANG):
        self.loop = EventLoop()
        self._client = aiohttp.ClientSession(loop=self.loop)
        self.lang = lang

    @property
    def timestamp(self):
        return int(time.time())

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)
        if inspect.ismethod(attr):
            return functools.update_wrapper(LazyObject(attr, self.loop), attr)
        return attr

    async def request_uuid(self):
        params = {
            'appid': APPID,
            'fun': 'new',
            'lang': self.lang,
            'redirect_uri': LOGIN_PAGE_URL,
            '_': self.timestamp,
        }

        resp = await self._client.post(UUID_URL, params=params)
        if resp.status != 200:
            logger.error('The server returned code %s while request uuid',
                         resp.status)
            return

        result = await resp.text()
        m = re.search(
            r'window.QRLogin.code = (?P<status_code>\d+); '
            r'window.QRLogin.uuid = "(?P<uuid>\S+)"', result)

        if not m:
            logger.error('Request uuid failed. resp: %r', result)
            return

        self.uuid = m.group('uuid')
        return self.uuid

    def __del__(self):
        self._client.close()
