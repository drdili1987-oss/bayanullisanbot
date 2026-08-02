from math import radians, sin, cos, sqrt, atan2


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return r * c


def sort_branches_by_distance(branches: list[dict], lat: float, lon: float) -> list[dict]:
    enriched = []
    for b in branches:
        d = haversine_km(lat, lon, b["lat"], b["lon"])
        enriched.append({**b, "distance_km": round(d, 2)})
    return sorted(enriched, key=lambda b: b["distance_km"])
