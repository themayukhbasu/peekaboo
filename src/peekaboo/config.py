"""Process settings.

Callers receive a Config from load_config. That function is the only
place in the package that may read the environment.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """Settings for one process.

    The skeleton has no fields yet. Later tickets add them here and
    read them inside load_config.
    """


def load_config() -> Config:
    """Load settings for this process."""
    return Config()
