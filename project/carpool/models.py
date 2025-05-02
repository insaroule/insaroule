from django.db import models


class Localisation(models.Model):
    lat = models.FloatField()
    lng = models.FloatField()


class Step(models.Model):
    name = models.TextField()
    loc = models.ForeignKey(Localisation, on_delete=models.CASCADE)


class Ride(models.Model):
    driver = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="rides_as_driver"
    )
    rider = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="rides_as_rider"
    )
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()
    start_loc = models.ForeignKey(
        Localisation, on_delete=models.CASCADE, related_name="rides_start_here"
    )
    end_loc = models.ForeignKey(
        Localisation, on_delete=models.CASCADE, related_name="rides_ends_here"
    )
    step = models.ForeignKey(Step, on_delete=models.CASCADE)
    payment_method = models.CharField(max_length=20)
    price = models.FloatField()
    comment = models.TextField()


class Vehicle(models.Model):
    name = models.CharField(max_length=50)
    seats = models.PositiveIntegerField()
    color = models.CharField(max_length=50)
