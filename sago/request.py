# -*- coding: utf-8 -*-

import aiohttp


class AsyncHTTPClient:

    def __init__(self, loop):
        self._loop = loop
        self.session = aiohttp.ClientSession(loop=loop)

    async def request(self, method, url, **kwargs):
        async with self.session.request(method, url, **kwargs) as resp:
            return resp

    async def get(self, url, **kwargs):
        return self.session.get(url, **kwargs)

    async def post(self, url, **kwargs):
        return self.session.post(url, **kwargs)

    def __del__(self):
        self.session.close()
