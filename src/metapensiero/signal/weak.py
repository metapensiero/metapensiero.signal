# -*- coding: utf-8 -*-
# :Project:   metapensiero.signal -- weak ref derived classes
# :Created:   mer 16 dic 2015 12:30:10 CET
# :Author:    Alberto Berti <alberto@metapensiero.it>
# :License:   GNU General Public License version 3 or later
# :Copyright: Copyright (C) 2015 Alberto Berti
#

from collections import OrderedDict
import inspect
import weakref


class MethodAwareWeakSet(weakref.WeakSet):
    """A WeakSet than can take instance method as member"""

    def add(self, item):
        """A customized add that tests item and if it's a method uses a
        proper weakref.
        """
        # unfortunately i have to reimplement the method completely
        if self._pending_removals:
            self._commit_removals()
        if inspect.ismethod(item):
            ref = weakref.WeakMethod
        else:
            ref = weakref.ref
        self.data.add(ref(item, self._remove))


class MethodAwareWeakKeyOrderedDict(weakref.WeakKeyDictionary):
    """A version of :class:`weakref.WeakKeyDictionary` object that uses a
    :class:`collections.OrderedDict` to store its data and also uses dedicated
    references for instance methods.
    """

    def __init__(self, dict=None):
        super(MethodAwareWeakKeyOrderedDict, self).__init__(dict)
        self.data = OrderedDict()
        if dict is not None:
            self.update(dict)

    def __contains__(self, key):
        try:
            wr = self._ref(key)
        except TypeError:
            return False
        return wr in self.data

    def __delitem__(self, key):
        self._dirty_len = True
        del self.data[self._ref(key)]

    def __getitem__(self, key):
        return self.data[self._ref(key)]

    def __setitem__(self, key, value):
        self.data[self._ref(key, self._remove)] = value

    def _ref(self, obj, *args, **kwargs):
        if inspect.ismethod(obj):
            ref = weakref.WeakMethod
        else:
            ref = weakref.ref
        return ref(obj, *args, **kwargs)

    def copy(self):
        new = MethodAwareWeakKeyOrderedDict()
        for key, value in self.data.items():
            o = key()
            if o is not None:
                new[o] = value
        return new

    __copy__ = copy

    def get(self, key, default=None):
        return self.data.get(self._ref(key), default)

    def pop(self, key, *args):
        self._dirty_len = True
        return self.data.pop(self._ref(key), *args)

    def setdefault(self, key, default=None):
        return self.data.setdefault(self._ref(key, self._remove), default)

    def update(self, dict=None, **kwargs):
        d = self.data
        if dict is not None:
            if not hasattr(dict, "items"):
                dict = type({})(dict)
            for key, value in dict.items():
                d[self._ref(key, self._remove)] = value
        if len(kwargs):
            self.update(kwargs)
