"""What Hermes raises, whichever carrier it spoke to."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .models import Carrier


class HermesError(Exception):
    """Something Hermes could not do."""


class CarrierNotConfiguredError(HermesError):
    """The carrier asked for was not given to Hermes."""

    def __init__(self, carrier: Carrier) -> None:
        """Initialize the error with the carrier that was asked for."""
        super().__init__(f"No {carrier.value} client was given to Hermes.")
        self.carrier = carrier


class CarrierError(HermesError):
    """The carrier refused or failed a request."""

    def __init__(self, carrier: Carrier, message: str, status_code: int | None = None) -> None:
        """Initialize the error with the carrier, what it said, and its HTTP status when there was one."""
        super().__init__(f"{carrier.value}: {message}")
        self.carrier = carrier
        self.status_code = status_code


class TrackingNotFoundError(CarrierError):
    """The carrier has no tracking for the number yet, or does not know it."""
