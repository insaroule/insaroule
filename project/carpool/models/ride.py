from uuid import uuid4

from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.db.models import Q


class RideManager(models.Manager):
    def count_shared_ride(self, user1, user2):
        """
        Return the number of rides shared between two users.
        A ride is "shared" if:
        - One user is the driver and the other is a rider.
        Or
        - Both users are riders in the same ride.
        And
        - The ride has ended (end_dt < now).
        """

        return (
            self.filter(
                Q(driver=user1, rider=user2)
                | Q(driver=user2, rider=user1)
                | (Q(rider=user1) & Q(rider=user2)),
                end_dt__lt=timezone.now(),
            )
            .distinct()
            .count()
        )


class Ride(models.Model):
    class PaymentMethod(models.TextChoices):
        CASH = "CASH", _("Cash")
        LYF = "LYF", _("Lyf Pay")
        WIRE = "WIRE", _("Wire Transfer")

    uuid = models.UUIDField(
        verbose_name=_("UUID"),
        primary_key=True,
        editable=False,
        default=uuid4,
    )

    driver = models.ForeignKey(
        verbose_name=_("driver"),
        to="accounts.User",
        help_text=_("The driver of the ride"),
        on_delete=models.CASCADE,
        related_name="rides_as_driver",
    )

    rider = models.ManyToManyField(
        verbose_name=_("rider"),
        to="accounts.User",
        help_text=_("The rider of the ride"),
        related_name="rides_as_rider",
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
        to="carpool.Location",
        help_text=_("The start location of the ride"),
        related_name="rides_start_here",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    end_loc = models.ForeignKey(
        verbose_name=_("end location"),
        to="carpool.Location",
        help_text=_("The end location of the ride"),
        related_name="rides_end_here",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )

    steps = models.ManyToManyField(
        verbose_name=_("steps"),
        to="carpool.Step",
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
    """
    vehicule = models.ForeignKey(
        verbose_name=_("vehicule"),
        to=Vehicle,
        help_text=_("The vehicule of the ride"),
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )
    """

    geometry = models.JSONField(
        verbose_name=_("geometry"),
        help_text=_("Geographical representation of the ride"),
        null=True,
        blank=True,
        default=dict,
    )

    duration = models.DurationField(
        verbose_name=_("duration"),
        help_text=_("Duration of the ride"),
        null=True,
        blank=True,
    )

    objects = RideManager()

    @property
    def remaining_seats(self):
        return 0

    def get_absolute_url(self):
        return reverse("carpool:detail", kwargs={"pk": self.pk})
