"""The carrier-neutral records every carrier is read into."""

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel


class Carrier(StrEnum):
    """A shipping carrier Hermes speaks to, by the code ShipStation and Core use for it."""

    UPS = "ups"
    FEDEX = "fedex"
    USPS = "usps"


class TrackingStatus(StrEnum):
    """Where a package stands, in the eight codes ShipStation's API uses and Core stores."""

    UNKNOWN = "UN"
    ACCEPTED = "AC"
    IN_TRANSIT = "IT"
    DELIVERED = "DE"
    EXCEPTION = "EX"
    DELIVERY_ATTEMPT = "AT"
    NOT_YET_IN_SYSTEM = "NY"
    DELIVERED_TO_COLLECTION_LOCATION = "SP"


class TrackingEvent(BaseModel):
    """One scan or event in a package's history."""

    occurred_at: dt.datetime | None
    status: TrackingStatus
    description: str | None = None
    #: The carrier's own code for the event.
    carrier_status_code: str | None = None
    #: The city, state and country it happened in, as one line.
    location: str | None = None


class Tracking(BaseModel):
    """Where one package is, as its carrier last said."""

    carrier: Carrier
    tracking_number: str
    status: TrackingStatus
    description: str | None = None
    #: The carrier's own code for the current status.
    carrier_status_code: str | None = None
    carrier_status_description: str | None = None
    #: The day the carrier expects to deliver, until it has.
    estimated_delivery_date: dt.date | None = None
    delivered_at: dt.datetime | None = None
    tracking_url: str | None = None
    #: Newest first.
    events: list[TrackingEvent] = []

    @property
    def last_event(self) -> TrackingEvent | None:
        """Answer the latest event that says when it happened."""
        dated = [event for event in self.events if event.occurred_at is not None]
        if not dated:
            return None
        return max(dated, key=lambda event: _comparable(event.occurred_at))


def _comparable(moment: dt.datetime | None) -> dt.datetime:
    """Compare local and UTC-offset times alike, reading a time without an offset as UTC."""
    if moment is None:  # pragma: no cover - only dated events are compared
        return dt.datetime.min.replace(tzinfo=dt.UTC)
    return moment if moment.tzinfo is not None else moment.replace(tzinfo=dt.UTC)
