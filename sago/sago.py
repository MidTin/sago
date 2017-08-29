# -*- coding: utf-8 -*-
import functools
import re

from .core import Core
from .exceptions import LoginTimeoutError
from .loop import EventLoop
from .models.contact import Contact, ContactList
from .models.user import ChatRoom, create_user, Friend, MP, SpecialAccount, User
from .utils.functional import AsyncObject


class BaseSago:

    def __init__(self, nowait=True):
        self.loop = EventLoop()
        self.core = Core(loop=self.loop)

        self.skey = None
        self.uin = None
        self.pass_ticket = None
        self.sid = None
        self.sync_key = None

        self.user = None

        self.has_logged_in = False
        self.contact = Contact()
        self.contact.add('friends', ContactList(Friend))
        self.contact.add('mps', ContactList(MP))
        self.contact.add('chatrooms', ContactList(ChatRoom))
        self.contact.add('special_accounts', ContactList(SpecialAccount))

        self.f = self.login(nowait=nowait)

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError as ex:
            try:
                a_func = super().__getattribute__('a_' + name)
                return functools.update_wrapper(
                    AsyncObject(a_func, self.loop), a_func)
            except AttributeError:
                raise ex

    async def a_login(self):
        import time
        start = int(time.time())
        uuid = await self.core.request_uuid()
        if not uuid:
            raise ValueError('Request uuid failed.')

        print('Fetch uuid finished in %ds' % (int(time.time()) - start))

        qrcode_storage = self.get_qrcode_storage()
        await self.core.get_login_qrcode(uuid, qrcode_storage)

        login_confirm_url = await self.a_waiting_login_confirm(uuid)
        start = int(time.time())
        ret = await self.core.login_confirm(login_confirm_url)
        print('login confirm finished in %ds' % (int(time.time()) - start))

        self.skey = ret['skey']
        self.sid = ret['sid']
        self.uin = ret['uin']
        self.pass_ticket = ret['pass_ticket']

        start = int(time.time())
        data = await self.core.init_client(
            self.skey, self.sid, self.uin, self.pass_ticket)
        print('init client finished in %ds' % (int(time.time()) - start))
        self.set_user_info(data['user_info'])
        self.sync_key = data['sync_key']

        self.has_logged_in = True

        await self.a_update_all_contact()
        await self.a_update_chatrooms_info()

    async def a_heart_beat(self):
        while self.has_logged_in:
            pass

    async def a_waiting_login_confirm(self, uuid):
        tip = 1
        while True:
            ret = await self.core.listen_qrcode_scanned(uuid, tip)
            m = re.search(r'window.code=(?P<code>\d+);', ret)
            code = m.group('code')
            if code == '200':
                m = re.search(
                    r'window.redirect_uri="(?P<redirect_uri>\S+)";', ret)
                return m.group('redirect_uri')

            if code == '201':
                tip = 0
                self.qrcode_scanned()

    async def a_update_contact(self, *user_id):
        contact_data = await self.core.batch_get_contact(
            self.skey, self.sid, self.uin, self.pass_ticket, *user_id)

        for user_info in contact_data:
            user = self.contact.search(user_info['UserName'])
            new_user = create_user(user_info)
            user.contact_list.add(new_user)
            del user

            if isinstance(new_user, ChatRoom):
                for member_data in user_info['MemberList']:
                    member = self.contact.get(member_data['UserName'])
                    if not member:
                        member = create_user(member_data)

                    new_user.add(member)

    async def a_update_chatrooms_info(self):
        await self.a_update_contact(
            *[u.id for u in self.contact.chatrooms.members])

    async def a_update_all_contact(self):
        contact_data = await self.core.request_all_contact(
            self.skey, self.pass_ticket)

        for user_info in contact_data:
            user = create_user(user_info)
            self.contact.add_user(user)

    def qrcode_scanned(self):
        return

    def login_timeout(self):
        raise LoginTimeoutError('Login timeout.')

    def get_qrcode_storage(self):
        return

    def set_user_info(self, user_info):
        self.user = User(user_info)
