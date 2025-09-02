from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


class Statistics(models.Model):
    """
    Model used to store overall statistics about the application.

    Used to avoid recalculating statistics on each request to the back-office.
    This model contains only 1 record that is updated daily by a Celery task.
    """

    # Last time the statistics were updated
    updated_at = models.DateTimeField(auto_now=True)

    # Global statistics
    total_users = models.IntegerField(default=0)
    total_rides = models.IntegerField(default=0)
    total_distance = models.FloatField(default=0.0)
    total_co2 = models.FloatField(default=0.0)

    class Meta:
        verbose_name = _("Statistic")
        verbose_name_plural = _("Statistics")


class MonthlyStatisticsManager(models.Manager):
    def filter_by_academic_year(self, start_year):
        """
        Filter MonthlyStatistics by academic year.
        """
        return self.filter(
            models.Q(year=start_year, month__gte=9)
            | models.Q(year=start_year + 1, month__lt=9)
        )


class MonthlyStatistics(models.Model):
    """
    Monthly statistics about the application usage.

    This model is updated monthly by a Celery task. The current month statistics
    is updated daily by the same Celery task that updates the overall statistics.
    """

    month = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(12)]
    )
    year = models.IntegerField()

    # Monthly statistics
    total_users = models.IntegerField(default=0)
    total_rides = models.IntegerField(default=0)
    total_distance = models.FloatField(default=0.0)
    total_co2 = models.FloatField(default=0.0)

    objects = MonthlyStatisticsManager()

    class Meta:
        unique_together = ("month", "year")
        verbose_name = _("Monthly statistic")
        verbose_name_plural = _("Monthly statistics")
