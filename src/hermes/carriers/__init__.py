"""One module per carrier, each importing only that carrier's SDK."""

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from hermes.models import Carrier, Tracking


class CarrierAdapter(Protocol):
    """What Hermes needs of a carrier."""

    carrier: Carrier

    def track(self, tracking_number: str) -> Tracking:
        """Answer where a package is."""
        ...
