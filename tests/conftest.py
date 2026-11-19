"""
Shared test setup.

Every `write_item_data` / `delete_item` also updates a SQLite mirror of all items,
`user/data/chronos_core.db` (modules/sequence/core_builder.py). Its path comes
from `modules/sequence/registry.py`, fixed at import to the repository's own
user/ folder, so the test fixtures that point the item folders at a temporary
user did not move it: on 2026-11-19 the pilot's real mirror held 22 rows written
by tests (".tmp_test_kairos_v2_user/..." and "AppData/Local/Temp/tmp..." paths)
next to their 4 real items. No test reads the mirror, so it is switched off for
every test. Kairos plans from the YAML files, not from this mirror.
"""
import os
import sys

import pytest

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


@pytest.fixture(autouse=True)
def _no_writes_to_the_real_item_mirror(monkeypatch):
    from modules.sequence import core_builder

    monkeypatch.setattr(core_builder, "upsert_item_in_core_db", lambda *args, **kwargs: None)
    monkeypatch.setattr(core_builder, "delete_item_from_core_db", lambda *args, **kwargs: None)
    yield
