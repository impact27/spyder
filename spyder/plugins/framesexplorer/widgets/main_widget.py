# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Frames Explorer Main Plugin Widget.
"""

# Third party imports
from qtpy.QtCore import Signal, Slot
from qtpy.QtWidgets import (
    QHBoxLayout, QStackedWidget, QVBoxLayout, QWidget)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.translations import get_translation
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.manager import CONF
from spyder.config.gui import get_color_scheme
from spyder.plugins.framesexplorer.widgets.framesbrowser import (
    FramesBrowser,
    FramesBrowserFinder,
    VALID_VARIABLE_CHARS)

# Localization
_ = get_translation('spyder')


# =============================================================================
# ---- Constants
# =============================================================================
class FramesExplorerWidgetActions:
    # Triggers
    Search = 'search'
    Refresh = 'refresh'

    # Toggles
    ToggleExcludeInternal = 'toggle_exclude_internal_action'
    ToggleCaptureLocals = 'toggle_capture_locals_action'


class FramesExplorerWidgetOptionsMenuSections:
    Display = 'excludes_section'
    Highlight = 'highlight_section'


class FramesExplorerWidgetMainToolBarSections:
    Main = 'main_section'


class FramesExplorerWidgetMenus:
    EmptyContextMenu = 'empty'
    PopulatedContextMenu = 'populated'


class FramesExplorerContextMenuActions:
    ViewLocalsAction = 'view_locals_action'


class FramesExplorerContextMenuSections:
    Locals = 'locals_section'


# =============================================================================
# ---- Widgets
# =============================================================================
class FramesStackedWidget(QStackedWidget):
    # Signals
    edit_goto = Signal((str, int, str), (str, int, str, bool))
    sig_show_namespace = Signal(dict)
    sig_hide_finder_requested = Signal()

    def __init__(self, parent):
        super().__init__(parent=parent)

    def addWidget(self, widget):
        """
        Override Qt method.
        """
        if isinstance(widget, FramesBrowser):
            widget.edit_goto.connect(
                self.edit_goto)
            widget.sig_show_namespace.connect(
                self.sig_show_namespace)
            widget.sig_hide_finder_requested.connect(
                self.sig_hide_finder_requested)

        super().addWidget(widget)


class FramesExplorerWidget(PluginMainWidget):

    # PluginMainWidget class constants
    ENABLE_SPINNER = True

    # Signals
    edit_goto = Signal((str, int, str), (str, int, str, bool))

    def __init__(self, name=None, plugin=None, parent=None):
        super().__init__(name, plugin, parent)

        # Widgets
        self._stack = FramesStackedWidget(self)
        self._shellwidgets = {}
        self.context_menu = None
        self.empty_context_menu = None

        # --- Finder
        self.finder = None

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self._stack)
        # Note: Later with the addition of the first FramesBrowser the
        # find/search widget is added. See 'set_current_widget'
        self.setLayout(layout)

        # Signals
        self._stack.edit_goto.connect(self.edit_goto)
        self._stack.sig_show_namespace.connect(self.set_namespace_view)
        self._stack.sig_hide_finder_requested.connect(self.hide_finder)


    def set_namespace_view(self, view):
        self.current_widget().shellwidget.set_namespace_view(view)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_title(self):
        return _('Frames Explorer')

    def get_focus_widget(self):
        return self.current_widget()

    def setup(self):

        # ---- Options menu actions
        exclude_internal_action = self.create_action(
            FramesExplorerWidgetActions.ToggleExcludeInternal,
            text=_("Exclude internal frames"),
            tip=_("Exclude frames that are not part of the user code"),
            toggled=True,
            option='exclude_internal',
        )

        capture_locals_action = self.create_action(
            FramesExplorerWidgetActions.ToggleCaptureLocals,
            text=_("Capture locals"),
            tip=_("Capture the variables in the Variable Explorer"),
            toggled=True,
            option='capture_locals',
        )


        # ---- Toolbar actions
        search_action = self.create_action(
            FramesExplorerWidgetActions.Search,
            text=_("Search frames"),
            icon=self.create_icon('find'),
            toggled=self.show_finder,
            register_shortcut=True
        )

        refresh_action = self.create_action(
            FramesExplorerWidgetActions.Refresh,
            text=_("Refresh frames"),
            icon=self.create_icon('refresh'),
            triggered=self.refresh_table,
            register_shortcut=True,
        )

        # ---- Context menu actions
        self.view_action = self.create_action(
            FramesExplorerContextMenuActions.ViewLocalsAction,
            _("View variables with the Variable Explorer"),
            icon=self.create_icon('outline_explorer'),
            triggered=self.view_item
        )

        # Options menu
        options_menu = self.get_options_menu()
        for item in [exclude_internal_action, capture_locals_action]:
            self.add_item_to_menu(
                item,
                menu=options_menu,
                section=FramesExplorerWidgetOptionsMenuSections.Display,
            )

        # Main toolbar
        main_toolbar = self.get_main_toolbar()
        for item in [search_action, refresh_action]:
            self.add_item_to_toolbar(
                item,
                toolbar=main_toolbar,
                section=FramesExplorerWidgetMainToolBarSections.Main,
            )

        # ---- Context menu to show when there are frames present
        self.context_menu = self.create_menu(
            FramesExplorerWidgetMenus.PopulatedContextMenu)
        for item in [self.view_action]:
            self.add_item_to_menu(
                item,
                menu=self.context_menu,
                section=FramesExplorerContextMenuSections.Locals,
            )

        # ---- Context menu when the frames explorer is empty
        self.empty_context_menu = self.create_menu(
            FramesExplorerWidgetMenus.EmptyContextMenu)
        for item in []:
            self.add_item_to_menu(
                item,
                menu=self.empty_context_menu,
                section=FramesExplorerContextMenuSections.Edit,
            )

    def update_style(self):
        self._stack.setStyleSheet(
            "FramesStackedWidget {padding: 0px; border: 0px}")

    @on_conf_change
    def on_section_conf_change(self, section):
        for index in range(self.count()):
            widget = self._stack.widget(index)
            if widget:
                widget.setup()

    # ---- Stack accesors
    # ------------------------------------------------------------------------
    def add_widget(self, nsb):
        self._stack.addWidget(nsb)

    def count(self):
        return self._stack.count()

    def current_widget(self):
        return self._stack.currentWidget()

    def remove_widget(self, nsb):
        self._stack.removeWidget(nsb)

    def update_finder(self, nsb, old_nsb):
        """Initialize or update finder widget."""
        if self.finder is None:
            # Initialize finder/search related widgets
            self.finder = QWidget(self)
            self.text_finder = FramesBrowserFinder(
                nsb.results_browser,
                callback=nsb.results_browser.set_regex,
                main=nsb,
                regex_base=VALID_VARIABLE_CHARS)
            self.finder.text_finder = self.text_finder
            self.finder_close_button = self.create_toolbutton(
                'close_finder',
                triggered=self.hide_finder,
                icon=self.create_icon('DialogCloseButton'),
            )

            finder_layout = QHBoxLayout()
            finder_layout.addWidget(self.finder_close_button)
            finder_layout.addWidget(self.text_finder)
            finder_layout.setContentsMargins(0, 0, 0, 0)
            self.finder.setLayout(finder_layout)

            layout = self.layout()
            layout.addSpacing(1)
            layout.addWidget(self.finder)
        else:
            # Just update references to the same text_finder (Custom QLineEdit)
            # widget to the new current FramesBrowser and save current
            # finder state in the previous FramesBrowser
            if old_nsb is not None:
                self.save_finder_state(old_nsb)
            self.text_finder.update_parent(
                nsb.results_browser,
                callback=nsb.results_browser.set_regex,
                main=nsb,
            )

    def set_current_widget(self, nsb, old_nsb):
        """
        Set the current FramesBrowser.

        This also setup the finder widget to work with the current
        FramesBrowser.
        """
        self.update_finder(nsb, old_nsb)
        finder_visible = nsb.set_text_finder(self.text_finder)
        self._stack.setCurrentWidget(nsb)
        self.finder.setVisible(finder_visible)
        search_action = self.get_action(FramesExplorerWidgetActions.Search)
        search_action.setChecked(finder_visible)

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Register shell with frames explorer.

        This function creates a new FramesBrowser for browsing
        frames in the shell.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self._shellwidgets:
            old_nsb = self.current_widget()

            color_scheme = get_color_scheme(
                CONF.get('appearance', 'selected'))
            nsb = FramesBrowser(
                self, color_scheme=color_scheme)
            nsb.set_shellwidget(shellwidget)
            nsb.setup()
            self.add_widget(nsb)
            self._shellwidgets[shellwidget_id] = nsb
            self.set_current_widget(nsb, old_nsb)
            self.update_actions()
            return nsb

    def remove_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets.pop(shellwidget_id)
            self.remove_widget(nsb)
            nsb.close()

    def set_shellwidget(self, shellwidget):
        shellwidget_id = id(shellwidget)
        old_nsb = self.current_widget()
        if shellwidget_id in self._shellwidgets:
            nsb = self._shellwidgets[shellwidget_id]
            self.set_current_widget(nsb, old_nsb)

    @Slot(bool)
    def show_finder(self, checked):
        if self.count():
            nsb = self.current_widget()
            if checked:
                self.finder.text_finder.setText(nsb.last_find)
            else:
                self.save_finder_state(nsb)
                self.finder.text_finder.setText('')
            self.finder.setVisible(checked)
            if self.finder.isVisible():
                self.finder.text_finder.setFocus()
            else:
                nsb.results_browser.setFocus()

    @Slot()
    def hide_finder(self):
        action = self.get_action(FramesExplorerWidgetActions.Search)
        action.setChecked(False)
        nsb = self.current_widget()
        self.save_finder_state(nsb)
        self.finder.text_finder.setText('')

    def save_finder_state(self, nsb):
        """
        Save finder state (last input text and visibility).

        The values are saved in the given FramesBrowser.
        """
        last_find = self.text_finder.text()
        finder_visibility = self.finder.isVisible()
        nsb.save_finder_state(last_find, finder_visibility)

    def refresh_table(self):
        if self.count():
            nsb = self.current_widget()
            nsb.refresh()

    def view_item(self):
        self._current_editor.view_item()

    def update_actions(self):
        nsb = self.current_widget()

        for __, action in self.get_actions().items():
            if action:
                # IMPORTANT: Since we are defining the main actions in here
                # and the context is WidgetWithChildrenShortcut we need to
                # assign the same actions to the children widgets in order
                # for shortcuts to work
                if nsb:
                    nsb_actions = nsb.actions()
                    if action not in nsb_actions:
                        nsb.addAction(action)