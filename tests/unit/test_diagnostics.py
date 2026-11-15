import logging

from jarvis.diagnostics.logging import configure


def test_logging_is_opt_in_and_bounded(tmp_path):
    logger = configure(None)
    assert isinstance(logger.handlers[0], logging.NullHandler)
    path = tmp_path / "diagnostics.log"
    logger = configure(path)
    for _ in range(3000):
        logger.info("Fixed diagnostic message " * 10)
    configure(None)
    assert path.exists()
    assert len(list(tmp_path.iterdir())) <= 3
    assert all(p.stat().st_size <= 256000 for p in tmp_path.iterdir())
