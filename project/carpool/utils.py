from carpool.models import Location


def get_or_create_location(data):
    return Location.objects.get_or_create(
        fulltext=data["fulltext"],
        street=data.get("street"),
        zipcode=data["zipcode"],
        city=data["city"],
        lat=data["latitude"],
        lng=data["longitude"],
    )[0]
