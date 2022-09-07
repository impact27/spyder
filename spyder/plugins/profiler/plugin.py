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
from spyder.plugins.mainmenu.api import ApplicationMenus, RunMenuSections
from spyder.plugins.profiler.confpage import ProfilerConfigPage
from spyder.plugins.profiler.widgets.main_widget import (
    ProfilerWidget, ProfilerToolbarActions)
from spyder.api.shellconnect.mixins import ShellConnectMixin
from spyder.utils.qthelpers import MENU_SEPARATOR
from spyder.config.manager import CONF
from spyder.plugins.toolbar.api import ApplicationToolbars

# Localization
_ = get_translation('spyder')


# --- Plugin
# ----------------------------------------------------------------------------
class Profiler(SpyderDockablePlugin, ShellConnectMixin):
    """
    Profiler (after python's profile and pstats).
    """

    NAME = 'profiler'
    REQUIRES = [Plugins.Preferences, Plugins.IPythonConsole]
    OPTIONAL = [Plugins.MainMenu, Plugins.Editor,  Plugins.Toolbar]
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
        widget = self.get_widget()
        widget.sig_profile_file.connect(self.profile_file)
        widget.sig_profile_cell.connect(self.profile_cell)
        widget.sig_profile_line.connect(self.profile_line)

    @on_plugin_available(plugin=Plugins.Editor)
    def on_editor_available(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        widget.sig_edit_goto_requested.connect(editor.load)

        # Apply shortcuts to editor and add actions to pythonfile list
        editor_shortcuts = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell,
            ProfilerToolbarActions.ProfileCurrentLine,
        ]
        for name in editor_shortcuts:
            action = widget.get_action(name)
            CONF.config_shortcut(
                action.trigger,
                context=self.CONF_SECTION,
                name=name,
                parent=editor)
            editor.pythonfile_dependent_actions += [action]

    @on_plugin_teardown(plugin=Plugins.Editor)
    def on_editor_teardown(self):
        widget = self.get_widget()
        editor = self.get_plugin(Plugins.Editor)

        widget.sig_edit_goto_requested.disconnect(editor.load)

        editor_shortcuts = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell,
            ProfilerToolbarActions.ProfileCurrentLine,
        ]
        for name in editor_shortcuts:
            action = widget.get_action(name)
            editor.pythonfile_dependent_actions.remove(action)

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
        mainmenu = self.get_plugin(Plugins.MainMenu)
        widget = self.get_widget()

        editor_shortcuts = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell,
            ProfilerToolbarActions.ProfileCurrentLine,
        ]
        for name in editor_shortcuts:
            action = widget.get_action(name)
            mainmenu.add_item_to_application_menu(
                action,
                menu_id=ApplicationMenus.Run,
                section=RunMenuSections.Profile,
            )

    @on_plugin_teardown(plugin=Plugins.MainMenu)
    def on_main_menu_teardown(self):
        mainmenu = self.get_plugin(Plugins.MainMenu)

        editor_shortcuts = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell,
            ProfilerToolbarActions.ProfileCurrentLine,
        ]
        for name in editor_shortcuts:
            mainmenu.remove_item_from_application_menu(
                name,
                menu_id=ApplicationMenus.Run
            )

    @on_plugin_available(plugin=Plugins.Toolbar)
    def on_toolbar_available(self):
        toolbar = self.get_plugin(Plugins.Toolbar)
        widget = self.get_widget()

        editor_shortcuts = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell,
            ProfilerToolbarActions.ProfileCurrentLine,
        ]
        for name in editor_shortcuts:
            toolbar.add_item_to_application_toolbar(
                widget.get_action(name),
                toolbar_id=ApplicationToolbars.Profile
            )

    @on_plugin_teardown(plugin=Plugins.Toolbar)
    def on_toolbar_teardown(self):
        toolbar = self.get_plugin(Plugins.Toolbar)

        editor_shortcuts = [
            ProfilerToolbarActions.ProfileCurrentFile,
            ProfilerToolbarActions.ProfileCurrentCell,
            ProfilerToolbarActions.ProfileCurrentLine,
        ]
        for name in editor_shortcuts:
            toolbar.remove_item_from_application_toolbar(
                name,
                toolbar_id=ApplicationToolbars.Profile
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

    @Slot()
    def profile_line(self):
        '''
        Profile Current line.

        Should only be called when an editor is avilable.
        '''
        editor = self.get_plugin(Plugins.Editor)
        if editor:
            editor.run_selection(prefix="%%profile\n")