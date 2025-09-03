import requests
from celery import shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from django.utils import timezone
from django.contrib.auth import get_user_model

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
    total_rides = Ride.objects.count()
    total_users = get_user_model().objects.count()
    total_distance = 0  # Ride.objects.aggregate(total_distance=Sum('distance'))['total_distance'] or 0
    total_co2 = 0

    logger.info(
        "Computing daily statistics: %d rides, %d users", total_rides, total_users
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

    # Check if MonthlyStatistics for the current month already exists
    now = timezone.now()

    if not MonthlyStatistics.objects.filter(month=now.month, year=now.year).exists():
        MonthlyStatistics.objects.create(
            month=now.month,
            year=now.year,
            total_rides=0,
            total_users=0,
            total_distance=0,
            total_co2=0,
        )

    # Update the current month's statistics
    current_month_rides = Ride.objects.filter(
        start_dt__year=now.year, start_dt__month=now.month
    )

    current_month_stats = MonthlyStatistics.objects.get(month=now.month, year=now.year)
    current_month_stats.total_rides = current_month_rides.count()
    current_month_stats.total_users = get_user_model().objects.count()
    current_month_stats.total_distance = 0  # current_month_rides.aggregate(total_distance=Sum('distance'))['total_distance'] or 0
    current_month_stats.total_co2 = 0
    current_month_stats.save()
