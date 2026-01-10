import datetime

from django.test import TestCase

from django.utils.translation import override as override_language

from accounts.tests.factories import UserFactory
from carpool.tests.factories import VehicleFactory, LocationFactory
from carpool.forms.ride import CreateRideStep1Form, CreateRideStep2Form
from django.utils import timezone
from carpool.forms.location import LocationForm
from django.conf import settings


class CreateRideStep1FormTestCase(TestCase):
    def setUp(self):
        # self.form = CreateRideForm()
        self.user = UserFactory()
        self.vehicle = VehicleFactory(driver=self.user, seats=4)
        self.loc1 = LocationFactory(lat=48.8566, lng=2.3522)  # Paris
        self.loc2 = LocationFactory(lat=51.5074, lng=-0.1278)  # London
        self.loc3 = LocationFactory(lat=40.7128, lng=-74.0060)  # New York

    def _valid_location_data(self, loc):
        return {
            "fulltext": loc.fulltext,
            "street": loc.street,
            "zipcode": loc.zipcode,
            "city": loc.city,
            "latitude": loc.lat,
            "longitude": loc.lng,
        }

    def test_departure_arrival_same_location(self):
        with override_language("en"):
            # Make sure that the date is in the future
            start_dt = (timezone.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
            data = {
                "stopovers-TOTAL_FORMS": "0",
                "stopovers-INITIAL_FORMS": "0",
                "stopovers-MIN_NUM_FORMS": "0",
                "stopovers-MAX_NUM_FORMS": "5",
                "r_geometry": "LINESTRING(0 0, 1 1)",
                "r_duration": 1.0,
                "departure_datetime": start_dt,
            }
            # Add prefixes for subforms
            data.update(
                {
                    f"departure-{k}": v
                    for k, v in self._valid_location_data(self.loc1).items()
                }
            )
            data.update(
                {
                    f"arrival-{k}": v
                    for k, v in self._valid_location_data(self.loc1).items()
                }
            )
            form = CreateRideStep1Form(data)
            self.assertFalse(form.is_valid())
            self.assertIn(
                "Departure and arrival locations cannot be the same.",
                form.errors["__all__"][0],
            )

    def test_valid_step1_form_no_stepover(self):
        # Make sure that the date is in the future
        start_dt = (timezone.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        data = {
            "stopovers-TOTAL_FORMS": "0",
            "stopovers-INITIAL_FORMS": "0",
            "stopovers-MIN_NUM_FORMS": "0",
            "stopovers-MAX_NUM_FORMS": "5",
            "r_geometry": "LINESTRING(0 0, 1 1)",
            "r_duration": 1.0,
            "departure_datetime": start_dt,
        }
        data.update(
            {
                f"departure-{k}": v
                for k, v in self._valid_location_data(self.loc1).items()
            }
        )
        data.update(
            {f"arrival-{k}": v for k, v in self._valid_location_data(self.loc2).items()}
        )
        form = CreateRideStep1Form(data)
        self.assertTrue(form.is_valid())

    def test_valid_step1_form_with_stepover(self):
        # Make sure that the date is in the future
        start_dt = (timezone.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%dT%H:%M")
        data = {
            "stopovers-TOTAL_FORMS": "1",
            "stopovers-INITIAL_FORMS": "0",
            "stopovers-MIN_NUM_FORMS": "0",
            "stopovers-MAX_NUM_FORMS": "5",
            "stopovers-0-fulltext": self.loc3.fulltext,
            "stopovers-0-street": self.loc3.street,
            "stopovers-0-zipcode": self.loc3.zipcode,
            "stopovers-0-city": self.loc3.city,
            "stopovers-0-latitude": self.loc3.lat,
            "stopovers-0-longitude": self.loc3.lng,
            "r_geometry": "LINESTRING(0 0, 1 1, 2 2)",
            "r_duration": 2.0,
            "departure_datetime": start_dt,
        }
        data.update(
            {
                f"departure-{k}": v
                for k, v in self._valid_location_data(self.loc1).items()
            }
        )
        data.update(
            {f"arrival-{k}": v for k, v in self._valid_location_data(self.loc2).items()}
        )
        form = CreateRideStep1Form(data)
        self.assertTrue(form.is_valid())

    def test_reject_datetime_in_the_past(self):
        # In the past date
        start_dt = (timezone.now() - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M")
        data = {
            "stopovers-TOTAL_FORMS": "0",
            "stopovers-INITIAL_FORMS": "0",
            "stopovers-MIN_NUM_FORMS": "0",
            "stopovers-MAX_NUM_FORMS": "5",
            "r_geometry": "LINESTRING(0 0, 1 1)",
            "r_duration": 1.0,
            "departure_datetime": start_dt,
        }
        data.update(
            {
                f"departure-{k}": v
                for k, v in self._valid_location_data(self.loc1).items()
            }
        )
        data.update(
            {f"arrival-{k}": v for k, v in self._valid_location_data(self.loc2).items()}
        )

        form = CreateRideStep1Form(data)
        # Should not be valid
        self.assertFalse(form.is_valid())
        self.assertIn("departure_datetime", form.errors)
        self.assertIn("in the past", form.errors["departure_datetime"][0])

    def test_reject_datetime_more_than_a_year_in_the_future(self):
        # One year from now in the future
        start_dt = (timezone.now() + datetime.timedelta(days=366)).strftime("%Y-%m-%dT%H:%M")
        data = {
            "stopovers-TOTAL_FORMS": "0",
            "stopovers-INITIAL_FORMS": "0",
            "stopovers-MIN_NUM_FORMS": "0",
            "stopovers-MAX_NUM_FORMS": "5",
            "r_geometry": "LINESTRING(0 0, 1 1)",
            "r_duration": 1.0,
            "departure_datetime": start_dt,
        }
        data.update(
            {
                f"departure-{k}": v
                for k, v in self._valid_location_data(self.loc1).items()
            }
        )
        data.update(
            {f"arrival-{k}": v for k, v in self._valid_location_data(self.loc2).items()}
        )

        form = CreateRideStep1Form(data)
        # Should not be valid
        self.assertFalse(form.is_valid())
        self.assertIn("departure_datetime", form.errors)
        self.assertIn("one year in the future", form.errors["departure_datetime"][0])

class CreateRideStep2FormTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.vehicle = VehicleFactory(driver=self.user, seats=4)

    def test_invalid_negative_price(self):
        data = {
            "seats_offered": 2,
            "vehicle": self.vehicle.pk,
            "price": -5,
            "payment_method": ["CASH"],
        }
        form = CreateRideStep2Form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("price", form.errors)

    def test_invalid_too_many_seats(self):
        data = {
            "seats_offered": settings.MAXIMUM_SEATS_IN_VEHICLE + 1,
            "vehicle": self.vehicle.pk,
            "price": 10.0,
        }
        form = CreateRideStep2Form(data)
        self.assertFalse(form.is_valid())
        self.assertIn("seats_offered", form.errors)

    def test_valid_step2_form(self):
        data = {
            "seats_offered": 3,
            "vehicle": self.vehicle.pk,
            "price": 12.5,
            "payment_method": ["CASH", "LYF"],
            "comment": "Smooth ride",
        }
        form = CreateRideStep2Form(data)
        self.assertTrue(form.is_valid())


class EditRideFormTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.vehicle = VehicleFactory(driver=self.user, seats=4)

    def test_departure_arrival_same_location(self):
        pass


class LocationFormTestCase(TestCase):
    def test_out_of_bounds_latitude(self):
        data = {
            "fulltext": "Some location",
            "street": "Some street",
            "zipcode": "12345",
            "city": "Some city",
            "latitude": 200,  # Invalid latitude
            "longitude": 50,
        }

        form = LocationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("latitude", form.errors)

    def test_out_of_bounds_longitude(self):
        data = {
            "fulltext": "Some location",
            "street": "Some street",
            "zipcode": "12345",
            "city": "Some city",
            "latitude": 45,
            "longitude": 200,  # Invalid longitude
        }

        form = LocationForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn("longitude", form.errors)

    def valid_location(self):
        data = {
            "fulltext": "Some location",
            "street": "Some street",
            "zipcode": "12345",
            "city": "Some city",
            "latitude": 45,
            "longitude": 90,
        }

        form = LocationForm(data=data)
        self.assertTrue(form.is_valid())
