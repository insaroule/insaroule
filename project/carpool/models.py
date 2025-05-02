from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class Location(models.Model):
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
        return f"Location({self.lat}, {self.lng})"


class Step(models.Model):
    name = models.CharField(verbose_name=_("name"), max_length=50)

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
        return self.name


class Ride(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", _("Cash")
        LYF = "LYF", _("Lyf Pay")
        WIRE = "WIRE", _("Wire Transfer")

    driver = models.ForeignKey(
        verbose_name=_("driver"),
        to="accounts.User",
        help_text=_("The driver of the ride"),
        on_delete=models.CASCADE,
        related_name="rides_as_driver",
    )

    rider = models.ForeignKey(
        verbose_name=_("rider"),
        to="accounts.User",
        help_text=_("The rider of the ride"),
        on_delete=models.CASCADE,
        related_name="rides_as_rider",
        null=True,
        blank=True,
    )

    start_dt = models.DateTimeField(
        verbose_name=_("start date and time"),
        help_text=_("The start date and time of the ride"),
        null=True,
        blank=True,
    )

    end_dt = models.DateTimeField(
        verbose_name=_("end date and time"),
        help_text=_("The end date and time of the ride"),
        null=True,
        blank=True,
    )

    start_loc = models.ForeignKey(
        verbose_name=_("start location"),
        to=Location,
        help_text=_("The start location of the ride"),
        related_name="rides_start_here",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    end_loc = models.ForeignKey(
        verbose_name=_("end location"),
        to=Location,
        help_text=_("The end location of the ride"),
        related_name="rides_end_here",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    steps = models.ManyToManyField(
        verbose_name=_("steps"),
        to=Step,
        help_text=_("The steps of the ride"),
        related_name="rides",
        blank=True,
    )

    payment_method = models.CharField(
        verbose_name=_("payment method"),
        choices=PaymentMethod.choices,
        max_length=10,
        help_text=_("The payment method for the ride"),
        null=True,
        blank=True,
    )

    price = models.FloatField(
        verbose_name=_("price"),
        help_text=_("The price of the ride"),
        validators=[MinValueValidator(0)],
        null=True,
        blank=True,
    )

    comment = models.TextField(
        verbose_name=_("comment"),
        help_text=_("Comment about the ride"),
        blank=True,
        null=True,
    )

    def humanized_duration(self):
        """
        A humanized duration of the ride.
        eg "2h" or "1h30" or "1 jour et 2h30"
        """

        if not self.start_dt or not self.end_dt:
            return None

        if self.start_dt > self.end_dt:
            raise ValueError("Start date must be before end date")

        duration = self.end_dt - self.start_dt
        days, seconds = duration.days, duration.seconds
        hours, remainder = divmod(seconds, 3600)
        minutes, _ = divmod(remainder, 60)
        parts = []
        if days:
            parts.append(f"{days} jour{'s' if days > 1 else ''}")
        if hours:
            parts.append(f"{hours}h")
        if minutes:
            parts.append(f"{minutes}min")

        return " et ".join(parts)


class Vehicle(models.Model):
    name = models.CharField(
        verbose_name=_("name"), help_text=_("Name of the vehicle"), max_length=50
    )

    seats = models.PositiveIntegerField(
        verbose_name=_("seats"),
        help_text=_("Number of seats in the vehicle"),
        validators=[MinValueValidator(1)],
        null=False,
        blank=False,
    )

    color = models.CharField(
        verbose_name=_("color"), help_text=_("Color of the vehicle"), max_length=50
    )

    def __str__(self):
        return f"{self.name} ({self.color})"
