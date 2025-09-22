import requests
from celery import shared_task
from celery.utils.log import get_task_logger

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models.functions import Length
from django.core.mail import EmailMessage
from django.db.models import Count, ExpressionWrapper, F, FloatField, Sum
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import gettext as _

from carpool.models.reservation import Reservation
from carpool.models.ride import Ride
from carpool.models.statistics import MonthlyStatistics, Statistics

logger = get_task_logger(__name__)

"""
We wanted to use the adresse.data.gouv.fr API, but the service is migrating
to a new API at data.geopf.fr.
The documentation for the new API can be found here:
https://geoservices.ign.fr/documentation/services/services-geoplateforme/geocodage
"""

API_BASE_URL = "https://data.geopf.fr/geocodage/search"


@shared_task(rate_limit=settings.GEOCODAGE_TASK_RATE_LIMIT)
def get_autocompletion(query):
    """A Celery task to get latitude and longitude for a given query.
    This is a placeholder function that should be implemented with actual logic.

    API doc: https://geoservices.ign.fr/documentation/services/services-geoplateforme/autocompletion
    """
    r = requests.get(
        f"https://data.geopf.fr/geocodage/completion/?text={query}&terr=METROPOLE&type=StreetAddress",
        timeout=5,
    )
    result = []
    if r.status_code == 200:
        data = r.json()
        if data and "results" in data:
            geocoding_results = data["results"]
            if geocoding_results:
                for geocoding_result in geocoding_results:
                    result.append(
                        {
                            "fulltext": geocoding_result["fulltext"],
                            "value": f"{geocoding_result['y']}/{geocoding_result['x']}",
                            "customProperties": {
                                "street": geocoding_result.get("street", ""),
                                "city": geocoding_result.get("city", ""),
                                "zipcode": geocoding_result.get("zipcode", ""),
                                "latitude": geocoding_result["x"],
                                "longitude": geocoding_result["y"],
                            },
                        },
                    )
    return result


@shared_task(rate_limit=settings.ROUTING_TASK_RATE_LIMIT)
def get_routing(start, end):
    """A Celery task to get routing information.
    This is a placeholder function that should be implemented with actual logic.
    """
    r = requests.get(
        f"https://data.geopf.fr/navigation/itineraire?resource=bdtopo-osrm&start={start}&end={end}&profile=car&optimization=fastest&geometryFormat=geojson&getSteps=true&getBbox=true&distanceUnit=kilometer&timeUnit=hour&crs=EPSG%3A4326",
    )

    if r.status_code == 200:
        return r.json()
    return {
        "error": "Failed to fetch routing information",
        "status_code": r.status_code,
    }


@shared_task
def compute_daily_statistics():
    """
    Compute daily statistics for total rides (Statistics model).
    Compute the current month statistics if not already done (MonthlyStatistics model).
    """

    rides = Ride.objects.annotate(
        distance_km=ExpressionWrapper(
            Length("geometry", spheroid=True) / 1000.0,
            output_field=FloatField(),
        ),
        rider_count=Count("rider", distinct=True),
    ).annotate(
        spared_co2_kg=ExpressionWrapper(
            F("rider_count") * F("distance_km") * F("vehicle__geqCO2_per_km") / 1000,
            output_field=FloatField(),
        )
    )

    totals = rides.aggregate(
        total_distance=Sum("distance_km"), total_co2=Sum("spared_co2_kg")
    )

    total_rides = rides.count()
    total_users = get_user_model().objects.count()
    total_distance = totals["total_distance"] or 0

    logger.info("Total co2 %s", totals["total_co2"])
    total_co2 = totals["total_co2"] or 0

    logger.info(
        "Computing daily statistics: %d rides, %d users  %d meters, %d kg",
        total_rides,
        total_users,
        total_distance,
        total_co2,
    )

    if Statistics.objects.count() == 0:
        logger.info("No statistics found, creating the first entry.")
        # If no statistics exist, create the first entry
        Statistics.objects.create(
            total_rides=total_rides,
            total_users=total_users,
            total_distance=total_distance,
            total_co2=total_co2,
        )
    else:
        logger.info("Updating existing statistics entry.")
        s = Statistics.objects.first()
        s.total_rides = total_rides
        s.total_users = total_users
        s.total_distance = total_distance
        s.total_co2 = total_co2
        s.save()

    logger.info("Checking monthly statistics for the current month.")
    # Check if MonthlyStatistics for the current month already exists
    now = timezone.now()

    if not MonthlyStatistics.objects.filter(month=now.month, year=now.year).exists():
        logger.info("No monthly statistics for the current month, creating one.")
        MonthlyStatistics.objects.create(
            month=now.month,
            year=now.year,
            total_rides=0,
            total_users=0,
            total_distance=0,
            total_co2=0,
        )

    # Update the current month's statistics
    current_month_rides = (
        Ride.objects.filter(start_dt__year=now.year, start_dt__month=now.month)
        .annotate(distance_km=Length("geometry", spheroid=True))
        .annotate(
            spared_co2_kg=ExpressionWrapper(
                Count("rider") * F("distance_km") * F("vehicle__geqCO2_per_km") / 1000,
                output_field=FloatField(),
            )
        )
    )

    total_distance = current_month_rides.aggregate(total_distance=Sum("distance_km"))[
        "total_distance"
    ]
    total_co2 = current_month_rides.aggregate(total_co2=Sum("spared_co2_kg"))[
        "total_co2"
    ]

    current_month_stats = MonthlyStatistics.objects.get(month=now.month, year=now.year)
    current_month_stats.total_rides = current_month_rides.count()
    current_month_stats.total_users = get_user_model().objects.count()
    current_month_stats.total_distance = total_distance.km if total_distance else 0
    current_month_stats.total_co2 = (
        total_co2 / 1000 if total_co2 else 0
    )  # Convert into kg
    current_month_stats.save()


@shared_task
def send_email_confirmed_ride(reservation_pk):
    """
    Send an email to the rider when their ride is confirmed by the driver.
    """
    reservation = Reservation.objects.get(pk=reservation_pk)

    # User Notification preferences
    if not reservation.user.notification_preferences.ride_status_update_notification:
        logger.info(
            f"User {reservation.user.email} has disabled ride confirmed notifications."
        )
        return

    context = {
        "username": reservation.user.username,
        "ride": reservation.ride,
    }

    message = render_to_string("chat/emails/confirmed_ride.txt", context)

    email = EmailMessage(
        subject="[INSAROULE] " + _("Your ride has been confirmed!"),
        body=message,
        to=[reservation.user.email],
    )

    email.send(fail_silently=False)
    logger.info(f"Sent ride confirmation email to {reservation.user.email}.")


@shared_task
def send_email_declined_ride(reservation_pk):
    """
    Send an email to the rider when their ride is declined by the driver.
    """
    reservation = Reservation.objects.get(pk=reservation_pk)

    # User Notification preferences
    if not reservation.user.notification_preferences.ride_status_update_notification:
        logger.info(
            f"User {reservation.user.email} has disabled ride declined notifications."
        )
        return

    context = {
        "username": reservation.user.username,
        "ride": reservation.ride,
    }

    message = render_to_string("chat/emails/declined_ride.txt", context)

    email = EmailMessage(
        subject="[INSAROULE] " + _("Your ride has been declined!"),
        body=message,
        to=[reservation.user.email],
    )

    email.send(fail_silently=False)
    logger.info(f"Sent ride decline email to {reservation.user.email}.")
