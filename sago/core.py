# -*- coding: utf-8 -*-
import functools
import inspect
import io
import logging
import re
import time
import xml.etree.ElementTree as ET

import aiohttp
import pyqrcode

import exceptions
from utils.functional import AsyncObject, random_num

logger = logging.getLogger('sago')

APPID = 'wx782c26e4c19acffb'
LANG = 'zh_CN'

CHECK_QRCODE_SCANNED_URL = r'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login'
GET_ALL_CONTACT_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact'
LOGIN_PAGE_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'
LOGIN_QRCODE_URL = r'https://login.weixin.qq.com/l/'
SYNC_CHECK_URL = r'https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck'
SYNC_DATA_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync'
UUID_URL = r'https://login.weixin.qq.com/jslogin'
WECHAT_INIT_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit'


class Core:

    def __init__(self, loop, lang=LANG):
        self.loop = loop
        self._client = aiohttp.ClientSession(loop=self.loop)
        self.lang = lang

    @property
    def reversed_timestamp(self):
        return abs(~int(time.time()))

    def __getattribute__(self, name):
        attr = super().__getattribute__(name)

        if inspect.iscoroutinefunction(attr) or inspect.iscoroutine(attr):
            return functools.update_wrapper(AsyncObject(attr, self.loop), attr)
        return attr

    async def request_uuid(self):
        params = {
            'appid': APPID,
            'fun': 'new',
            'lang': self.lang,
            'redirect_uri': LOGIN_PAGE_URL,
            '_': self.reversed_timestamp,
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

        return m.group('uuid')

    async def get_login_qrcode(self, uuid, storage=None):
        qrcode = pyqrcode.create(LOGIN_QRCODE_URL + uuid)
        if storage:
            buff = io.BytesIO()
            qrcode.png(buff, scale=10)
            fn = functools.partial(storage.save, buff)
            return await self.loop.run_in_executor(None, fn)

        print(qrcode.terminal(quiet_zone=1))

    async def listen_qrcode_scanned(self, uuid):
        is_scanned = False

        params = {
            'loginicon': 'true',
            'uuid': uuid,
            'tip': 1,
        }

        while not is_scanned:
            logger.info('Listening the qrcode scan event..')
            params['_'] = self.reversed_timestamp

            async with self._client.get(
                    CHECK_QRCODE_SCANNED_URL, params=params) as resp:
                ret = await resp.text()

            m = re.search(r'window.code=(?P<code>\d+);', ret)
            if m:
                code = m.group('code')
                if code == '201':
                    logger.info('QRCode for login is scanned.')

                elif code == '408':
                    raise exceptions.LoginTimeoutError()

                is_scanned = code == '200'
        else:
            m = re.search(
                r'window.redirect_uri="(?P<redirect_uri>\S+)";', ret)
            if not m:
                raise exceptions.LoginPageUrlNotFound()

            return m.group('redirect_uri')

    async def login_confirm(self, login_page_url):
        async with self._client.get(login_page_url) as resp:
            xml_ret = await resp.text()

        tree = ET.fromstring(xml_ret)
        root = tree.getroot()
        return {
            'skey': root.find('skey').text,
            'sid': root.find('wxsid').text,
            'uin': root.find('wxuin').text,
            'pass_ticket': root.find('pass_ticket').text,
        }

    def get_base_request_data(self, skey, sid, uin):
        return {
            'BaseRequest': {
                'Skey': skey,
                'Sid': sid,
                'Uin': uin,
                'DeviceID': 'e' + random_num(),
            }
        }

    def serialize_sync_key(self, sync_key_list):
        sync_key = []
        for itm in sync_key_list:
            sync_key.append('%d_%d' % (itm['Key'], itm['Val']))

        return '|'.join(sync_key)

    async def init_client(self, skey, sid, uin, pass_ticket):
        data = self.get_base_request_data(skey, sid, uin)
        params = {
            'pass_ticket': pass_ticket,
            'skey': skey,
            'r': self.reversed_timestamp,
        }

        async with self._client.post(
                WECHAT_INIT_URL, params=params, json=data) as resp:
            ret = await resp.json()

        return {
            'user_info': ret['User'],
            'sync_key': ret['SyncKey'],
        }

    async def request_all_contact(self, skey, pass_ticket):
        params = {
            'skey': skey,
            'pass_ticket': pass_ticket,
            'seq': 0,
            'r': self.reversed_timestamp,
        }
        async with self._client.post(GET_ALL_CONTACT_URL, params=params) as resp:
            ret = await resp.json()

        return ret['MemberList']

    async def sync_check(self, skey, sid, uin, sync_key):
        params = {
            'r': self.reversed_timestamp,
            'skey': skey,
            'sid': sid,
            'uin': uin,
            'synckey': self.serialize_sync_key(sync_key['List']),
            '_': self.reversed_timestamp,
        }

        async with self._client.get(SYNC_CHECK_URL, params=params) as resp:
            ret = await resp.text()

        m = re.search(
            r'window.synccheck={retcode: "(?P<retcode>\d+)", '
            r'selector: "(?P<selector>\d+)"}', ret)
        return m.group('retcode'), m.group('selector')

    async def sync_data(self, skey, sid, uin, sync_key, pass_ticket):
        params = {
            'skey': skey,
            'pass_ticket': pass_ticket,
            'sid': sid,
        }
        data = self.get_base_request_data(skey, sid, uin)
        data['SyncKey'] = sync_key
        data['rr'] = self.reversed_timestamp

        async with self._client.post(
                SYNC_DATA_URL, params=params, json=data) as resp:
            return await resp.json()

    def __del__(self):
        self._client.close()
