# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Frames browser widget

This is the main widget used in the Frames Explorer plugin
"""
import os.path as osp
import html

# Third library imports (qtpy)
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (QHBoxLayout, QMenu, QWidget)
from qtpy.QtGui import QAbstractTextDocumentLayout, QTextDocument
from qtpy.QtCore import (QSize, Qt, Slot)
from qtpy.QtWidgets import (QApplication, QStyle,
                            QStyledItemDelegate, QStyleOptionViewItem,
                            QTreeWidgetItem)

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    create_toolbutton, create_plugin_layout,
                                    MENU_SEPARATOR)
from spyder.widgets.onecolumntree import OneColumnTree
from spyder.config.gui import get_font


ON = 'on'
OFF = 'off'


class FramesBrowser(QWidget):
    """Frames browser (global frames explorer widget)"""
    sig_option_changed = Signal(str, object)
    edit_goto = Signal((str, int, str), (str, int, str, bool))
    sig_show_namespace = Signal(dict)

    def __init__(self, parent, color_scheme, options_button=None, plugin_actions=[]):
        QWidget.__init__(self, parent)

        self.shellwidget = None
        self.exclude_internal = True
        self.capture_locals = True
        self.results_browser = None
        self.options_button = options_button
        self.actions = None
        self.plugin_actions = plugin_actions
        self.color_scheme = color_scheme

    def setup(self, exclude_internal=None, capture_locals=None):
        """
        Setup the frames browser with provided settings.
        """
        assert self.shellwidget is not None

        if self.results_browser is not None:
            self.refresh()
            return

        self.results_browser = ResultsBrowser(self, self.color_scheme)
        self.results_browser.sig_edit_goto.connect(self.edit_goto)
        self.results_browser.sig_show_namespace.connect(self.sig_show_namespace)

        # Setup toolbar layout.

        self.tools_layout = QHBoxLayout()
        toolbar = self.setup_toolbar()
        for widget in toolbar:
            self.tools_layout.addWidget(widget)
        self.tools_layout.addStretch()
        self.setup_option_actions(exclude_internal=exclude_internal,
                                  capture_locals=capture_locals)
        self.setup_options_button()

        # Setup layout.
        layout = create_plugin_layout(self.tools_layout, self.results_browser)
        self.setLayout(layout)

        self.sig_option_changed.connect(self.option_changed)

    def set_shellwidget(self, shellwidget):
        """Bind shellwidget instance to frames browser"""
        self.shellwidget = shellwidget
        shellwidget.sig_pdb_stack.connect(self.refresh_from_pdb)
        shellwidget.sig_show_traceback.connect(self.refresh_traceback)

    def get_actions(self):
        """Get actions of the widget."""
        return self.actions

    def setup_toolbar(self):
        """Setup toolbar"""
        self.refresh_button = create_toolbutton(
            self,
            text=_("Refresh frames"),
            icon=ima.icon('refresh'),
            triggered=self.refresh)

        self.enable_button = create_toolbutton(
            self,
            text=_("Enable Faulthandler"),
            icon=ima.icon('filesave'),
            triggered=self.enable_faulthandler)

        self.load_button = create_toolbutton(
            self,
            text=_("Load Faulthandler"),
            icon=ima.icon('fileopen'),
            triggered=self.load_faulthandler)

        CONF.config_shortcut(
            self.refresh,
            context='frames_explorer',
            name='refresh',
            parent=self)

        return [self.refresh_button, self.enable_button, self.load_button]

    def setup_option_actions(self, exclude_internal, capture_locals):
        """Setup the actions to show in the cog menu."""
        self.exclude_internal_action = create_action(
            self,
            _("Exclude internal threads"),
            tip=_("Exclude internal threads"),
            toggled=lambda state:
            self.sig_option_changed.emit('exclude_internal', state))
        self.exclude_internal_action.setChecked(exclude_internal)

        self.capture_locals_action = create_action(
            self,
            _("Capture Frames locals"),
            tip=_("Capture Frames locals"),
            toggled=lambda state:
            self.sig_option_changed.emit('capture_locals', state))
        self.capture_locals_action.setChecked(capture_locals)

        self.actions = [self.exclude_internal_action, self.capture_locals_action]

    def setup_options_button(self):
        """Add the cog menu button to the toolbar."""
        if not self.options_button:
            self.options_button = create_toolbutton(
                self, text=_('Options'), icon=ima.icon('tooloptions'))

            actions = self.actions + [MENU_SEPARATOR] + self.plugin_actions
            self.options_menu = QMenu(self)
            add_actions(self.options_menu, actions)
            self.options_button.setMenu(self.options_menu)

        if self.tools_layout.itemAt(self.tools_layout.count() - 1) is None:
            self.tools_layout.insertWidget(
                self.tools_layout.count() - 1, self.options_button)
        else:
            self.tools_layout.addWidget(self.options_button)

    def option_changed(self, option, value):
        """Option has changed"""
        setattr(self, to_text_string(option), value)

    def refresh(self):
        """Refresh frames table"""
        if self.isVisible():
            sw = self.shellwidget
            if sw.kernel_client is None:
                return
            sw.call_kernel(
                interrupt=True, callback=self.set_frames
                ).get_current_frames(
                    ignore_internal_threads=self.exclude_internal,
                    capture_locals=self.capture_locals)

    def enable_faulthandler(self):
        """Enable faulthandler."""
        if self.isVisible():
            sw = self.shellwidget
            if sw.kernel_client is None:
                return
            fn = osp.expanduser("~/Desktop/test.fault")
            sw.call_kernel(
                interrupt=True
                ).enable_faulthandler(fn)

    def load_faulthandler(self):
        """Load faulthandler result."""
        if self.isVisible():
            sw = self.shellwidget
            if sw.kernel_client is None:
                return
            fn = osp.expanduser("~/Desktop/test.fault")
            sw.call_kernel(
                interrupt=True, callback=self.set_frames
                ).load_faulthandler(
                    fn,
                    ignore_internal_threads=self.exclude_internal)

    def set_frames(self, frames):
        """Set current frames"""
        if self.results_browser is not None:
            self.results_browser.set_frames(frames)
            try:
                self.results_browser.sig_activated.disconnect(
                    self.shellwidget.set_pdb_index)
            except TypeError:
                pass

    def refresh_from_pdb(self, pdb_stack, curindex):
        """Refresh from pdb stack"""
        self.set_frames({'pdb': pdb_stack})
        self.set_current_item(0, curindex)
        self.results_browser.sig_activated.connect(
            self.shellwidget.set_pdb_index)

    def refresh_traceback(self, etype, error, tb):
        """Refresh from exception"""
        self.set_frames({etype.__name__: tb})

    def set_current_item(self, top_idx, sub_index):
        """Todo"""
        if self.results_browser is not None:
            self.results_browser.set_current_item(top_idx, sub_index)


class LineFrameItem(QTreeWidgetItem):

    def __init__(self, parent, index, filename, line, lineno, name,
                 f_locals, font, color_scheme=None):
        self.index = index
        self.filename = filename
        self.text = line
        self.lineno = lineno
        self.context = name
        self.color_scheme = color_scheme
        self.font = font
        self.locals = f_locals
        QTreeWidgetItem.__init__(self, parent, [self.__repr__()],
                                 QTreeWidgetItem.Type)

    def __repr__(self):
        if self.filename is None:
            return ("<!-- LineFrameItem -->"
                    "<p>idle</p>")
        _str = ("<!-- LineFrameItem -->" +
                "<p style=\"color:'{0}';\"><b> ".format(self.color_scheme['normal'][0]) +
                "<span style=\"color:'{0}';\">{1}</span>:".format(
                    self.color_scheme['string'][0],
                    html.escape(osp.basename(self.filename))) +
                "<span style=\"color:'{0}';\">{1}</span></b>".format(
                    self.color_scheme['number'][0], self.lineno))
        if self.context:
            _str += " (<span style=\"color:'{0}';\">{1}</span>)".format(
                self.color_scheme['builtin'][0], html.escape(self.context))

        _str += ("    <span style=\"font-family:{0};".format(self.font.family())
                 + "color:'{0}';font-size:50%;\"><em>{1}</em></span></p>".format(
                     self.color_scheme['comment'][0], self.text))
        return _str

    def __unicode__(self):
        return self.__repr__()

    def __str__(self):
        return self.__repr__()

    def __lt__(self, x):
        return self.index < x.index

    def __ge__(self, x):
        return self.index >= x.index


class ThreadItem(QTreeWidgetItem):

    def __init__(self, parent, name, text_color):
        self.name = str(name)

        title_format = to_text_string('<!-- ThreadItem -->'
                                      '<b style="color:{1}">{0}</b>'
                                      )
        title = (title_format.format(name, text_color))
        QTreeWidgetItem.__init__(self, parent, [title], QTreeWidgetItem.Type)

        self.setToolTip(0, self.name)

    def __lt__(self, x):
        return self.name < x.name

    def __ge__(self, x):
        return self.name >= x.name


class ItemDelegate(QStyledItemDelegate):

    def __init__(self, parent):
        QStyledItemDelegate.__init__(self, parent)
        self._margin = None

    def paint(self, painter, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)

        style = (QApplication.style() if options.widget is None
                 else options.widget.style())

        doc = QTextDocument()
        text = options.text
        doc.setHtml(text)
        doc.setDocumentMargin(0)

        # This needs to be an empty string to avoid the overlapping the
        # normal text of the QTreeWidgetItem
        options.text = ""
        style.drawControl(QStyle.CE_ItemViewItem, options, painter)

        ctx = QAbstractTextDocumentLayout.PaintContext()

        textRect = style.subElementRect(QStyle.SE_ItemViewItemText,
                                        options, None)
        painter.save()

        painter.translate(textRect.topLeft())
        painter.setClipRect(textRect.translated(-textRect.topLeft()))
        doc.documentLayout().draw(painter, ctx)
        painter.restore()

    def sizeHint(self, option, index):
        options = QStyleOptionViewItem(option)
        self.initStyleOption(options, index)
        doc = QTextDocument()
        doc.setHtml(options.text)
        doc.setTextWidth(options.rect.width())
        size = QSize(int(doc.idealWidth()), int(doc.size().height()))
        return size


class ResultsBrowser(OneColumnTree):
    sig_edit_goto = Signal(str, int, str)
    sig_activated = Signal(int)
    sig_show_namespace = Signal(dict)

    def __init__(self, parent, color_scheme):
        OneColumnTree.__init__(self, parent)
        self.font = get_font()
        self.data = None
        self.threads = None
        self.color_scheme = color_scheme
        self.text_color = color_scheme['normal'][0]

        # Setup
        self.set_title('')
        self.setSortingEnabled(False)
        self.setItemDelegate(ItemDelegate(self))
        self.setUniformRowHeights(True)  # Needed for performance
        self.sortByColumn(0, Qt.AscendingOrder)

        # Signals
        self.header().sectionClicked.connect(self.sort_section)


    def setup_common_actions(self):
        """Setup context menu common actions"""
        actions = super(ResultsBrowser, self).setup_common_actions()
        self.get_namespace_action = create_action(
            self,
            text=_('Set namespacebrowser here'),
            icon=ima.icon('ArrowDown'),
            triggered=self.get_namespace)

        return actions + [self.get_namespace_action]

    def get_namespace(self):
        """Set namespace to currentr item"""
        items = self.selectedItems()
        if not items:
            return
        item = items[0]
        if not isinstance(item, LineFrameItem):
            return
        loc = item.locals
        if loc is None:
            return
        self.sig_show_namespace.emit(loc)

    def activated(self, item):
        """Double-click event."""
        itemdata = self.data.get(id(self.currentItem()))
        if itemdata is not None:
            filename, lineno = itemdata
            self.sig_edit_goto.emit(filename, lineno, '')
            # Index exists if the item is in self.data
            self.sig_activated.emit(self.currentItem().index)

    @Slot(int)
    def sort_section(self, idx):
        self.setSortingEnabled(True)

    def clicked(self, item):
        """Click event."""
        self.activated(item)

    def set_current_item(self, top_idx, sub_index):
        """Todo"""
        item = self.topLevelItem(top_idx).child(sub_index)
        self.setCurrentItem(item)

    def set_frames(self, frames):
        """set frames."""
        self.clear()
        self.threads = {}
        self.data = {}
        self.frames = frames
        for threadId, stack in frames.items():
            parent = ThreadItem(
                self, threadId, self.text_color)
            parent.setExpanded(True)
            self.threads[threadId] = parent
            if stack:
                for idx, frame in enumerate(stack):
                    item = LineFrameItem(parent, idx,
                                         frame.filename,
                                         frame.line,
                                         frame.lineno,
                                         frame.name,
                                         frame.locals,
                                         self.font, self.color_scheme)
                    self.data[id(item)] = (frame.filename, frame.lineno)
            else:
                item = LineFrameItem(
                    parent, 0, None, '', 0, '', None, self.font, self.color_scheme)

        if 'MainThread' in self.frames and len(self.frames['MainThread']) > 0:
            main_frame = self.frames['MainThread'][-1]
            self.sig_edit_goto.emit(osp.abspath(main_frame.filename),
                                    main_frame.lineno, '')
