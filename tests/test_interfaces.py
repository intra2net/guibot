#!/usr/bin/python3
# Copyright 2013-2023 Intranet AG and contributors
#
# guibot is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# guibot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with guibot.  If not, see <http://www.gnu.org/licenses/>.

import sys
import inspect
from unittest import main, mock, TestCase

import common_test


class SimpleAPITest(TestCase):

    def setUp(self) -> None:
        from guibot import guibot_simple as simple
        simple.guibot = mock.MagicMock()
        simple.check_initialized = mock.MagicMock()
        self.interface = simple

    def test_call_delegations(self) -> None:
        """Test that all calls from the interface to the actual object are valid."""
        args = [True, 1, 2.0, "test-args"]
        kwargs = {"bool": False, "int": 0, "float": 3.0, "str": "test-kwargs"}
        for funcname in dir(self.interface):
            func = self.interface.__dict__[funcname]
            if not inspect.isfunction(func):
                continue
            if funcname in ["initialize", "check_initialized", "namedtuple"]:
                continue

            func(args, kwargs)

            self.interface.check_initialized.assert_called_once()
            method_calls = self.interface.guibot.method_calls
            self.assertEqual(len(method_calls), 1)
            self.assertEqual(len(method_calls[0]), 3)
            self.assertEqual(method_calls[0][0], funcname)
            self.assertEqual(method_calls[0][1], (args, kwargs))
            self.interface.guibot.reset_mock()
            self.interface.check_initialized.reset_mock()

    @mock.patch("guibot.guibot_simple.GuiBot")
    def test_key_imports(self, mock_guibot) -> None:
        """Test that all keys imported by the simple interface work."""
        self.interface.initialize()
        mock_guibot.return_value.dc_backend.keymap.ESC = "esc"
        mock_guibot.return_value.dc_backend.modmap.MOD_SHIFT = ""
        mock_guibot.return_value.dc_backend.mousemap.LEFT_BUTTON = 1

        buttons = self.interface.buttons
        self.assertEqual(buttons.key.ESC, "esc")
        self.assertEqual(buttons.mod.MOD_SHIFT, "")
        self.assertEqual(buttons.mouse.LEFT_BUTTON, 1)


class ProxyAPITest(TestCase):

    def setUp(self) -> None:
        # fake the remote objects dependency for this interface
        sys.modules["Pyro4"] = mock.MagicMock()
        from guibot import guibot_proxy as remote
        self.interface = remote.GuiBotProxy(cv=None, dc=None)
        self.interface._proxify = mock.MagicMock()

    def tearDown(self) -> None:
        del sys.modules["Pyro4"]

    @mock.patch('guibot.guibot_proxy.super')
    def test_call_delegations(self, mock_super) -> None:
        """Test that all calls from the interface to the actual object are valid."""
        args = [True, 1, 2.0, "test-args"]
        kwargs = {"bool": False, "int": 0, "float": 3.0, "str": "test-kwargs"}
        for funcname in dir(self.interface):
            # instance __dict__ will only include its attributes
            dirdict = type(self.interface).__dict__
            if funcname not in dirdict:
                continue
            func = dirdict[funcname]
            if not inspect.isfunction(func):
                continue
            if funcname in ["__init__", "_proxify"]:
                continue

            func(self.interface, args, kwargs)

            if funcname != "find_all":
                self.interface._proxify.assert_called_once()
            method_calls = mock_super.return_value.method_calls
            self.assertEqual(len(method_calls), 1)
            self.assertEqual(len(method_calls[0]), 3)
            self.assertEqual(method_calls[0][0], funcname)
            self.assertEqual(method_calls[0][1], (args, kwargs))
            mock_super.reset_mock()
            self.interface._proxify.reset_mock()


if __name__ == '__main__':
    main()
