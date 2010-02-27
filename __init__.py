#! /usr/bin/env python
# -*- coding: utf-8 -*-

# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
# MA 02110-1301, USA.

from cream.util import cached_property

from .base import Component

CONFIG_AUTOSAVE = True

class Module(Component):
    """ Baseclass for all modules... """

    def main(self):
        """ Run a GLib-mainloop. """

        import gobject
        gobject.threads_init()

        self._mainloop = gobject.MainLoop()
        try:
            self._mainloop.run()
        except (SystemError, KeyboardInterrupt), e:
            # shut down gracefully.
            self.quit()
            raise e


    @cached_property
    def messages(self):
        from cream.log import Messages
        return Messages(id=self._bus_name)


    def quit(self):
        self._autosave()
        self._mainloop.quit()

