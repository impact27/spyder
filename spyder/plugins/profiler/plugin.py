# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler Plugin.
"""

# Third party imports
from qtpy.QtCore import Signal, Slot

# Local imports
from spyder.api.plugins import Plugins, SpyderDockablePlugin
from spyder.api.plugin_registration.decorators import (
    on_plugin_available, on_plugin_teardown)
from spyder.api.translations import get_translation
from spyder.plugins.mainmenu.api import ApplicationMenus
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import (
    ProfilerWidget, ProfilerToolbarActions)
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.utils.qthelpers import MENU_SEPARATOR
from spyder.config.manager import CONF

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin, ShellConnectMixin):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.Editor, Plugins.IPythonConsole]
    OPTIONAL = [Plugins.MainMenu]
    TABIFY = [Plugins.Help]
    WIDGET_CLASS = ProfilerWidget
    CONF_SECTION = NAME
    CONF_WIDGET_CLASS = ProfilerConfigPage
    CONF_FILE = False

    # --- SpyderDockablePlugin API
    # ------------------------------------------------------------------------
    @staticmethod
    def get_name():
        return _("Profiler")

    def get_description(self):
        return _("Profile your scripts and find bottlenecks.")

    def get_icon(self):
        return self.create_icon('profiler')

    def on_initialize(self):
        pass

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        widget.sig_edit_goto_requested.connect(editor.load)
        # The editor is avilable, connect signal.
        widget.sig_profile_file.connect(self.profile_file)
        widget.sig_profile_cell.connect(self.profile_cell)

        for name in [ProfilerToolbarActions.ProfileCurrentFile,
                     ProfilerToolbarActions.ProfileCurrentCell]:
            action = widget.get_action(name)
            CONF.config_shortcut(
                action.trigger,
                context=self.CONF_SECTION,
                name=name,
                parent=editor)
            self.main.debug_toolbar_actions += [action]

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)
        widget.sig_edit_goto_requested.disconnect(editor.load)
        widget.sig_profile_file.disconnect(self.profile_file)
        widget.sig_profile_cell.disconnect(self.profile_cell)

        names = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell
        ]
        for name in names:
            action = widget.get_action(name)
            self.main.debug_toolbar_actions.remove(action)

    @on_plugin_available(plugin=Plugins.Preferences)
    def on_preferences_available(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.register_plugin_preferences(self)

    @on_plugin_teardown(plugin=Plugins.Preferences)
    def on_preferences_teardown(self):
        preferences = self.get_plugin(Plugins.Preferences)
        preferences.deregister_plugin_preferences(self)

    @on_plugin_available(plugin=Plugins.MainMenu)
    def on_main_menu_available(self):
        widget = self.get_widget()
        profile_file_action = widget.get_action(
            ProfilerToolbarActions.ProfileCurrentFile)
        profile_cell_action = widget.get_action(
            ProfilerToolbarActions.ProfileCurrentCell)

        self.main.run_menu_actions += [
                MENU_SEPARATOR,
                profile_file_action,
                profile_cell_action
            ]

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        mainmenu.remove_item_from_application_menu(
            ProfilerToolbarActions.ProfileCurrentFile,
            menu_id=ApplicationMenus.Run
        )
        mainmenu.remove_item_from_application_menu(
            ProfilerToolbarActions.ProfileCurrentCell,
            menu_id=ApplicationMenus.Run
        )

    # ---- Public API
    # ------------------------------------------------------------------------
    @Slot()
    def profile_file(self):
        """
        Profile current script.

        Should only be called when an editor is avilable.
        """
        editor = self.get_plugin(Plugins.Editor)
        if editor:
            editor.switch_to_plugin()
            editor.run_file(method="profile_file")

    @Slot()
    def profile_cell(self):
        '''
        Profile Current cell.

        Should only be called when an editor is avilable.
        '''
        editor = self.get_plugin(Plugins.Editor)
        if editor:
            editor.run_cell(method="profile_cell")