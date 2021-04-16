# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Frames Explorer Plugin."""
# Local imports
from spyder.config.base import _
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.plugins.framesexplorer.confpage import FramesExplorerConfigPage
from spyder.plugins.framesexplorer.widgets.main_widget import (
    FramesExplorerWidget)


class FramesExplorer(SpyderDockablePlugin):
    """Frames Explorer plugin."""

    NAME = 'frames_explorer'
    REQUIRES = [Plugins.IPythonConsole, Plugins.Preferences,
                Plugins.Editor]
    TABIFY = None
    WIDGET_CLASS = FramesExplorerWidget
    CONF_SECTION = NAME
    CONF_FILE = False
    CONF_WIDGET_CLASS = FramesExplorerConfigPage
    DISABLE_ACTIONS_WHEN_HIDDEN = False

    # ---- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _('Frames explorer')

    def get_description(self):
        return _('Display, explore frames in the current kernel.')

    def get_icon(self):
        return self.create_icon('dictedit')

    def register(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        editor = self.get_plugin(Plugins.Editor)
        preferences = self.get_plugin(Plugins.Preferences)

        # Preferences
        preferences.register_plugin_preferences(self)

        # Signals
        ipyconsole.sig_shellwidget_changed.connect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_process_started.connect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_process_finished.connect(
            self.remove_shellwidget)
        ipyconsole.sig_shellwidget_external_connect.connect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_external_disconnect.connect(
            self.remove_shellwidget)

        if editor:
            self.get_widget().edit_goto.connect(editor.load)

    def unregister(self):
        # Plugins
        ipyconsole = self.get_plugin(Plugins.IPythonConsole)
        editor = self.get_plugin(Plugins.Editor)

        # Signals
        ipyconsole.sig_shellwidget_changed.disconnect(self.set_shellwidget)
        ipyconsole.sig_shellwidget_process_started.disconnect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_process_finished.disconnect(
            self.remove_shellwidget)
        ipyconsole.sig_shellwidget_external_connect.disconnect(
            self.add_shellwidget)
        ipyconsole.sig_shellwidget_external_disconnect.disconnect(
            self.remove_shellwidget)
        if editor:
            self.edit_goto.disconnect(editor.load)

    # ---- Public API
    # ------------------------------------------------------------------------
    def current_widget(self):
        """
        Return the current widget displayed at the moment.

        Returns
        -------
        spyder.plugins.spyder.plugins.framesexplorer.widgets.framesbrowser.
            FramesBrowser
        """
        return self.get_widget().current_widget()

    def set_shellwidget(self, shelwidget):
        """
        Update the current shellwidget associated to the Frames Explorer.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().set_shellwidget(shelwidget)

    def add_shellwidget(self, shelwidget):
        """
        Add a new shellwidget to be registered with the Frames Explorer.

        This function registers a new NamespaceBrowser for browsing variables
        in the shellwidget.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().add_shellwidget(shelwidget)

    def remove_shellwidget(self, shelwidget):
        """
        Remove the shellwidget registered with the Frames Explorer.

        Parameters
        ----------
        shellwidget: spyder.plugins.ipyconsole.widgets.shell.ShellWidget
            The shell widget.
        """
        self.get_widget().remove_shellwidget(shelwidget)
