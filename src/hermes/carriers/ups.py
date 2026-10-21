"""UPS, through tailstory-ups (``pip install tailstory-hermes[ups]``)."""

import datetime as dt
from http import HTTPStatus
from typing import TYPE_CHECKING

import niquests

from hermes.errors import CarrierError, TrackingNotFoundError
from hermes.models import Carrier, Tracking, TrackingEvent, TrackingStatus

if TYPE_CHECKING:
    from ups_sdk import UPSClient
    from ups_sdk.models import Activity, Package, Status

#: UPS's status types, as Hermes's statuses.
STATUS_TYPES: dict[str, TrackingStatus] = {
    "M": TrackingStatus.ACCEPTED,  # Shipper created a label; UPS has the billing information
    "MV": TrackingStatus.UNKNOWN,  # The label was voided
    "P": TrackingStatus.ACCEPTED,  # Picked up
    "I": TrackingStatus.IN_TRANSIT,
    "O": TrackingStatus.IN_TRANSIT,  # Out for delivery
    "W": TrackingStatus.IN_TRANSIT,  # Warehousing
    "DO": TrackingStatus.IN_TRANSIT,  # Delivered to the origin freight station
    "DD": TrackingStatus.IN_TRANSIT,  # Delivered to the destination freight station
    "D": TrackingStatus.DELIVERED,
    "X": TrackingStatus.EXCEPTION,
    "RS": TrackingStatus.EXCEPTION,  # Returning to the shipper
    "NA": TrackingStatus.UNKNOWN,
}

#: UPS's warning that it has no tracking information for a number.
_NOT_FOUND_WARNING = "TW0001"
_DELIVERED_DATE = "DEL"
_EXPECTED_DATES = ("RDD", "SDD")


def tracking_url(tracking_number: str) -> str:
    """Answer the page on ups.com that tracks a number."""
    return f"https://www.ups.com/track?tracknum={tracking_number}"


class UPSCarrier:
    """UPS, read into Hermes's records."""

    carrier = Carrier.UPS

    def __init__(self, client: UPSClient) -> None:
        """Initialize the carrier with a signed-in UPS client."""
        self.client = client

    def track(self, tracking_number: str) -> Tracking:
        """Answer where a UPS package is.

        Raises
        ------
        TrackingNotFoundError
            If UPS has no tracking for the number.
        CarrierError
            If UPS refused or failed the request.
        """
        try:
            answer = self.client.get_tracking(tracking_number)
        except niquests.HTTPError as error:
            status_code = None if error.response is None else error.response.status_code
            if status_code == HTTPStatus.NOT_FOUND:
                raise TrackingNotFoundError(self.carrier, str(error), status_code) from error
            raise CarrierError(self.carrier, str(error), status_code) from error
        packages = [package for shipment in answer.shipment for package in shipment.package]
        if not packages:
            warnings = [warning for shipment in answer.shipment for warning in shipment.warnings]
            message = "; ".join(warning.message or warning.code or "" for warning in warnings) or "No packages."
            if any(warning.code == _NOT_FOUND_WARNING for warning in warnings) or not warnings:
                raise TrackingNotFoundError(self.carrier, message)
            raise CarrierError(self.carrier, message)
        package = next((row for row in packages if row.tracking_number == tracking_number), packages[0])
        return read_package(package, tracking_number)


def read_package(package: Package, tracking_number: str) -> Tracking:
    """Read one UPS package's tracking into Hermes's record."""
    current = package.current_status
    events = [_event(activity) for activity in package.activity]
    status = _status(current)
    return Tracking(
        carrier=Carrier.UPS,
        tracking_number=package.tracking_number or tracking_number,
        status=status,
        description=(current.description if current else None) or package.status_description,
        carrier_status_code=current.code if current else package.status_code,
        carrier_status_description=current.simplified_text_description if current else None,
        estimated_delivery_date=None if status is TrackingStatus.DELIVERED else _expected(package),
        delivered_at=_delivered_at(package) if status is TrackingStatus.DELIVERED else None,
        tracking_url=tracking_url(package.tracking_number or tracking_number),
        events=events,
    )


def _status(status: Status | None) -> TrackingStatus:
    if status is None or status.type is None:
        return TrackingStatus.UNKNOWN
    return STATUS_TYPES.get(status.type.upper(), TrackingStatus.UNKNOWN)


def _event(activity: Activity) -> TrackingEvent:
    address = activity.location.address if activity.location else None
    parts = [address.city, address.state_province, address.country_code or address.country] if address else []
    return TrackingEvent(
        occurred_at=activity.occurred_at,
        status=_status(activity.status),
        description=activity.status.description if activity.status else None,
        carrier_status_code=activity.status.code if activity.status else None,
        location=", ".join(part for part in parts if part) or None,
    )


def _expected(package: Package) -> dt.date | None:
    """Answer the rescheduled delivery day if UPS gave one, else the scheduled one."""
    dates = {row.type: row.date for row in package.delivery_date if row.type and row.date}
    return next((dates[kind] for kind in _EXPECTED_DATES if kind in dates), None)


def _delivered_at(package: Package) -> dt.datetime | None:
    """Answer when the delivery scan happened, else the delivered day at midnight."""
    scans = [
        activity.occurred_at
        for activity in package.activity
        if activity.occurred_at is not None and _status(activity.status) is TrackingStatus.DELIVERED
    ]
    if scans:
        return scans[0]
    day = next((row.date for row in package.delivery_date if row.type == _DELIVERED_DATE and row.date), None)
    if day is None:
        return None
    return dt.datetime.combine(day, dt.time())
