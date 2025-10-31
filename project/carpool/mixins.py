class BaseLocationMixin:
    """
    Mixin providing location-related utilities for forms.
    """

    location_fields = ["fulltext", "street", "zipcode", "city", "latitude", "longitude"]

    def get_location_data(self, prefix):
        return {f: self.data.get(f"{prefix}_{f}") for f in self.location_fields}

    @staticmethod
    def location_are_identical(loc1, loc2, tolerance=1e-5):
        loc1_lat, loc1_lng = loc1.get("latitude"), loc1.get("longitude")
        loc2_lat, loc2_lng = loc2.get("latitude"), loc2.get("longitude")
        return (
            loc1_lat is not None
            and loc1_lng is not None
            and loc2_lat is not None
            and loc2_lng is not None
            and abs(loc1_lat - loc2_lat) < tolerance
            and abs(loc1_lng - loc2_lng) < tolerance
        )
