# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Status bar widgets."""
# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.widgets.status import StatusBarWidget
from spyder_kernels.utils.misc import MPL_BACKENDS_FROM_SPYDER


class MatplotlibStatus(StatusBarWidget):
    """Status bar widget for current matplotlib mode."""

    def __init__(self, parent, statusbar):
        super(MatplotlibStatus, self).__init__(
            parent, statusbar)
        self._gui = None
        self._shellwidget_dict = {}
        self._current_id = None
        # Signals
        self.sig_clicked.connect(self.toggle_matplotlib)

    def get_tooltip(self):
        """Return localized tool tip for widget."""
        return _("Matplotlib interactive.")

    def toggle_matplotlib(self):
        """Toggle matplotlib ineractive."""
        backend = "inline" if self._gui != "inline" else "auto"
        self.current_shellwidget().execute("%matplotlib " + backend)
        is_spyder_kernel = self._shellwidget_dict[self._current_id][
            "spyder_kernel"]
        if not is_spyder_kernel:
            self.update_matplotlib_gui(backend)

    def update_matplotlib_gui(self, gui, shellwidget_id=None):
        """Update matplotlib interactive."""
        if shellwidget_id is None:
            shellwidget_id = self._current_id
        if shellwidget_id in self._shellwidget_dict:
            self._shellwidget_dict[shellwidget_id]["gui"] = gui
            if shellwidget_id == self._current_id:
                self.update(gui)

    def current_shellwidget(self):
        """Get current shellwidget."""
        if self._current_id:
            return self._shellwidget_dict[self._current_id]["widget"]

    def update(self, gui):
        """Update interactive state."""
        self._gui = gui
        self.set_value(_("Matplotlib: {}").format(gui))

    def add_shellwidget(self, shellwidget, external=False):
        """Add shellwidget."""
        backend = MPL_BACKENDS_FROM_SPYDER[
            str(CONF.get('ipython_console', 'pylab/backend'))]
        swid = id(shellwidget)
        self._shellwidget_dict[swid] = {
            "gui": backend,
            "widget": shellwidget,
            "spyder_kernel": not external
            }
        self.set_shellwidget_from_id(swid)
        if external:
            shellwidget.sig_is_spykernel.connect(
                lambda swid=swid: self.set_is_spyder_kernel(swid))

    def set_is_spyder_kernel(self, shellwidget_id):
        """Shellwidget is spyder_kernels."""
        if shellwidget_id in self._shellwidget_dict:
            self._shellwidget_dict[shellwidget_id][
                "spyder_kernel"] = True

    def set_shellwidget_from_id(self, shellwidget_id):
        """Set current shellwidget."""
        if shellwidget_id in self._shellwidget_dict:
            self.update(self._shellwidget_dict[shellwidget_id]["gui"])
            self._current_id = shellwidget_id

    def remove_shellwidget(self, shellwidget_id):
        """Remove shellwidget."""
        if shellwidget_id in self._shellwidget_dict:
            del self._shellwidget_dict[shellwidget_id]
