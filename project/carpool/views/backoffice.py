from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.contrib.auth.decorators import permission_required
from carpool.models.statistics import Statistics, MonthlyStatistics


@permission_required(["carpool.view_statistics"])
def statistics_json_monthly(request):
    # Get labels for the current academic year (from September to August)
    now = timezone.now()
    if now.month >= 9:
        start_year = now.year
    else:
        start_year = now.year - 1
    labels = []
    for month in range(9, 13):
        labels.append(f"{month:02d}-{start_year}")
    for month in range(1, 9):
        labels.append(f"{month:02d}-{start_year + 1}")
    monthly_stats = MonthlyStatistics.objects.filter_by_academic_year(start_year)
    monthly_total_rides = [stat.total_rides for stat in monthly_stats]
    monthly_total_users = [stat.total_users for stat in monthly_stats]
    monthly_total_distance = [stat.total_distance for stat in monthly_stats]
    monthly_total_co2 = [stat.total_co2 for stat in monthly_stats]

    data = {
        "labels": labels,
        "monthly_total_rides": monthly_total_rides,
        "monthly_total_users": monthly_total_users,
        "monthly_total_distance": monthly_total_distance,
        "monthly_total_co2": monthly_total_co2,
    }

    return JsonResponse(data)


@permission_required(["carpool.view_statistics"])
def statistics(request):
    if Statistics.objects.count() == 0:
        # Create the Statistics object if it does not exist
        Statistics.objects.create()

    context = {
        "last_updated_at": Statistics.objects.first().updated_at,
        "total_users": Statistics.objects.first().total_users,
        "total_rides": Statistics.objects.first().total_rides,
        "total_distance": Statistics.objects.first().total_distance,
        "total_co2": Statistics.objects.first().total_co2,
    }

    return render(request, "rides/back-office/statistics.html", context)
