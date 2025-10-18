from django.test import TestCase
from django.core.exceptions import ValidationError
from django.utils import timezone

from accounts.tests.factories import UserFactory
from carpool.tests.factories import LocationFactory, VehicleFactory, RideFactory
from carpool.forms import CreateRideForm, EditRideForm
from carpool.models.ride import Ride


class LocationValidationTestCase(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.vehicle = VehicleFactory(driver=self.user, seats=4)
        # use identical coords
        self.lat = 48.8566
        self.lng = 2.3522

    def test_create_ride_form_rejects_identical_locations(self):
        form_data = {
            "d_fulltext": "Paris",
            "d_street": "",
            "d_zipcode": "75000",
            "d_city": "Paris",
            "d_latitude": self.lat,
            "d_longitude": self.lng,
            "a_fulltext": "Paris",
            "a_street": "",
            "a_zipcode": "75000",
            "a_city": "Paris",
            "a_latitude": self.lat,
            "a_longitude": self.lng,
            "r_geometry": "LINESTRING(2.3522 48.8566, 2.3522 48.8566)",
            "r_duration": 1,
            "departure_datetime": timezone.now() + timezone.timedelta(days=1),
            "seats_offered": 2,
            "vehicle": self.vehicle.pk,
            "price_per_seat": 0,
        }

        form = CreateRideForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("a_fulltext", form.errors)

    def test_edit_ride_form_rejects_identical_locations(self):
        start = LocationFactory(lat=self.lat, lng=self.lng)
        end = LocationFactory()
        ride = RideFactory(start_loc=start, end_loc=end, vehicle=self.vehicle, driver=self.user)

        data = {
            "d_fulltext": start.fulltext,
            "d_street": start.street,
            "d_zipcode": start.zipcode,
            "d_city": start.city,
            "d_latitude": start.lat,
            "d_longitude": start.lng,
            "a_fulltext": start.fulltext,
            "a_street": start.street,
            "a_zipcode": start.zipcode,
            "a_city": start.city,
            "a_latitude": start.lat,
            "a_longitude": start.lng,
            "r_geometry": ride.geometry.geojson if ride.geometry else "LINESTRING(2.3522 48.8566, 2.3522 48.8566)",
            "r_duration": 1,
            "departure_datetime": timezone.now() + timezone.timedelta(days=1),
            "seats": 2,
            "price_per_seat": 0,
        }

        form = EditRideForm(data=data, instance=ride)
        self.assertFalse(form.is_valid())
        self.assertIn("a_fulltext", form.errors)

    def test_ride_model_clean_rejects_identical_locations(self):
        start = LocationFactory(lat=self.lat, lng=self.lng)
        end = LocationFactory(lat=self.lat, lng=self.lng)
        ride = RideFactory(start_loc=start, end_loc=end, vehicle=self.vehicle, driver=self.user)

        with self.assertRaises(ValidationError):
            ride.clean()
