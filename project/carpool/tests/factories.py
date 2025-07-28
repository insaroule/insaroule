import factory
from django.utils import timezone
from carpool.models.ride import Ride
from carpool.models import Location
import random


class RideFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Ride

    start_dt = timezone.now() + timezone.timedelta(days=1)
    end_dt = start_dt + timezone.timedelta(hours=2)
    start_loc = factory.SubFactory("carpool.tests.factories.LocationFactory")
    end_loc = factory.SubFactory("carpool.tests.factories.LocationFactory")

    payment_method = "['CASH']"
    price = random.randint(1, 100)
    comment = factory.Faker("text", max_nb_chars=200)
    duration = timezone.timedelta(hours=2)


class LocationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Location

    fulltext = factory.Faker("address")
    street = factory.Faker("street_address")
    zipcode = factory.Faker("postcode")
    city = factory.Faker("city")
    lat = factory.Faker("latitude")
    lng = factory.Faker("longitude")
