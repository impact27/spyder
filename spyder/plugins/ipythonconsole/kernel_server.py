#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 26 07:16:24 2022

@author: quentin
"""

# Standard library imports
import ast
import os
import os.path as osp
from subprocess import PIPE
from threading import Lock, Thread, Queue
import uuid

# Third-party imports
from jupyter_core.paths import jupyter_runtime_dir

class KernelServer():
    pass




# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kernel handler."""

"""
local:
    create client, comm
    Handle fault
    handle connection
    keep kernel references
    cache kernel

plan: server that: (Anything done by the kernel manager)
    1 - sends connection files
    2 - sends std messages to frontend
    3 - close restarter / std files

"""



class KernelConnectionState:
    SpyderKernelReady = 'spyder_kernel_ready'
    IpykernelReady = 'ipykernel_ready'
    Connecting = 'connecting'
    Error = 'error'
    Closed = 'closed'

class StdThread(Thread):
    """Poll for changes in std buffers."""

    def __init__(self, parent, std_buffer):
        super().__init__(parent)
        self._std_buffer = std_buffer
        self._closing = False

    def run(self):
        txt = True
        while txt:
            txt = self._std_buffer.read1()
            if txt:
                self.sig_out.emit(txt.decode())


class KernelHandler():
    """
    A class to handle the kernel in several ways and store kernel connection
    information.
    """

    def __init__(
        self,
        connection_file,
        kernel_manager=None,
        kernel_client=None,
    ):
        super().__init__()
        # Connection Informations
        self.connection_file = connection_file
        self.kernel_manager = kernel_manager
        self.kernel_client = kernel_client
        self.kernel_error_message = None
        self.connection_state = KernelConnectionState.Connecting

        # Internal
        self._shutdown_thread = None
        self._shutdown_lock = Lock()
        self._stdout_thread = None
        self._stderr_thread = None
        self._fault_args = None
        self._init_stderr = ""
        self._init_stdout = ""
        self._spyder_kernel_info_uuid = None
        self._shellwidget_connected = False

        # Start kernel
        self.connect_std_pipes()
        self.kernel_client.start_channels()
        self.check_kernel_info()

    def connect(self):
        """Connect to shellwidget."""
        self._shellwidget_connected = True
        if self.connection_state != KernelConnectionState.Connecting:
            # Emit signal in case the connection is already made
            self.sig_kernel_connection_state.emit()
        # Show initial io
        if self._init_stderr:
            self.sig_stderr.emit(self._init_stderr)
        self._init_stderr = None
        if self._init_stdout:
            self.sig_stdout.emit(self._init_stdout)
        self._init_stdout = None

    def check_kernel_info(self):
        """Send request to check kernel info."""
        code = "getattr(get_ipython(), '_spyder_kernels_version', False)"
        self.kernel_client.shell_channel.message_received.connect(
            self._dispatch_kernel_info)
        self._spyder_kernel_info_uuid = str(uuid.uuid1())
        self.kernel_client.execute(
            '', silent=True, user_expressions={
                self._spyder_kernel_info_uuid:code })

    def _dispatch_kernel_info(self, msg):
        """Listen for spyder_kernel_info."""
        user_exp = msg['content'].get('user_expressions')
        if not user_exp:
            return
        for expression in user_exp:
            if expression == self._spyder_kernel_info_uuid:
                self.kernel_client.shell_channel.message_received.disconnect(
                    self._dispatch_kernel_info)
                # Process kernel reply
                data = user_exp[expression].get('data')
                if data is not None and 'text/plain' in data:
                    spyder_kernel_info = ast.literal_eval(
                        data['text/plain'])
                    self.check_spyder_kernel_info(spyder_kernel_info)

    def check_spyder_kernel_info(self, spyder_kernel_info):
        """
        Check if the Spyder-kernels version is the right one after receiving it
        from the kernel.

        If the kernel is non-locally managed, check if it is a spyder-kernel.
        """

        if not spyder_kernel_info:
            if self.known_spyder_kernel:
                # spyder-kernels version < 3.0
                self.kernel_error_message = (
                    ERROR_SPYDER_KERNEL_VERSION_OLD.format(
                        SPYDER_KERNELS_MIN_VERSION,
                        SPYDER_KERNELS_MAX_VERSION,
                        SPYDER_KERNELS_CONDA,
                        SPYDER_KERNELS_PIP
                    )
                )
                self.connection_state = KernelConnectionState.Error
                self.known_spyder_kernel = False
                self.sig_kernel_connection_state.emit()
                return

            self.connection_state = KernelConnectionState.IpykernelReady
            self.sig_kernel_connection_state.emit()
            return

        version, pyexec = spyder_kernel_info
        if not check_version_range(version, SPYDER_KERNELS_VERSION):
            # Development versions are acceptable
            if "dev0" not in version:
                self.kernel_error_message = (
                    ERROR_SPYDER_KERNEL_VERSION.format(
                        pyexec,
                        version,
                        SPYDER_KERNELS_MIN_VERSION,
                        SPYDER_KERNELS_MAX_VERSION,
                        SPYDER_KERNELS_CONDA,
                        SPYDER_KERNELS_PIP
                    )
                )
                self.known_spyder_kernel = False
                self.connection_state = KernelConnectionState.Error
                self.sig_kernel_connection_state.emit()
                return

        self.known_spyder_kernel = True
        self.connection_state = KernelConnectionState.SpyderKernelReady
        self.sig_kernel_connection_state.emit()

    def connect_std_pipes(self):
        """Connect to std pipes."""
        self.close_std_threads()
        # Connect new threads
        if self.kernel_manager is None:
            return

        stdout = self.kernel_manager.provisioner.process.stdout
        stderr = self.kernel_manager.provisioner.process.stderr

        if stdout:
            self._stdout_thread = StdThread(self, stdout)
            self._stdout_thread.sig_out.connect(self.handle_stdout)
            self._stdout_thread.start()
        if stderr:
            self._stderr_thread = StdThread(self, stderr)
            self._stderr_thread.sig_out.connect(self.handle_stderr)
            self._stderr_thread.start()

    def disconnect_std_pipes(self):
        """Disconnect old std pipes."""
        if self._stdout_thread and not self._stdout_thread._closing:
            self._stdout_thread.sig_out.disconnect(self.handle_stdout)
            self._stdout_thread._closing = True
        if self._stderr_thread and not self._stderr_thread._closing:
            self._stderr_thread.sig_out.disconnect(self.handle_stderr)
            self._stderr_thread._closing = True

    def close_std_threads(self):
        """Close std threads."""
        if self._stdout_thread is not None:
            self._stdout_thread.wait()
            self._stdout_thread = None
        if self._stderr_thread is not None:
            self._stderr_thread.wait()
            self._stderr_thread = None

    def handle_stderr(self, err):
        """Handle stderr"""
        if self._shellwidget_connected:
            self.sig_stderr.emit(err)
        else:
            self._init_stderr += err

    def handle_stdout(self, out):
        """Handle stdout"""
        if self._shellwidget_connected:
            self.sig_stdout.emit(out)
        else:
            self._init_stdout += out

    @staticmethod
    def new_connection_file():
        """
        Generate a new connection file

        Taken from jupyter_client/console_app.py
        Licensed under the BSD license
        """
        # Check if jupyter_runtime_dir exists (Spyder addition)
        if not osp.isdir(jupyter_runtime_dir()):
            try:
                os.makedirs(jupyter_runtime_dir())
            except (IOError, OSError):
                return None
        cf = ""
        while not cf:
            ident = str(uuid.uuid4()).split("-")[-1]
            cf = os.path.join(jupyter_runtime_dir(), "kernel-%s.json" % ident)
            cf = cf if not os.path.exists(cf) else ""
        return cf

    @classmethod
    def new_from_spec(cls, kernel_spec):
        """
        Create a new kernel.

        Might raise all kinds of exceptions
        """
        connection_file = cls.new_connection_file()
        if connection_file is None:
            raise RuntimeError(
                PERMISSION_ERROR_MSG.format(jupyter_runtime_dir())
            )

        # Kernel manager
        kernel_manager = SpyderKernelManager(
            connection_file=connection_file,
            config=None,
            autorestart=True,
        )

        kernel_manager._kernel_spec = kernel_spec

        kernel_manager.start_kernel(
            stderr=PIPE,
            stdout=PIPE,
            env=kernel_spec.env,
        )

        # Kernel client
        kernel_client = kernel_manager.client()

        # Increase time (in seconds) to detect if a kernel is alive.
        # See spyder-ide/spyder#3444.
        kernel_client.hb_channel.time_to_dead = 25.0

        return cls(
            connection_file=connection_file,
            kernel_manager=kernel_manager,
            kernel_client=kernel_client,
        )

    def close(self, shutdown_kernel=True, now=False):
        """Close kernel"""
        self.connection_state = KernelConnectionState.Closed

        if shutdown_kernel and self.kernel_manager is not None:
            km = self.kernel_manager
            km.stop_restarter()

            self.disconnect_std_pipes()

            if now:
                km.shutdown_kernel(now=True)
                self.after_shutdown()
            else:
                shutdown_thread = Thread(None)
                shutdown_thread.run = self._thread_shutdown_kernel
                shutdown_thread.start()
                shutdown_thread.finished.connect(self.after_shutdown)
                self._shutdown_thread = shutdown_thread

        if (
            self.kernel_client is not None
            and self.kernel_client.channels_running
        ):
            self.kernel_client.stop_channels()

    def after_shutdown(self):
        """Cleanup after shutdown"""
        self.close_std_threads()
        self._shutdown_thread = None

    def _thread_shutdown_kernel(self):
        """Shutdown kernel."""
        with self._shutdown_lock:
            # Avoid calling shutdown_kernel on the same manager twice
            # from different threads to avoid crash.
            if self.kernel_manager.shutting_down:
                return
            self.kernel_manager.shutting_down = True
        try:
            self.kernel_manager.shutdown_kernel()
        except Exception:
            # kernel was externally killed
            pass

    def wait_shutdown_thread(self):
        """Wait shutdown thread."""
        thread = self._shutdown_thread
        if thread is None:
            return
        if thread.isRunning():
            try:
                thread.kernel_manager._kill_kernel()
            except Exception:
                pass
            thread.quit()
            thread.wait()

