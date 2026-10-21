"""Tests for reading UPS into Hermes's records. Numbers and places are invented."""

import datetime as dt
from http import HTTPStatus
from typing import Any

import pytest
from niquests import HTTPError, Response
from ups_sdk.models import TrackApiResponse, TrackResponse

from hermes import Carrier, CarrierError, TrackingNotFoundError, TrackingStatus
from hermes.carriers.ups import UPSCarrier, tracking_url

NUMBER = "1Z999AA10123456784"
CENTRAL = dt.timezone(dt.timedelta(hours=-5))


class _FakeUPS:
    """Stand-in for UPSClient: answers one canned tracking response or raises."""

    def __init__(self, answer: dict[str, Any] | None = None, error: Exception | None = None) -> None:
        self.answer = answer
        self.error = error
        self.asked: list[str] = []

    def get_tracking(self, tracking_number: str) -> TrackResponse:
        self.asked.append(tracking_number)
        if self.error is not None:
            raise self.error
        return TrackApiResponse.model_validate(self.answer).track_response


def _answer(package: dict[str, Any] | None = None, warnings: list[dict[str, str]] | None = None) -> dict[str, Any]:
    shipment: dict[str, Any] = {"inquiryNumber": NUMBER, "package": [] if package is None else [package]}
    if warnings is not None:
        shipment["warnings"] = warnings
    return {"trackResponse": {"shipment": [shipment]}}


def _activity(kind: str, day: str, clock: str, city: str, description: str) -> dict[str, Any]:
    return {
        "location": {"address": {"city": city, "stateProvince": "IL", "countryCode": "US"}},
        "status": {"type": kind, "description": description, "code": kind + "X"},
        "date": day,
        "time": clock,
        "gmtOffset": "-05:00",
    }


IN_TRANSIT: dict[str, Any] = {
    "trackingNumber": NUMBER,
    "currentStatus": {"type": "I", "description": "On the Way", "code": "OR", "simplifiedTextDescription": "Moving"},
    "deliveryDate": [{"type": "SDD", "date": "20261024"}, {"type": "RDD", "date": "20261025"}],
    "activity": [
        _activity("I", "20261021", "043000", "Springfield", "Departed from Facility"),
        _activity("P", "20261020", "180000", "Peoria", "Pickup Scan"),
    ],
}

DELIVERED: dict[str, Any] = {
    "trackingNumber": NUMBER,
    "currentStatus": {"type": "D", "description": "Delivered", "code": "FS"},
    "deliveryDate": [{"type": "DEL", "date": "20261023"}],
    "activity": [
        _activity("D", "20261023", "141500", "Chicago", "Delivered"),
        _activity("I", "20261023", "080000", "Chicago", "Out For Delivery Today"),
    ],
}


def test_an_in_transit_package_reads_its_status_expected_day_and_events() -> None:
    """The status maps to Hermes's code and the rescheduled day wins over the scheduled one."""
    tracking = UPSCarrier(_FakeUPS(_answer(IN_TRANSIT))).track(NUMBER)  # type: ignore[arg-type]

    assert tracking.carrier is Carrier.UPS
    assert tracking.status is TrackingStatus.IN_TRANSIT
    assert tracking.description == "On the Way"
    assert tracking.carrier_status_code == "OR"
    assert tracking.estimated_delivery_date == dt.date(2026, 10, 25)
    assert tracking.delivered_at is None
    assert tracking.tracking_url == tracking_url(NUMBER)
    assert [event.status for event in tracking.events] == [TrackingStatus.IN_TRANSIT, TrackingStatus.ACCEPTED]
    assert tracking.events[0].location == "Springfield, IL, US"
    assert tracking.last_event is not None
    assert tracking.last_event.occurred_at == dt.datetime(2026, 10, 21, 4, 30, tzinfo=CENTRAL)


def test_a_delivered_package_reads_when_it_was_delivered() -> None:
    """The delivery scan's time is the delivered time, and no expected day is kept."""
    tracking = UPSCarrier(_FakeUPS(_answer(DELIVERED))).track(NUMBER)  # type: ignore[arg-type]

    assert tracking.status is TrackingStatus.DELIVERED
    assert tracking.delivered_at == dt.datetime(2026, 10, 23, 14, 15, tzinfo=CENTRAL)
    assert tracking.estimated_delivery_date is None


def test_a_delivered_package_without_a_delivery_scan_falls_back_to_the_delivered_day() -> None:
    """With no delivered scan, the delivered day at midnight stands in."""
    package = {**DELIVERED, "activity": []}

    tracking = UPSCarrier(_FakeUPS(_answer(package))).track(NUMBER)  # type: ignore[arg-type]

    assert tracking.delivered_at == dt.datetime(2026, 10, 23)  # noqa: DTZ001 - UPS gives the day without an offset


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        ("M", TrackingStatus.ACCEPTED),
        ("X", TrackingStatus.EXCEPTION),
        ("RS", TrackingStatus.EXCEPTION),
        ("d", TrackingStatus.DELIVERED),
        ("ZZ", TrackingStatus.UNKNOWN),
        (None, TrackingStatus.UNKNOWN),
    ],
)
def test_status_types_map_to_hermes_statuses(kind: str | None, expected: TrackingStatus) -> None:
    """Each UPS status type reads as a Hermes status, and an unknown one as unknown."""
    package = {"trackingNumber": NUMBER, "currentStatus": {"type": kind}}

    tracking = UPSCarrier(_FakeUPS(_answer(package))).track(NUMBER)  # type: ignore[arg-type]

    assert tracking.status is expected


def test_a_package_without_a_current_status_is_unknown() -> None:
    """A package UPS gives no status for reads as unknown."""
    tracking = UPSCarrier(_FakeUPS(_answer({"trackingNumber": NUMBER}))).track(NUMBER)  # type: ignore[arg-type]

    assert tracking.status is TrackingStatus.UNKNOWN
    assert tracking.last_event is None


def _http_error(status_code: int) -> HTTPError:
    response = Response()
    response.status_code = status_code
    return HTTPError(f"{status_code} Client Error", response=response)


def test_a_number_ups_does_not_know_is_not_found() -> None:
    """UPS's 404 raises TrackingNotFoundError."""
    with pytest.raises(TrackingNotFoundError) as raised:
        UPSCarrier(_FakeUPS(error=_http_error(HTTPStatus.NOT_FOUND))).track(NUMBER)  # type: ignore[arg-type]

    assert raised.value.status_code == HTTPStatus.NOT_FOUND


def test_a_refused_request_is_a_carrier_error() -> None:
    """Any other UPS failure raises CarrierError with its status."""
    with pytest.raises(CarrierError) as raised:
        UPSCarrier(_FakeUPS(error=_http_error(HTTPStatus.FORBIDDEN))).track(NUMBER)  # type: ignore[arg-type]

    assert not isinstance(raised.value, TrackingNotFoundError)
    assert raised.value.status_code == HTTPStatus.FORBIDDEN


def test_a_not_found_warning_is_not_found() -> None:
    """UPS answering no package with its not-found warning raises TrackingNotFoundError."""
    answer = _answer(warnings=[{"code": "TW0001", "message": "Tracking Information Not Found"}])

    with pytest.raises(TrackingNotFoundError, match="Tracking Information Not Found"):
        UPSCarrier(_FakeUPS(answer)).track(NUMBER)  # type: ignore[arg-type]


def test_another_warning_without_a_package_is_a_carrier_error() -> None:
    """UPS answering no package with another warning raises CarrierError."""
    answer = _answer(warnings=[{"code": "TW0002", "message": "Something else"}])

    with pytest.raises(CarrierError) as raised:
        UPSCarrier(_FakeUPS(answer)).track(NUMBER)  # type: ignore[arg-type]

    assert not isinstance(raised.value, TrackingNotFoundError)


def test_no_package_and_no_warning_is_not_found() -> None:
    """An answer with nothing in it raises TrackingNotFoundError."""
    with pytest.raises(TrackingNotFoundError):
        UPSCarrier(_FakeUPS(_answer())).track(NUMBER)  # type: ignore[arg-type]
