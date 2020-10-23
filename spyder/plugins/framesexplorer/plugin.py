# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Frames Explorer Plugin."""
# Third party imports
from qtpy.QtCore import Slot, Signal
from qtpy.QtWidgets import QStackedWidget, QVBoxLayout

# Local imports
from spyder.config.base import _
from spyder.api.plugins import SpyderPluginWidget
from spyder.utils import icon_manager as ima
from spyder.plugins.framesexplorer.widgets.framesbrowser import (
        FramesBrowser)
from spyder.plugins.framesexplorer.confpage import FramesExplorerConfigPage


class FramesExplorer(SpyderPluginWidget):
    """Frames Explorer plugin."""

    CONF_SECTION = 'frames_explorer'
    CONFIGWIDGET_CLASS = FramesExplorerConfigPage
    CONF_FILE = False
    DISABLE_ACTIONS_WHEN_HIDDEN = False
    edit_goto = Signal((str, int, str), (str, int, str, bool))
    sig_show_namespace = Signal(dict)

    def __init__(self, parent):
        SpyderPluginWidget.__init__(self, parent)

        # Widgets
        self.stack = QStackedWidget(self)
        self.stack.setStyleSheet("QStackedWidget{padding: 0px; border: 0px}")
        self.shellwidgets = {}

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def register_plugin(self):
        """Register plugin."""
        super(FramesExplorer, self).register_plugin()
        self.edit_goto.connect(self.main.editor.load)
        self.sig_show_namespace.connect(
            lambda view: self.main.variableexplorer.current_widget(
                ).process_remote_view(view))

    def get_settings(self):
        """
        Retrieve all Frames Explorer configuration settings.

        Specifically, return the settings in CONF_SECTION with keys in
        REMOTE_SETTINGS, and the setting 'dataframe_format'.

        Returns:
            dict: settings
        """
        settings = {}
        for name in ['exclude_internal', 'capture_locals']:
            settings[name] = self.get_option(name)
        return settings

    @Slot(str, object)
    def change_option(self, option_name, new_value):
        """
        Change a config option.
        """
        self.sig_option_changed.emit(option_name, new_value)

    # ----- Stack accesors ----------------------------------------------------
    def set_current_widget(self, fsb):
        """Set current widget."""
        self.stack.setCurrentWidget(fsb)
        # We update the actions of the options button (cog menu) and we move
        # it to the layout of the current widget.
        self._refresh_actions()
        fsb.setup_options_button()

    def current_widget(self):
        """Get current widget."""
        return self.stack.currentWidget()

    def count(self):
        """Count number of widgets."""
        return self.stack.count()

    def remove_widget(self, fsb):
        """Remove a widget."""
        self.stack.removeWidget(fsb)

    def add_widget(self, fsb):
        """Add a widget."""
        self.stack.addWidget(fsb)

    # ----- Public API --------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Register shell with frames explorer.

        This function opens a new FramesBrowser for browsing the frames
        in the shell.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self.shellwidgets:
            self.options_button.setVisible(True)
            color_scheme = self.get_color_scheme()
            fsb = FramesBrowser(self, options_button=self.options_button,
                                color_scheme=color_scheme)
            fsb.set_shellwidget(shellwidget)
            fsb.setup(**self.get_settings())
            fsb.sig_option_changed.connect(self.change_option)
            fsb.edit_goto.connect(self.edit_goto)
            fsb.sig_show_namespace.connect(self.sig_show_namespace)
            self.add_widget(fsb)
            self.shellwidgets[shellwidget_id] = fsb
            self.set_shellwidget_from_id(shellwidget_id)
            return fsb

    def remove_shellwidget(self, shellwidget_id):
        """Removes a shellwidget."""
        # If shellwidget_id is not in self.shellwidgets, it simply means
        # that shell was not a Python-based console (it was a terminal)
        if shellwidget_id in self.shellwidgets:
            fsb = self.shellwidgets.pop(shellwidget_id)
            self.remove_widget(fsb)
            fsb.close()

    def set_shellwidget_from_id(self, shellwidget_id):
        """Sets the current shellwidget."""
        if shellwidget_id in self.shellwidgets:
            fsb = self.shellwidgets[shellwidget_id]
            self.set_current_widget(fsb)

    # ----- SpyderPluginWidget API --------------------------------------------
    def get_plugin_title(self):
        """Return widget title"""
        return _('Frames explorer')

    def get_plugin_icon(self):
        """Return plugin icon"""
        return ima.icon('dictedit')

    def get_focus_widget(self):
        """
        Return the widget to give focus to when
        this plugin's dockwidget is raised on top-level
        """
        return self.current_widget()

    def get_plugin_actions(self):
        """Return a list of actions related to plugin"""
        return self.current_widget().actions if self.current_widget() else []

    def apply_plugin_settings(self, options):
        """Apply configuration file's plugin settings"""
        for fsb in list(self.shellwidgets.values()):
            fsb.setup(**self.get_settings())
