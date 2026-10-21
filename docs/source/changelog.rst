Changelog
=========

- :release:`1.0.0 <21st October 2026>`
- :feature:`-` Hermes is now the library over the carrier SDKs: ``Hermes([UPSCarrier(UPSClient(...))])``
  tracks a package with ``track(carrier, number)`` and answers a carrier-neutral ``Tracking``
  (status in ShipStation's eight codes, delivery dates, events)
- :feature:`-` UPS, through ``tailstory-ups``, installed with the ``ups`` extra
- :support:`-` The CSV batch-shipment tool and its configuration are gone, and the shipping types
  formerly in ``darbiadev-shipping-types`` live here
