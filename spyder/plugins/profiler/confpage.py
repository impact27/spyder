# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Profiler config page."""

from qtpy.QtCore import Qt
from qtpy.QtWidgets import QGroupBox, QLabel, QVBoxLayout

from spyder.api.preferences import PluginConfigPage
from spyder.config.base import _


class ProfilerConfigPage(PluginConfigPage):
    def setup_page(self):
        results_group = QGroupBox(_("Results"))
        results_layout = QVBoxLayout()
        results_group.setLayout(results_layout)

        vlayout = QVBoxLayout()
        vlayout.addWidget(results_group)
        vlayout.addStretch(1)
        self.setLayout(vlayout)
