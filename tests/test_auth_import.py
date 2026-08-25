from __future__ import annotations

import sys


def test_cli_import_does_not_load_queue():
    for name in list(sys.modules):
        if name.startswith("pehli_salary"):
            sys.modules.pop(name, None)
    import pehli_salary.cli  # noqa: F401

    assert "pehli_salary.queue" not in sys.modules
    assert "yaml" not in sys.modules or "pehli_salary.queue" not in sys.modules
