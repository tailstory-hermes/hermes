"""The one entry point: hand Hermes the carriers you have, then ask about any of them."""

from typing import TYPE_CHECKING

from .errors import CarrierNotConfiguredError
from .models import Carrier, Tracking

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .carriers import CarrierAdapter


class Hermes:
    """Track packages across the carriers it was given."""

    def __init__(self, carriers: Iterable[CarrierAdapter]) -> None:
        """Initialize Hermes with one adapter per carrier, such as ``UPSCarrier(UPSClient(...))``."""
        self.carriers: dict[Carrier, CarrierAdapter] = {adapter.carrier: adapter for adapter in carriers}

    def supports(self, carrier: Carrier | str) -> bool:
        """Say whether Hermes was given the carrier, by enum or by code such as ``"ups"``."""
        try:
            return Carrier(carrier) in self.carriers
        except ValueError:
            return False

    def track(self, carrier: Carrier | str, tracking_number: str) -> Tracking:
        """Answer where a package is.

        Parameters
        ----------
        carrier
            The carrier, by enum or by code such as ``"ups"``.
        tracking_number
            The carrier's tracking number.

        Raises
        ------
        CarrierNotConfiguredError
            If Hermes was not given the carrier.
        TrackingNotFoundError
            If the carrier has no tracking for the number.
        CarrierError
            If the carrier refused or failed the request.
        ValueError
            If ``carrier`` is no carrier Hermes knows.
        """
        code = Carrier(carrier)
        adapter = self.carriers.get(code)
        if adapter is None:
            raise CarrierNotConfiguredError(code)
        return adapter.track(tracking_number)
