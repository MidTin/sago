# -*- coding: utf-8 -*-
import functools
import inspect
import logging
import re
import time

import aiohttp

import exceptions
from loop import EventLoop
from functional import LazyObject

logger = logging.getLogger('sago')

APPID = 'wx782c26e4c19acffb'
LANG = 'zh_CN'

UUID_URL = r'https://login.weixin.qq.com/jslogin'
LOGIN_PAGE_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'
LOGIN_QRCODE_URL = r'https://login.weixin.qq.com/l/'
CHECK_QRCODE_SCANNED_URL = r'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login'


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

    async def fetch_login_qrcode(self):
        assert hasattr(self, 'uuid'), ('request_uuid should be called before'
                                       'this method.')
        url = LOGIN_QRCODE_URL + self.uuid
        resp = await self._client.get(url)
        return await resp.read()

    async def listen_qrcode_scanned(self):
        assert hasattr(self, 'uuid'), ('request_uuid should be called before'
                                       'this method.')

        is_scanned = False

        params = {
            'loginicon': True,
            'uuid': self.uuid,
            'tip': 1,
        }
        while not is_scanned:
            params['_'] = self.timestamp

            resp = await self._client.get(
                CHECK_QRCODE_SCANNED_URL, params=params)

            ret = await resp.text()
            m = re.search(r'window.code=(?P<code>\d+);', ret)
            if m:
                code = m.group('code')
                if code == '201':
                    logger.info('QRCode for login is scanned.')

                elif code == '408':
                    raise exceptions.LoginTimeoutError()

                is_scanned = code == '200'
                if is_scanned:
                    m = re.search(
                        r'window.redirect_uri="(?P<redirect_uri>\S+";', ret)
                    if not m:
                        raise exceptions.LoginUrlNotFound()

                    self.login_redirect_uri = m.group('redirect_uri')

        return is_scanned

    def __del__(self):
        self._client.close()
