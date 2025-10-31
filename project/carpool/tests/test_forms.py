from django.test import TestCase

from accounts.tests.factories import UserFactory
from carpool.tests.factories import VehicleFactory
# from carpool.forms import CreateRideStep1Form, CreateRideStep2Form
# from django.utils import timezone


class CreateRideFormTestCase(TestCase):
    def setUp(self):
        # self.form = CreateRideForm()
        self.user = UserFactory()
        self.vehicle = VehicleFactory(driver=self.user, seats=4)
