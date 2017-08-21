# -*- coding: utf-8 -*-
import copy

from .user import AbstractUser


class Contact:

    def __init__(self, member_type):
        if not issubclass(member_type, AbstractUser):
            raise TypeError('member_type should be subclass of AbstractUser')

        self.member_type = member_type
        self._members = {}
        self.all_members = []

    def add(self, *users):
        for u in users:
            if isinstance(u, self.member_type):
                self._members[u.id] = u

        self.all_members = []

    def get(self, user_id):
        user = self._members.get(user_id)
        if user:
            return copy.copy(user)

    @property
    def members(self):
        if not self.all_members:
            self.all_members = copy.deepcopy(list(self._members.values()))

        return self.all_members

    def count(self):
        return len(self._members)
