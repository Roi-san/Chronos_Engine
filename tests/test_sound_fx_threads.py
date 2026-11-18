"""The chime must be started before Python shuts down (issue 3, 2026-11-18).

`python modules/console.py today reschedule` exited with 139 (access violation)
after writing the schedule. faulthandler showed the crash in
`sound_fx._play_sync` on a background thread: the "done" chime was played on a
daemon thread, and the interpreter tore pygame's audio down while that thread
was still inside `snd.play()`. Python waits for non-daemon threads before it
runs exit handlers, so the thread must not be a daemon.
"""

import os
import sys
import unittest
from unittest import mock

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from modules import sound_fx


class _FakeThread:
    created = []

    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        _FakeThread.created.append(self)

    def start(self):
        pass


class ChimeThreads(unittest.TestCase):
    def setUp(self):
        _FakeThread.created = []

    def _patched(self):
        return (
            mock.patch.object(sound_fx, "_is_enabled", return_value=True),
            mock.patch.object(sound_fx, "_resolve_sound_path", return_value="done.wav"),
            mock.patch.object(sound_fx, "_play_sync", return_value=True),
            mock.patch.object(sound_fx.threading, "Thread", _FakeThread),
        )

    def test_a_chime_plays_on_a_thread_python_waits_for(self):
        enabled, path, play_sync, thread = self._patched()
        with enabled, path, play_sync, thread:
            self.assertTrue(sound_fx.play("done"))
        self.assertEqual(len(_FakeThread.created), 1)
        self.assertFalse(_FakeThread.created[0].kwargs.get("daemon", False))

    def test_a_waiting_chime_needs_no_thread(self):
        enabled, path, play_sync, thread = self._patched()
        with enabled, path, play_sync, thread:
            self.assertTrue(sound_fx.play("done", wait=True))
        self.assertEqual(_FakeThread.created, [])


if __name__ == "__main__":
    unittest.main()
