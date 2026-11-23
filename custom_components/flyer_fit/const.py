"""Constants for the Flyer FIT integration."""

from datetime import timedelta
import logging

DOMAIN = "flyer_fit"
LOGGER = logging.getLogger(__package__)

# How often to read the bike while it is switched on. Each read holds the bike's
# single Bluetooth connection for a few seconds, so keep this modest.
UPDATE_INTERVAL = timedelta(minutes=2)

# When the bike starts advertising again (switched on), read it right away, but not
# more often than this.
MIN_SECONDS_BETWEEN_POLLS = 60

# Readings with changed raw values kept for the diagnostics download.
HISTORY_SIZE = 300

DEFAULT_ASSIST_MODES = ["off", "eco", "std", "auto", "high"]
