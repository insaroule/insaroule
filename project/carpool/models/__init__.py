from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Location(models.Model):
    fulltext = models.CharField(
        verbose_name=_("label"),
        help_text=_("Label for the location"),
        max_length=100,
    )

    street = models.CharField(
        verbose_name=_("street"),
        help_text=_("Street address of the location"),
        max_length=200,
        blank=True,
    )

    zipcode = models.CharField(
        verbose_name=_("zipcode"),
        help_text=_("Zipcode of the location"),
        max_length=10,
        blank=True,
    )

    city = models.CharField(
        verbose_name=_("city"),
        help_text=_("City of the location"),
        max_length=100,
        blank=True,
    )

    lat = models.FloatField(
        verbose_name=_("latitude"),
        help_text=_("Latitude of the location"),
        validators=[MinValueValidator(-90), MaxValueValidator(90)],
    )

    lng = models.FloatField(
        verbose_name=_("longitude"),
        help_text=_("Longitude of the location"),
        validators=[MinValueValidator(-180), MaxValueValidator(180)],
    )

    def __str__(self):
        return (
            f"Location({self.fulltext if self.fulltext else f'{self.lat}, {self.lng}'})"
        )


class Step(models.Model):
    location = models.ForeignKey(
        verbose_name=_("localisation"),
        help_text=_("Location of the step"),
        to=Location,
        on_delete=models.CASCADE,
    )

    order = models.PositiveIntegerField(
        verbose_name=_("order"),
        help_text=_("Order of the step in the ride"),
        validators=[MinValueValidator(1)],
    )

    def __str__(self):
        return f"Step({self.location}, order={self.order})"


class Vehicle(models.Model):
    name = models.CharField(
        verbose_name=_("name"),
        help_text=_("Name of the vehicle"),
        max_length=50,
        default="default",
    )

    driver = models.ForeignKey(
        verbose_name=_("driver"),
        help_text=_("Driver of the vehicle"),
        to="accounts.User",
        related_name="vehicles",
        related_query_name="vehicle",
        on_delete=models.CASCADE,
    )

    seats = models.PositiveIntegerField(
        verbose_name=_("seats"),
        help_text=_("Number of seats in the vehicle"),
        validators=[MinValueValidator(1)],
        null=False,
        blank=False,
    )

    description = models.CharField(
        verbose_name=_("visual description"),
        help_text=_("Visual description of the vehicle"),
        max_length=150,
        blank=True,
    )

    geqCO2_per_km = models.PositiveIntegerField(
        verbose_name=_("geqCO2 per km"),
        help_text=_("Number of grams of CO2 emitted per kilometer"),
        null=True,
        blank=True,
    )
