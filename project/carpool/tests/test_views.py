from accounts.tests.factories import UserFactory

from django.conf import settings
from django.test import TestCase
from django.urls import reverse

from carpool.tests.factories import RideFactory, VehicleFactory


class AnonymousAccessTestCase(TestCase):
    def setUp(self):
        u1 = UserFactory()
        self.r1 = RideFactory(driver=u1)
        self.r2 = RideFactory(driver=u1)

    def test_anonymous_access_rides_list(self):
        # Anonymous access to rides list is disabled
        settings.ANONYMOUS_ACCESS_RIDES_LIST = False
        r = self.client.get(reverse("carpool:list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r.url)

        # Anonymous access to rides list is enabled
        settings.ANONYMOUS_ACCESS_RIDES_LIST = True
        r = self.client.get(reverse("carpool:list"))
        self.assertEqual(r.status_code, 200)
        self.assertIn(self.r1, r.context["rides"])
        self.assertIn(self.r2, r.context["rides"])

    def test_login_required_map_view(self):
        # Test that rides map view requires login
        r = self.client.get(reverse("carpool:map"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r.url)

    def test_login_required_ride_detail(self):
        # Test that ride detail view requires login
        r = self.client.get(reverse("carpool:detail", kwargs={"pk": self.r1.pk}))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r.url)

    def test_login_required_ride_subscribe(self):
        # Test that ride subscribe view requires login
        r = self.client.get(
            reverse("carpool:subscribe", kwargs={"ride_pk": self.r1.pk})
        )
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r.url)

    def test_login_required_ride_edit(self):
        # Test that ride edit view requires login
        r = self.client.get(reverse("carpool:edit", kwargs={"pk": self.r1.pk}))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("accounts:login"), r.url)


class VehicleViewTestCase(TestCase):
    def setUp(self):
        self.user1 = UserFactory(email_verified=True)
        self.user2 = UserFactory(email_verified=True)
        self.vehicle1 = VehicleFactory(driver=self.user1)

    def test_vehicle_create_view(self):
        # Test only post method is allowed
        # Test that the vehicle is created and linked to the request user
        # Test the response is a json containing the vehicle data created
        # Test that invalid data returns the form with errors TODO better errors in the frontend
        pass

    def test_vehicle_update_view(self):
        self.client.force_login(self.user1)
        url = reverse("carpool:update_vehicle", kwargs={"pk": self.vehicle1.pk})

        # Test only post method is allowed
        r = self.client.get(url)
        self.assertEqual(r.status_code, 405)  # Method Not Allowed

        # Test editing a vehicle by its driver
        self.client.force_login(self.user1)
        r = self.client.post(
            url,
            {
                "name": "Updated Vehicle",
                "description": "Updated Description",
                "seats": 4,
                "geqCO2_per_km": 90.0,
            },
        )
        self.assertEqual(r.status_code, 201)

        # Test the vehicle data is invalid
        r = self.client.post(
            url,
            {
                "name": "",  # Name is required
                "description": "Updated Description",
                "seats": -1,  # Invalid seats
                "geqCO2_per_km": -50.0,  # Invalid geqCO2_per_km
            },
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("name", r.json()["errors"])
        self.assertIn("seats", r.json()["errors"])
        self.assertIn("geqCO2_per_km", r.json()["errors"])

        # Test that a user cannot edit another user's vehicle
        self.client.force_login(self.user2)
        r = self.client.post(
            url,
            {
                "name": "Malicious Update",
                "description": "Hacked Description",
                "seats": 2,
                "geqCO2_per_km": 150.0,
            },
        )
        self.assertEqual(r.status_code, 403)  # Forbidden
        self.assertIn("You are not the driver", r.json().get("error", ""))
