# -*- coding: utf-8 -*-
import functools
import re

from .core import Core
from .exceptions import LoginTimeoutError
from .models.contacts import Contacts, ContactGroup
from .models.user import ChatRoom, create_user, Friend, MP, SpecialAccount, User
from .utils.functional import AsyncObject


class BaseSago:

    def __init__(self, nowait=True):
        self.core = Core()

        self.skey = None
        self.uin = None
        self.pass_ticket = None
        self.sid = None
        self.sync_key = None
        self.user = None
        self.has_logged_in = False

        self.init_contacts()
        self.f = self.login(nowait=nowait)

    def __getattribute__(self, name):
        try:
            return super().__getattribute__(name)
        except AttributeError as ex:
            try:
                a_func = super().__getattribute__('a_' + name)
                return functools.update_wrapper(
                    AsyncObject(a_func, self.core.loop), a_func)
            except AttributeError:
                raise ex

    def init_contacts(self):
        self.contacts = Contacts()
        self.contacts.add('friends', ContactGroup(Friend))
        self.contacts.add('mps', ContactGroup(MP))
        self.contacts.add('chatrooms', ContactGroup(ChatRoom))
        self.contacts.add('special_accounts', ContactGroup(SpecialAccount))

    def run_async(self, method, **kwargs):
        return AsyncObject(method, self.core.loop)(**kwargs)

    def logout(self):
        try:
            self._current_state.cancel()
        except AttributeError:
            pass

        self.has_logged_in = False
        self.init_contacts()

    def login(self, **kwargs):
        self.logout()
        self._current_state = self.run_async(self.a_login, **kwargs)
        return self._current_state

    async def a_login(self):
        uuid = await self.core.request_uuid()
        if not uuid:
            raise ValueError('Request uuid failed.')

        qrcode_storage = self.get_qrcode_storage()
        await self.core.get_login_qrcode(uuid, qrcode_storage)

        login_confirm_url = await self.a_waiting_login_confirm(uuid)
        ret = await self.core.login_confirm(login_confirm_url)

        self.skey = ret['skey']
        self.sid = ret['sid']
        self.uin = ret['uin']
        self.pass_ticket = ret['pass_ticket']

        data = await self.core.init_client(
            self.skey, self.sid, self.uin, self.pass_ticket)
        self.set_user_info(data['user_info'])
        self.sync_key = data['sync_key']

        self.has_logged_in = True

        await self.a_update_all_contacts()
        await self.a_update_chatrooms_info()

    async def a_heart_beat(self):
        while self.has_logged_in:
            retcode, selector = await self.core.sync_check(
                self.skey, self.sid, self.uin, self.sync_key)
            if selector != '2':
                continue

            new_data = await self.core.sync_data(
                self.skey, self.sid, self.uin, self.sync_key, self.pass_ticket)

            if new_data.get('AddMsgList'):
                for msg_data in new_data['AddMsgList']:
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

            elif code == '201':
                tip = 0
                self.qrcode_scanned()

            elif code == '400':
                return self.login()

    async def a_update_contacts(self, *user_id):
        contact_data = await self.core.batch_get_contact(
            self.skey, self.sid, self.uin, self.pass_ticket, *user_id)

        for user_info in contact_data:
            user = self.contacts.search(user_info['UserName'])
            new_user = create_user(user_info, self.skey)
            user.contact_group.add(new_user)
            del user

            if isinstance(new_user, ChatRoom):
                for member_data in user_info['MemberList']:
                    member = self.contacts.get(member_data['UserName'])
                    if not member:
                        member = create_user(member_data, self.skey)

                    new_user.add(member)

    async def a_update_chatrooms_info(self):
        await self.a_update_contacts(
            *[u.id for u in self.contacts.chatrooms.members])

    async def a_update_all_contact(self):
        contact_data = await self.core.request_all_contact(
            self.skey, self.pass_ticket)

        for user_info in contact_data:
            user_info['skey'] = self.skey
            user = create_user(user_info)
            self.contacts.add_user(user)

    def qrcode_scanned(self):
        return

    def login_timeout(self):
        raise LoginTimeoutError('Login timeout.')

    def get_qrcode_storage(self):
        return

    def set_user_info(self, user_info):
        self.user = User(user_info)
