"""Deterministic transport simulation for explicitly identified demo vehicles."""
from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from datetime import datetime, timezone


EARTH_RADIUS_M = 6_371_008.8


def distance_m(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance for (lon, lat) coordinates."""
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    dlon, dlat = lon2 - lon1, lat2 - lat1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(h)))


def bearing_degrees(a: tuple[float, float], b: tuple[float, float]) -> float:
    lon1, lat1, lon2, lat2 = map(math.radians, (*a, *b))
    y = math.sin(lon2 - lon1) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(lon2 - lon1)
    return (math.degrees(math.atan2(y, x)) + 360) % 360


@dataclass(frozen=True)
class RouteMeasure:
    coordinates: list[tuple[float, float]]
    cumulative: list[float]
    length_m: float

    @classmethod
    def from_coordinates(cls, coordinates: list[list[float]]) -> "RouteMeasure":
        points = [(float(point[0]), float(point[1])) for point in coordinates]
        if len(points) < 2:
            raise ValueError("A demo route needs at least two coordinates")
        cumulative = [0.0]
        for start, end in zip(points, points[1:]):
            cumulative.append(cumulative[-1] + distance_m(start, end))
        if cumulative[-1] <= 0:
            raise ValueError("A demo route needs a non-zero length")
        return cls(points, cumulative, cumulative[-1])

    def point_at(self, travelled_m: float) -> tuple[float, float, float]:
        target = min(max(travelled_m, 0.0), self.length_m)
        segment = max(0, len(self.cumulative) - 2)
        for index in range(len(self.cumulative) - 1):
            if target <= self.cumulative[index + 1]:
                segment = index
                break
        start, end = self.coordinates[segment], self.coordinates[segment + 1]
        segment_length = self.cumulative[segment + 1] - self.cumulative[segment]
        fraction = 0 if segment_length == 0 else (target - self.cumulative[segment]) / segment_length
        lon = start[0] + (end[0] - start[0]) * fraction
        lat = start[1] + (end[1] - start[1]) * fraction
        return lon, lat, bearing_degrees(start, end)

    def nearest_vertex_distance(self, coordinate: tuple[float, float]) -> float:
        index = min(range(len(self.coordinates)), key=lambda i: distance_m(self.coordinates[i], coordinate))
        return self.cumulative[index]


def _stable_number(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:4], "big")


def simulate_vehicle(
    vehicle_id: str,
    coordinates: list[list[float]],
    stops: list[dict],
    instant: datetime | None = None,
) -> dict:
    """Return a timestamp-derived position shared by every client."""
    now = instant or datetime.now(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("Simulation timestamp must include a timezone")
    route = RouteMeasure.from_coordinates(coordinates)
    seed = _stable_number(vehicle_id)
    speed_kph = (18.0, 22.0, 26.0)[seed % 3]
    speed_mps = speed_kph / 3.6
    dwell_seconds = 18.0
    stop_distances = sorted(
        (route.nearest_vertex_distance((float(stop["lon"]), float(stop["lat"]))), stop)
        for stop in stops
    )
    cycle_seconds = route.length_m / speed_mps + dwell_seconds * len(stop_distances)
    elapsed = (now.timestamp() + seed % max(1, int(cycle_seconds))) % cycle_seconds

    travelled = 0.0
    status = "moving"
    completed_dwell = 0.0
    for stop_distance, _stop in stop_distances:
        arrival = stop_distance / speed_mps + completed_dwell
        if elapsed < arrival:
            travelled = max(0.0, (elapsed - completed_dwell) * speed_mps)
            break
        if elapsed < arrival + dwell_seconds:
            travelled = stop_distance
            status = "stopped"
            break
        completed_dwell += dwell_seconds
    else:
        travelled = min(route.length_m, (elapsed - completed_dwell) * speed_mps)

    variant = seed % 7
    age_seconds = 0
    if variant == 5:
        status, speed_kph = "delayed", round(speed_kph * 0.55, 1)
    elif variant == 6:
        status, speed_kph, age_seconds = "offline", 0.0, 720
        travelled = route.length_m * ((seed % 71) / 100)

    lon, lat, heading = route.point_at(travelled)
    upcoming = []
    for stop_distance, stop in stop_distances:
        forward_distance = stop_distance - travelled
        if forward_distance < -5:
            forward_distance += route.length_m
        eta_seconds = int(max(0, forward_distance) / max(speed_mps, 0.1))
        upcoming.append({
            "id": stop["id"], "name": stop["name"],
            "distance_m": round(max(0, forward_distance)), "eta_seconds": eta_seconds,
        })
    upcoming.sort(key=lambda item: item["eta_seconds"])
    return {
        "id": vehicle_id,
        "position": {"lon": lon, "lat": lat},
        "heading": round(heading, 1), "speed_kph": round(speed_kph, 1),
        "status": status, "occupancy": ("low", "medium", "high")[seed % 3],
        "age_seconds": age_seconds, "route_progress": round(travelled / route.length_m, 5),
        "next_stop": upcoming[0] if upcoming else None, "upcoming_stops": upcoming[:5],
    }
