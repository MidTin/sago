# -*- coding: utf-8 -*-
from .user import AbstractUser


class Contact(dict):

    def __init__(self):
        self.count = 0

    def add(self, key, contact_list):
        self[key] = contact_list
        self.count += len(contact_list)

    def __getattribute__(self, name):
        attr = self.get(name)
        if attr:
            return attr

        return super().__getattribute__(name)

    def search(self, key):
        for _list in self.values():
            user = _list.search(key)
            if user:
                return user

    def add_user(self, user):
        for _list in self.values():
            if isinstance(user, _list.member_type):
                _list.add(user)


class ContactList:

    def __init__(self, member_type):
        if not issubclass(member_type, AbstractUser):
            raise TypeError('member_type should be subclass of AbstractUser')

        self.member_type = member_type
        self._members = {}
        self._nick_name_index = {}

    def add(self, *users):
        for u in users:
            if isinstance(u, self.member_type):
                self._members[u.id] = u
                self._nick_name_index[u.nickname] = u

                u.contact_list = self

    def search(self, key):
        user = self._members.get(key)
        if user:
            return user
        else:
            return self._nick_name_index.get(key)

    @property
    def members(self):
        return list(self._members.values())

    def count(self):
        return len(self._members)

    def __len__(self):
        return len(self._members)
