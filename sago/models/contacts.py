# -*- coding: utf-8 -*-
from .user import AbstractUser


class Contacts(dict):

    def __init__(self):
        self.count = 0

    def add(self, key, contact_group):
        self[key] = contact_group
        self.count += len(contact_group)

    def __getattribute__(self, name):
        try:
            return self[name]
        except KeyError:
            return super().__getattribute__(name)

    def search(self, key):
        for group in self.values():
            user = group.search(key)
            if user:
                return user

    def add_user(self, user):
        for group in self.values():
            if isinstance(user, group.member_type):
                group.add(user)
                self.count += 1

    def __repr__(self):
        return '<Contacts members: %d>' % self.count


class ContactGroup:

    def __init__(self, member_type):
        if not issubclass(member_type, AbstractUser):
            raise TypeError('member_type should be subclass of AbstractUser')

        self.member_type = member_type
        self._members = {}
        self._nick_name_index = {}
        self._count = 0

    def add(self, *users):
        for u in users:
            if isinstance(u, self.member_type):
                self._members[u.uid] = u
                self._nick_name_index[u.nickname] = u

                u.contact_group = self
                self._count += 1

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
        return self._count

    def __len__(self):
        return self._count

    def __repr__(self):
        return str(self.members)
