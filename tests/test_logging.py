import logging

from dip_experiments import configure_logging, get_logger


def test_get_logger_returns_logger():
    logger = get_logger("dip_experiments.test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "dip_experiments.test"


def test_configure_logging_sets_level():
    configure_logging(level=logging.WARNING)
    logger = get_logger("dip_experiments.warning")
    assert logger.isEnabledFor(logging.WARNING)
