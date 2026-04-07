from carpool.models.ride import Ride
from carpool.models import Location, Step
from rest_framework import serializers


class CityLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["city"]


class SmallRideSerializer(serializers.ModelSerializer):
    start_loc = CityLocationSerializer(read_only=True)
    end_loc = CityLocationSerializer(read_only=True)

    class Meta:
        model = Ride
        fields = ["uuid", "start_loc", "end_loc", "start_dt", "end_dt"]


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["fulltext", "street", "zipcode", "city", "lat", "lng"]


class StepSerializer(serializers.ModelSerializer):
    location = LocationSerializer(read_only=True)

    class Meta:
        model = Step
        fields = ["location", "order"]


class RideSerializer(serializers.ModelSerializer):
    steps = StepSerializer(many=True, read_only=True)
    start_loc = LocationSerializer(read_only=True)
    end_loc = LocationSerializer(read_only=True)

    class Meta:
        model = Ride
        fields = [
            "uuid",
            "driver",
            "start_dt",
            "end_dt",
            "start_loc",  # TODO: nested serializer
            "end_loc",  # TODO: nested serializer
            "steps",  # TODO: nested serializer
            "payment_method",
            "geometry",
            "duration",
            "comment",
            "remaining_seats",
            "booked_seats",
        ]
