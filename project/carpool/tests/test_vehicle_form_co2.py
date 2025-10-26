from django.test import TestCase

from carpool.forms import VehicleForm
from carpool.tests.factories import VehicleFactory


class VehicleFormCO2TestCase(TestCase):
    def test_initial_empty_when_none(self):
        vehicle = VehicleFactory.build(geqCO2_per_km=None)
        form = VehicleForm(instance=vehicle)
        self.assertEqual(form.fields["geqCO2_per_km"].initial, "")

    def test_clean_empty_to_none(self):
        vehicle = VehicleFactory.build(geqCO2_per_km=None)
        form = VehicleForm(data={"name": vehicle.name, "description": vehicle.description, "seats": vehicle.seats, "geqCO2_per_km": ""}, instance=vehicle)
        self.assertTrue(form.is_valid())
        self.assertIsNone(form.cleaned_data["geqCO2_per_km"])
