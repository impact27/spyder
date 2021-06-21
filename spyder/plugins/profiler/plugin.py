# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler Plugin.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.translations import get_translation
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import (ProfilerWidget,
                                                         ProfilerWidgetActions)
from spyder.plugins.run.widgets import get_run_configuration

# Localization
_ = get_translation('spyder')


# --- Constants
# ----------------------------------------------------------------------------
class ProfilerActions:
    ProfileCurrentFile = 'profile_current_filename_action'
    ProfileCurrentCell = 'profile_current_cell_action'


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.Editor]
    OPTIONAL = [Plugins.MainMenu, Plugins.IPythonConsole]
    TABIFY = Plugins.Help
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # --- Signals
    # ------------------------------------------------------------------------
    sig_profile_file = Signal()
    """This signal is emitted to request the current file to be profiled."""

    sig_profile_cell = Signal()
    """This signal is emitted to request the current cell to be profiled."""

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    def get_name(self):
        return _("Profiler")

    def get_description(self):
        return _("Profile your scripts and find bottlenecks.")

    def get_icon(self):
        return self.create_icon('profiler')

    def register(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        mainmenu = self.get_plugin(Plugins.MainMenu)
        preferences = self.get_plugin(Plugins.Preferences)
        ipythonconsole = self.get_plugin(Plugins.IPythonConsole)

        preferences.register_plugin_preferences(self)
        widget.sig_edit_goto_requested.connect(editor.load)
        profile_file_action = self.create_action(
            ProfilerActions.ProfileCurrentFile,
            text=_("Profile file"),
            tip=_("Profile file"),
            icon=self.create_icon('profiler'),
            triggered=self.sig_profile_file.emit,
            register_shortcut=True,
        )

        profile_cell_action = self.create_action(
            ProfilerActions.ProfileCurrentCell,
            text=_("Profile cell"),
            tip=_("Profile cell"),
            icon=self.create_icon('profiler'),
            triggered=self.sig_profile_cell.emit,
            register_shortcut=True,
        )

        if ipythonconsole:
            ipythonconsole.sig_show_profile_file.connect(
                self.show_profile_file)
        if editor:
            self.sig_profile_file.connect(editor.profile_file)
            self.sig_profile_cell.connect(editor.profile_cell)

        if mainmenu:
            run_menu = mainmenu.get_application_menu(ApplicationMenus.Run)
            for action in [
                    profile_file_action, profile_cell_action]:
                mainmenu.add_item_to_application_menu(
                    action, menu=run_menu,
                    section=RunMenuSections.Profile)

        # TODO: On a separate PR when core plugin is merged
        # self.main.editor.pythonfile_dependent_actions += [profiler_act]

    # --- Public API
    # ------------------------------------------------------------------------
    def show_profile_file(self, filename):
        """
        Show profile sent by shell.

        Parameters
        ----------
        filename: str
            Path to file to analyze.
        """
        self.switch_to_plugin()
        self.get_widget().show_profile_file(filename)
