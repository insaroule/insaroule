from django.test import TestCase

from accounts.tests.factories import UserFactory
from carpool.tests.factories import VehicleFactory
from carpool.forms import CreateRideForm
from django.utils import timezone


class CreateRideFormTestCase(TestCase):
    def setUp(self):
        self.form = CreateRideForm()
        self.user = UserFactory()
        self.vehicle = VehicleFactory(driver=self.user, seats=4)

    def test_seats_offered_greater_than_vehicle_capacity(self):
        form_data = {
            "d_fulltext": "Departure fulltext",
            "d_street": "Departure street",
            "d_zipcode": "12345",
            "d_city": "Departure city",
            "d_latitude": 40.7128,
            "d_longitude": -74.0060,
            "a_fulltext": "Arrival fulltext",
            "a_street": "Arrival street",
            "a_zipcode": "67890",
            "a_city": "Arrival city",
            "a_latitude": 34.0522,
            "a_longitude": -118.2437,
            "r_geometry": "LINESTRING(40.7128 -74.0060, 34.0522 -118.2437)",
            "r_distance": 4500,
            "departure_datetime": timezone.now() + timezone.timedelta(days=1),
            "seats_offered": 5,
            "vehicle": self.vehicle.pk,
            "price_per_seat": 10.00,
            "payment_method": ["CASH"],
        }

        form = CreateRideForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn("seats_offered", form.errors)
