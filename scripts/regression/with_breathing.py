"""Run a regression dump script with breathing room switched on in the test fixture.

Usage: python with_breathing.py <export_root> <dump_script.py>
Adds buffer_settings.yml global_dynamic_buffer 5/5 (the pilot's real values) to
the fixture the dump scripts use, then runs the script unchanged.
"""
import os
import runpy
import sys

root, script = os.path.abspath(sys.argv[1]), os.path.abspath(sys.argv[2])
sys.path[:0] = [root, os.path.join(root, "tests")]
os.chdir(root)
import chronos_fixture  # noqa: E402

chronos_fixture._FIXTURE_FILES[os.path.join("settings", "buffer_settings.yml")] = {
    "global_dynamic_buffer": {"buffer_duration_minutes": 5, "buffer_interval_minutes": 5},
}
sys.argv = [script, root]
runpy.run_path(script, run_name="__main__")
