from django.test import TestCase
from accounts.tests.factories import UserFactory
from carpool.tests.factories import RideFactory
from chat.tests.factories import ChatRequestFactory


class ChatModelsTestCase(TestCase):
    def test_chatrequest_get_room_url(self):
        ride = RideFactory(driver=UserFactory())
        cr = ChatRequestFactory(ride=ride)
        self.assertEqual(
            cr.get_room_url(),
            f"/chat/{cr.pk}/",
        )
