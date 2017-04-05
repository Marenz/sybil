from __future__ import absolute_import

import pytest
from _pytest._code.code import TerminalRepr
from _pytest import fixtures
from _pytest.fixtures import FuncFixtureInfo
from _pytest.python import Module

from ..example import SybilFailure


class SybilFailureRepr(TerminalRepr):

    def __init__(self, item, message):
        self.item = item
        self.message = message

    def toterminal(self, tw):
        tw.line()
        for line in self.message.splitlines():
            tw.line(line)
        tw.line()
        tw.write(self.item.parent.name, bold=True, red=True)
        tw.line(":%s: SybilFailure" % self.item.example.line)


class SybilItem(pytest.Item):

    def __init__(self, parent, sybil, example):
        name = 'line:{},column:{}'.format(example.line, example.column)
        super(SybilItem, self).__init__(name, parent)
        self.example = example
        self.request_fixtures(sybil.fixtures)

    def request_fixtures(self, names):
        # pytest fixtures dance:
        fm = self.session._fixturemanager
        names_closure, arg2fixturedefs = fm.getfixtureclosure(names, self)
        fixtureinfo = FuncFixtureInfo(names, names_closure, arg2fixturedefs)
        self._fixtureinfo = fixtureinfo
        self.funcargs = {}
        self._request = fixtures.FixtureRequest(self)

    def reportinfo(self):
        info = '%s line=%i column=%i' % (
            self.fspath.basename, self.example.line, self.example.column
        )
        return self.example.path, self.example.line, info

    def getparent(self, cls):
        if cls is Module:
            return self.parent

    def setup(self):
        fixtures.fillfixtures(self)
        for name, fixture in self.funcargs.items():
            self.example.namespace[name] = fixture

    def runtest(self):
        self.example.evaluate()

    def repr_failure(self, excinfo):
        if isinstance(excinfo.value, SybilFailure):
            return SybilFailureRepr(self, str(excinfo.value))
        return super(SybilItem, self).repr_failure(excinfo)


class SybilFile(pytest.File):

    def __init__(self, path, parent, sybil):
        super(SybilFile, self).__init__(path, parent)
        self.sybil = sybil

    def collect(self):
        self.document = self.sybil.parse(self.fspath.strpath)
        for example in self.document:
            yield SybilItem(self, self.sybil, example)

    def setup(self):
        if self.sybil.setup:
            self.sybil.setup(self.document.namespace)

    def teardown(self):
        if self.sybil.teardown:
            self.sybil.teardown(self.document.namespace)


def pytest_integration(sybil):

    def pytest_collect_file(parent, path):
        if path.fnmatch(sybil.pattern):
            return SybilFile(path, parent, sybil)

    return pytest_collect_file