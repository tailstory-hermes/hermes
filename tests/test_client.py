"""Tests for the Hermes entry point."""

import pytest

from hermes import Carrier, CarrierNotConfiguredError, Hermes, Tracking, TrackingStatus


class _FakeCarrier:
    """A carrier answering in transit for every number."""

    carrier = Carrier.UPS

    def track(self, tracking_number: str) -> Tracking:
        return Tracking(carrier=self.carrier, tracking_number=tracking_number, status=TrackingStatus.IN_TRANSIT)


def test_track_goes_to_the_carrier_named_by_code_or_enum() -> None:
    """A carrier is found by its code or its enum."""
    hermes = Hermes([_FakeCarrier()])

    assert hermes.track("ups", "1Z1").status is TrackingStatus.IN_TRANSIT
    assert hermes.track(Carrier.UPS, "1Z2").tracking_number == "1Z2"


def test_a_carrier_not_given_is_refused() -> None:
    """Asking for a carrier Hermes was not given raises."""
    with pytest.raises(CarrierNotConfiguredError) as raised:
        Hermes([_FakeCarrier()]).track("fedex", "123")

    assert raised.value.carrier is Carrier.FEDEX


def test_an_unknown_carrier_code_is_a_value_error() -> None:
    """A code that names no carrier raises ValueError."""
    with pytest.raises(ValueError, match="dhl"):
        Hermes([]).track("dhl", "123")


def test_supports_says_which_carriers_it_was_given() -> None:
    """Hermes answers for given, known-but-not-given and unknown carriers."""
    hermes = Hermes([_FakeCarrier()])

    assert hermes.supports("ups")
    assert not hermes.supports(Carrier.USPS)
    assert not hermes.supports("dhl")
