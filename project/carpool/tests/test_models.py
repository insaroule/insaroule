from django.test import TestCase

from carpool.tests.factories import RideFactory
from accounts.tests.factories import UserFactory


class ModelTestCase(TestCase):
    def test_remaining_seats(self):
        driver = UserFactory()
        ride = RideFactory(seats_offered=4, driver=driver)
        self.assertEqual(ride.remaining_seats, 4)
        user = UserFactory()
        ride.rider.add(user)
        self.assertEqual(ride.remaining_seats, 3)
