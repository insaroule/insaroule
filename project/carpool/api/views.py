from carpool.api.serializers import RideSerializer
from rest_framework import viewsets, permissions
from carpool.models.ride import Ride


class RideListViewSet(viewsets.ModelViewSet):
    queryset = Ride.objects.filter_upcoming()
    serializer_class = RideSerializer
    permission_classes = [permissions.IsAuthenticated]
