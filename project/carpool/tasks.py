import time
import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from requests.exceptions import RequestException, Timeout, ConnectionError
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.gis.db.models.functions import Length
from django.core.mail import EmailMessage
from django.db.models import (
    Count,
    ExpressionWrapper,
    F,
    FloatField,
    Sum,
    When,
    Case,
    Q,
    Value,
)
from django.template.loader import render_to_string
from django.utils import timezone, translation
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
    """
    Celery task to get routing information between two points using the IGN routing API.

    Args:
        start (str): Starting point coordinates, format "lon,lat" (e.g. "-1.68365,48.110899")
        end (str): Ending point coordinates, format "lon,lat" (e.g. "-1.466824,47.297116")

    Returns:
        dict: Routing result (JSON) or error information.
    """

    base_url = "https://data.geopf.fr/navigation/itineraire"
    params = {
        "resource": "bdtopo-osrm",
        "start": start,
        "end": end,
        "profile": "car",
        "optimization": "fastest",
        "geometryFormat": "geojson",
        "getSteps": "true",
        "getBbox": "true",
        "distanceUnit": "kilometer",
        "timeUnit": "hour",
        "crs": "EPSG:4326",
    }

    # Configuration
    TIMEOUT = 60  # seconds
    MAX_RETRIES = 3
    BACKOFF_BASE = 2  # exponential backoff base

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            start_time = time.time()
            response = requests.get(base_url, params=params, timeout=TIMEOUT)
            duration = round(time.time() - start_time, 2)

            logger.info(
                f"[IGN Routing] Call #{attempt} ({duration}s) - "
                f"status={response.status_code} start={start} end={end}"
            )

            if response.status_code == 200:
                return response.json()

            elif response.status_code in (502, 503, 504):
                # Transient error → retry
                if attempt < MAX_RETRIES:
                    wait = BACKOFF_BASE**attempt
                    logger.warning(
                        f"[IGN Routing] Temporary error {response.status_code}, "
                        f"retrying in {wait}s (attempt {attempt}/{MAX_RETRIES})"
                    )
                    time.sleep(wait)
                    continue
                else:
                    break

            else:
                # Permanent error (e.g., 400, 404)
                logger.error(
                    f"[IGN Routing] Failed (HTTP {response.status_code}): {response.text[:200]}"
                )
                return {
                    "error": "Failed to fetch routing information",
                    "status_code": response.status_code,
                    "details": response.text,
                }

        except (Timeout, ConnectionError) as e:
            # Retry on network timeout or connectivity issues
            if attempt < MAX_RETRIES:
                wait = BACKOFF_BASE**attempt
                logger.warning(
                    f"[IGN Routing] Network error: {e}. Retrying in {wait}s..."
                )
                time.sleep(wait)
                continue
            else:
                logger.error("[IGN Routing] Network error after retries")
                return {"error": str(e), "status_code": None}

        except RequestException as e:
            logger.error("[IGN Routing] Unexpected request error")
            return {"error": str(e), "status_code": None}

    # If all retries failed
    return {
        "error": "IGN routing service unavailable after retries",
        "status_code": None,
    }


@shared_task
def compute_daily_statistics():
    """
    Compute daily statistics for total rides (Statistics model).
    Compute the current month statistics if not already done (MonthlyStatistics model).
    """

    logger.info("Computing daily statistics for total rides.")

    rides = (
        Ride.objects.annotate(
            distance_km=ExpressionWrapper(
                Length("geometry", spheroid=True) / 1000.0,
                output_field=FloatField(),
            ),
            rider_count=Count("rider", distinct=True),
        )
        .annotate(
            effective_co2_per_km=Case(
                When(
                    Q(vehicle__geqCO2_per_km__isnull=True)
                    | Q(vehicle__geqCO2_per_km=0),
                    then=Value(settings.AVERAGE_CO2_EMISSION_PER_KM),
                ),
                default=F("vehicle__geqCO2_per_km"),
                output_field=FloatField(),
            ),
        )
        .annotate(
            spared_co2_kg=ExpressionWrapper(
                F("rider_count") * F("distance_km") * F("effective_co2_per_km") / 1000,
                output_field=FloatField(),
            )
        )
    )

    totals = rides.aggregate(
        total_distance=Sum("distance_km"),
        total_co2=Sum("spared_co2_kg"),
    )

    total_rides = rides.count()
    total_users = get_user_model().objects.count()
    total_distance = totals["total_distance"] or 0
    total_co2 = totals["total_co2"] or 0

    logger.info(
        "Computing daily statistics: %d rides, %d users, %.2f km, %.2f kg CO2",
        total_rides,
        total_users,
        total_distance,
        total_co2,
    )

    # --- Daily Statistics ---
    if Statistics.objects.count() == 0:
        logger.info("No statistics found, creating the first entry.")
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

    # --- Monthly Statistics ---
    now = timezone.now()
    logger.info("Checking monthly statistics for %d-%d", now.year, now.month)

    month_stats, created = MonthlyStatistics.objects.get_or_create(
        month=now.month,
        year=now.year,
        defaults={
            "total_rides": 0,
            "total_users": 0,
            "total_distance": 0,
            "total_co2": 0,
        },
    )

    current_month_rides = (
        Ride.objects.filter(start_dt__year=now.year, start_dt__month=now.month)
        .annotate(distance_km=Length("geometry", spheroid=True) / 1000.0)
        .annotate(
            effective_co2_per_km=Case(
                When(
                    Q(vehicle__geqCO2_per_km__isnull=True)
                    | Q(vehicle__geqCO2_per_km=0),
                    then=Value(settings.AVERAGE_CO2_EMISSION_PER_KM),
                ),
                default=F("vehicle__geqCO2_per_km"),
                output_field=FloatField(),
            ),
        )
        .annotate(
            spared_co2_kg=ExpressionWrapper(
                Count("rider", distinct=True)
                * F("distance_km")
                * F("effective_co2_per_km")
                / 1000,
                output_field=FloatField(),
            )
        )
    )

    month_totals = current_month_rides.aggregate(
        total_distance=Sum("distance_km"), total_co2=Sum("spared_co2_kg")
    )

    month_stats.total_rides = current_month_rides.count()
    month_stats.total_users = get_user_model().objects.count()
    month_stats.total_distance = month_totals["total_distance"] or 0
    month_stats.total_co2 = month_totals["total_co2"] or 0
    month_stats.save()

    logger.info(
        "Monthly statistics updated successfully for %d-%d", now.year, now.month
    )


@shared_task
def send_email_incoming_reservation_to_driver(site_base_url, reservation_pk):
    """
    Send an email to the driver when a new reservation is made to a ride
    """
    reservation = Reservation.objects.get(pk=reservation_pk)

    # User Notification preferences
    if not reservation.ride.driver.notification_preferences.ride_status_update_notification:
        logger.info(
            f"User {reservation.ride.driver.email} has disabled ride status update notifications."
        )
        return

    context = {
        "driver": reservation.ride.driver,
        "ride": reservation.ride,
        "reservation": reservation,
        "link": site_base_url + reservation.get_chat_request_url(),
    }

    with translation.override(reservation.ride.driver.preferred_language):
        subject = "[INSAROULE] " + _(
            "New reservation for your ride to %(destination)s"
        ) % {
            "destination": reservation.ride.end_loc.city,
        }

        message = render_to_string("rides/emails/incoming_reservation.html", context)

    email = EmailMessage(
        subject=subject,
        body=message,
        to=[reservation.ride.driver.email],
    )

    email.content_subtype = "html"
    email.send(fail_silently=False)


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

    with translation.override(reservation.user.preferred_language):
        subject = "[INSAROULE] " + _("Your ride has been confirmed!")
        message = render_to_string("rides/emails/confirmed_ride.txt", context)

    email = EmailMessage(
        subject=subject,
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

    with translation.override(reservation.user.preferred_language):
        subject = "[INSAROULE] " + _("Your ride has been declined!")
        message = render_to_string("rides/emails/declined_ride.txt", context)

    email = EmailMessage(
        subject=subject,
        body=message,
        to=[reservation.user.email],
    )

    email.send(fail_silently=False)
    logger.info(f"Sent ride decline email to {reservation.user.email}.")


@shared_task
def send_email_suggest_ride_sharing(ride_pk, similar_rides_pks, requester_pk):
    """
    Send an email to the driver suggesting them to share their ride.
    """
    ride = Ride.objects.get(pk=ride_pk)
    similar_rides = Ride.objects.filter(pk__in=similar_rides_pks)
    requester = get_user_model().objects.get(pk=requester_pk)

    # User Notification preferences
    if not ride.driver.notification_preferences.ride_sharing_suggestion_notification:
        logger.info(
            f"User {ride.driver.email} has disabled ride sharing suggestion notifications."
        )
        return

    logger.debug(f"ride: {ride}")

    context = {
        "driver": ride.driver,
        "ride": ride,
        "similar_rides": similar_rides,
        "requester": requester.first_name
        if requester.first_name
        else requester.username,
    }
    # Send the email using driver preferred language if available

    with translation.override(ride.driver.preferred_language):
        subject = "[INSAROULE] " + _("Suggestion to share your ride")
        message = render_to_string("rides/emails/suggest_ride_sharing.html", context)

    email = EmailMessage(
        subject=subject,
        body=message,
        to=[ride.driver.email],
    )
    # email content
    email.content_subtype = "html"
    email.reply_to = [requester.email]

    email.send(fail_silently=False)
    logger.info(f"Sent ride sharing suggestion email to {ride.driver.email}.")
