# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based on pylintgui.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler widget.

See the official documentation on python profiling:
https://docs.python.org/3/library/profile.html
"""

# Standard library imports
import logging
import os
import sys

# Third party imports
from qtpy.compat import getopenfilename, getsavefilename
from qtpy.QtCore import Signal
from qtpy.QtWidgets import QLabel

# Local imports
from spyder.api.translations import get_translation
from spyder.utils.misc import getcwd_or_home, get_python_executable
from spyder.utils.palette import QStylePalette
from spyder.api.shellconnect.main_widget import ShellConnectMainWidget
from spyder.plugins.profiler.widgets.profiler_data_tree import (
    ProfilerSubWidget)

# Localization
_ = get_translation('spyder')

# Logging
logger = logging.getLogger(__name__)


# --- Constants
# ----------------------------------------------------------------------------
MAIN_TEXT_COLOR = QStylePalette.COLOR_TEXT_1


class ProfilerWidgetActions:
    # Triggers
    Browse = 'browse_action'
    Clear = 'clear_action'
    Collapse = 'collapse_action'
    Expand = 'expand_action'
    ToggleTreeDirection = "tree_direction_action"
    ToggleBuiltins = "toggle_builtins_action"
    Home = "HomeAction"
    SlowLocal = 'slow_local_action'
    LoadData = 'load_data_action'
    Run = 'run_action'
    SaveData = 'save_data_action'
    ShowOutput = 'show_output_action'
    Search = "find_action"
    Undo = "undo_action"
    Redo = "redo_action"


class ProfilerToolbarActions:
    ProfileCurrentFile = 'profile file'
    ProfileCurrentCell = 'profile cell'


class ProfilerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class ProfilerContextMenuSections:
    Locals = 'locals_section'


class ProfilerWidgetContextMenuActions:
    ShowCallees = "show_callees_action"
    ShowCallers = "show_callers_action"


class ProfilerWidgetToolbars:
    Information = 'information_toolbar'


class ProfilerWidgetMainToolbarSections:
    Main = 'main_section'


class ProfilerWidgetInformationToolbarSections:
    Main = 'main_section'


class ProfilerWidgetMainToolbarItems:
    FileCombo = 'file_combo'


class ProfilerWidgetInformationToolbarItems:
    Stretcher1 = 'stretcher_1'
    Stretcher2 = 'stretcher_2'
    DateLabel = 'date_label'


# --- Widgets
# ----------------------------------------------------------------------------
class ProfilerWidget(ShellConnectMainWidget):
    """
    Profiler widget.
    """

    # --- Signals
    # ------------------------------------------------------------------------
    sig_edit_goto_requested = Signal(str, int, str)
    """
    This signal will request to open a file in a given row and column
    using a code editor.

    Parameters
    ----------
    path: str
        Path to file.
    row: int
        Cursor starting row position.
    word: str
        Word to select on given row.
    """

    sig_profile_file = Signal()
    """This signal is emitted to request the current file to be profiled."""

    sig_profile_cell = Signal()
    """This signal is emitted to request the current cell to be profiled."""

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)
        self.set_conf('text_color', MAIN_TEXT_COLOR)

        # Attributes
        self.text_color = self.get_conf('text_color')

        # Widgets
        self.datelabel = QLabel()
        self.datelabel.ID = ProfilerWidgetInformationToolbarItems.DateLabel

    # --- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Profiler')

    def setup(self):
        self.collapse_action = self.create_action(
            ProfilerWidgetActions.Collapse,
            text=_('Collapse'),
            tip=_('Collapse one level up'),
            icon=self.create_icon('collapse'),
            triggered=lambda x=None: self.current_widget(
                ).data_tree.change_view(-1),
        )
        self.expand_action = self.create_action(
            ProfilerWidgetActions.Expand,
            text=_('Expand'),
            tip=_('Expand one level down'),
            icon=self.create_icon('expand'),
            triggered=lambda x=None: self.current_widget(
                ).data_tree.change_view(1),
        )
        self.home_action = self.create_action(
            ProfilerWidgetActions.Home,
            text=_("Reset tree"),
            tip=_('Go back to full tree'),
            icon=self.create_icon('home'),
            triggered=self.home_tree,
        )
        self.toggle_tree_action = self.create_action(
            ProfilerWidgetActions.ToggleTreeDirection,
            text=_("Switch tree direction"),
            tip=_('Switch tree direction between callers and callees'),
            icon=self.create_icon('swap'),
            toggled=self.toggle_tree,
        )
        self.slow_local_action = self.create_action(
            ProfilerWidgetActions.SlowLocal,
            text=_("Show items with large local time"),
            tip=_('Show items with large local time'),
            icon=self.create_icon('slow'),
            triggered=self.slow_local_tree,
        )
        self.toggle_builtins_action = self.create_action(
            ProfilerWidgetActions.ToggleBuiltins,
            text=_("Hide builtins"),
            tip=_('Hide builtins'),
            icon=self.create_icon('hide'),
            toggled=self.toggle_builtins,
        )
        self.save_action = self.create_action(
            ProfilerWidgetActions.SaveData,
            text=_("Save data"),
            tip=_('Save profiling data'),
            icon=self.create_icon('filesave'),
            triggered=self.save_data,
        )
        self.load_action = self.create_action(
            ProfilerWidgetActions.LoadData,
            text=_("Load data"),
            tip=_('Load profiling data for comparison'),
            icon=self.create_icon('fileimport'),
            triggered=self.compare,
        )
        self.clear_action = self.create_action(
            ProfilerWidgetActions.Clear,
            text=_("Clear comparison"),
            tip=_("Clear comparison"),
            icon=self.create_icon('editdelete'),
            triggered=self.clear,
        )
        self.clear_action.setEnabled(False)
        search_action = self.create_action(
            ProfilerWidgetActions.Search,
            text=_("Search"),
            icon=self.create_icon('find'),
            toggled=self.toggle_finder,
            register_shortcut=True
        )
        undo_action = self.create_action(
            ProfilerWidgetActions.Undo,
            text=_("Previous View"),
            icon=self.create_icon('undo'),
            triggered=self.undo,
            register_shortcut=True
        )
        redo_action = self.create_action(
            ProfilerWidgetActions.Redo,
            text=_("Next View"),
            icon=self.create_icon('redo'),
            triggered=self.redo,
            register_shortcut=True
        )

        # Toolbar
        toolbar = self.get_main_toolbar()
        for item in [
                self.collapse_action,
                self.expand_action,
                undo_action,
                redo_action,
                self.home_action,
                self.toggle_tree_action,
                self.toggle_builtins_action,
                self.slow_local_action,
                search_action,
                self.create_stretcher(
                    id_=ProfilerWidgetInformationToolbarItems.Stretcher1),
                self.create_stretcher(
                    id_=ProfilerWidgetInformationToolbarItems.Stretcher2),
                self.save_action,
                self.load_action,
                self.clear_action
                ]:
            self.add_item_to_toolbar(
                item,
                toolbar=toolbar,
                section=ProfilerWidgetInformationToolbarSections.Main,
            )
        # ---- Context menu actions
        self.show_callees_action = self.create_action(
            ProfilerWidgetContextMenuActions.ShowCallees,
            _("Show callees"),
            icon=self.create_icon('2downarrow'),
            triggered=self.show_callees
        )
        self.show_callers_action = self.create_action(
            ProfilerWidgetContextMenuActions.ShowCallers,
            _("Show callers"),
            icon=self.create_icon('2uparrow'),
            triggered=self.show_callers
        )
        # ---- Context menu to show when there are frames present
        self.context_menu = self.create_menu(
            ProfilerWidgetMenus.PopulatedContextMenu)
        for item in [self.show_callers_action, self.show_callees_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=ProfilerContextMenuSections.Locals,
            )

        # toolbar
        self.create_action(
            ProfilerToolbarActions.ProfileCurrentFile,
            text=_("Profile file"),
            tip=_("Profile file"),
            icon=self.create_icon('profiler'),
            triggered=self.sig_profile_file,
            register_shortcut=True,
        )
        self.create_action(
            ProfilerToolbarActions.ProfileCurrentCell,
            text=_("Profile cell"),
            tip=_("Profile cell"),
            icon=self.create_icon('profile_cell'),
            triggered=self.sig_profile_cell,
            register_shortcut=True,
        )

    def update_actions(self):
        """Update actions."""
        widget = self.current_widget()
        search_action = self.get_action(ProfilerWidgetActions.Search)
        toggle_tree_action = self.get_action(
            ProfilerWidgetActions.ToggleTreeDirection)
        toggle_builtins_action = self.get_action(
            ProfilerWidgetActions.ToggleBuiltins)

        if widget is None:
            search = False
            inverted_tree = False
            ignore_builtins = False
        else:
            search = widget.finder_is_visible()
            inverted_tree = widget.data_tree.inverted_tree
            ignore_builtins = widget.data_tree.ignore_builtins

        search_action.setChecked(search)
        toggle_tree_action.setChecked(inverted_tree)
        toggle_builtins_action.setChecked(ignore_builtins)

    # --- Public API
    # ------------------------------------------------------------------------
    def home_tree(self):
        """Invert tree."""
        self.current_widget().data_tree.home_tree()

    def toggle_tree(self, state):
        """Invert tree."""
        widget = self.current_widget().data_tree
        widget.inverted_tree = state
        widget.refresh_tree()

    def toggle_builtins(self, state):
        """Invert tree."""
        widget = self.current_widget().data_tree
        widget.ignore_builtins = state
        widget.refresh_tree()

    def slow_local_tree(self):
        """Show items with large local times"""
        self.current_widget().data_tree.show_slow()

    def undo(self):
        """Undo change."""
        self.current_widget().data_tree.undo()

    def redo(self):
        """Redo changes."""
        self.current_widget().data_tree.redo()

    def show_callers(self):
        """Invert tree."""
        widget = self.current_widget().data_tree
        widget.show_selected()
        if not self.toggle_tree_action.isChecked():
            self.toggle_tree_action.setChecked(True)

    def show_callees(self):
        """Invert tree."""
        widget = self.current_widget().data_tree
        widget.show_selected()
        if self.toggle_tree_action.isChecked():
            self.toggle_tree_action.setChecked(False)

    def save_data(self):
        """Save data."""
        title = _( "Save profiler result")
        filename, _selfilter = getsavefilename(
            self,
            title,
            getcwd_or_home(),
            _("Profiler result") + " (*.Result)",
        )

        if filename:
            self.current_widget().data_tree.save_data(filename)

    def compare(self):
        """Compare previous saved run with last run."""
        filename, _selfilter = getopenfilename(
            self,
            _("Select script to compare"),
            getcwd_or_home(),
            _("Profiler result") + " (*.Result)",
        )

        if filename:
            self.current_widget().data_tree.compare(filename)
            self.current_widget().data_tree.home_tree()
            self.clear_action.setEnabled(True)

    def clear(self):
        """Clear data in tree."""
        self.current_widget().data_tree.compare(None)
        self.current_widget().data_tree.home_tree()
        self.clear_action.setEnabled(False)

    def create_new_widget(self, shellwidget):
        """Create new profiler widget."""
        widget = ProfilerSubWidget(self)
        widget.sig_edit_goto_requested.connect(self.sig_edit_goto_requested)
        widget.sig_display_requested.connect(self.display_request)
        widget.set_context_menu(self.context_menu)
        widget.sig_hide_finder_requested.connect(self.hide_finder)

        shellwidget.spyder_kernel_comm.register_call_handler(
            "show_profile_file", widget.show_profile_buffer)
        widget.shellwidget = shellwidget

        return widget

    def close_widget(self, widget):
        """Close profiler widget."""
        widget.sig_edit_goto_requested.disconnect(
            self.sig_edit_goto_requested)
        widget.sig_display_requested.disconnect(self.display_request)
        widget.sig_hide_finder_requested.disconnect(self.hide_finder)

        # Unregister
        widget.shellwidget.spyder_kernel_comm.register_call_handler(
            "show_profile_file", None)
        widget.setParent(None)
        widget.close()

    def switch_widget(self, widget, old_widget):
        """Switch widget."""
        pass

    def display_request(self, widget):
        """
        Display request from ProfilerDataTree.

        Only display if this is the current widget.
        """
        if self.current_widget() is widget:
            self.get_plugin().switch_to_plugin()

    def toggle_finder(self, checked):
        """Show or hide finder."""
        widget = self.current_widget()
        if widget is None:
            return
        widget.toggle_finder(checked)

    def hide_finder(self):
        """Hide finder."""
        action = self.get_action(ProfilerWidgetActions.Search)
        action.setChecked(False)


# =============================================================================
# Tests
# =============================================================================
def primes(n):
    """
    Simple test function
    Taken from http://www.huyng.com/posts/python-performance-analysis/
    """
    if n == 2:
        return [2]
    elif n < 2:
        return []
    s = list(range(3, n + 1, 2))
    mroot = n ** 0.5
    half = (n + 1) // 2 - 1
    i = 0
    m = 3
    while m <= mroot:
        if s[i]:
            j = (m * m - 3) // 2
            s[j] = 0
            while j < half:
                s[j] = 0
                j += m
        i = i + 1
        m = 2 * i + 3
    return [2] + [x for x in s if x]


def test():
    """Run widget test"""
    from spyder.utils.qthelpers import qapplication
    import inspect
    import tempfile
    from unittest.mock import MagicMock

    primes_sc = inspect.getsource(primes)
    fd, script = tempfile.mkstemp(suffix='.py')
    with os.fdopen(fd, 'w') as f:
        f.write("# -*- coding: utf-8 -*-" + "\n\n")
        f.write(primes_sc + "\n\n")
        f.write("primes(100000)")

    plugin_mock = MagicMock()
    plugin_mock.CONF_SECTION = 'profiler'

    app = qapplication(test_time=5)
    widget = ProfilerWidget('test', plugin=plugin_mock)
    widget._setup()
    widget.setup()
    widget.get_conf('executable', get_python_executable(),
                    section='main_interpreter')
    widget.resize(800, 600)
    widget.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    test()
