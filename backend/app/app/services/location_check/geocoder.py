"""
Geocoding utilities using Google Maps API.

Supports two backends (configurable via GEOCODER_BACKEND env var):
- "rest": Direct REST API calls (default)
- "googlemaps": googlemaps Python client
"""

import asyncio
import logging
from typing import Optional, Tuple

import requests
import googlemaps
from geopy.distance import geodesic

from app.services.location_check.config import GOOGLE_MAPS_API_KEY, GEOCODER_BACKEND

logger = logging.getLogger(__name__)

# Google Maps Geocoding API endpoint
GEOCODE_API_URL = "https://maps.googleapis.com/maps/api/geocode/json"

# Initialize Google Maps client (for googlemaps backend and reverse geocoding)
_gmaps_client: Optional[googlemaps.Client] = None


def _get_client() -> googlemaps.Client:
    """Get or create Google Maps client."""
    global _gmaps_client
    if _gmaps_client is None:
        _gmaps_client = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    return _gmaps_client


# ─── REST-based geocoding ────────────────────────────────────────────────────

async def _geocode_address_rest(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert address to (lat, lon) using direct REST API call.

    Args:
        address: Address string

    Returns:
        (lat, lon) tuple or None if geocoding fails
    """
    try:
        params = {
            "address": address,
            "key": GOOGLE_MAPS_API_KEY,
        }
        logger.info(f"[geocoder:rest] Geocoding: {address}")

        response = await asyncio.to_thread(
            requests.get, GEOCODE_API_URL, params=params
        )
        data = response.json()

        if data["status"] == "OK":
            location = data["results"][0]["geometry"]["location"]
            lat, lon = location["lat"], location["lng"]
            formatted = data["results"][0].get("formatted_address", address)
            logger.info(f"[geocoder:rest] Found: ({lat}, {lon}) - {formatted}")
            return (lat, lon)
        else:
            logger.warning(f"[geocoder:rest] API status '{data['status']}' for: {address}")
    except Exception as e:
        logger.error(f"[geocoder:rest] Error for '{address}': {e}")

    return None


# ─── googlemaps client-based geocoding ───────────────────────────────────────

async def _geocode_address_googlemaps(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert address to (lat, lon) using googlemaps Python client.

    Args:
        address: Address string

    Returns:
        (lat, lon) tuple or None if geocoding fails
    """
    try:
        client = _get_client()
        # Add India suffix for better results with Indian addresses
        query = f"{address}, India" if "india" not in address.lower() else address
        logger.info(f"[geocoder:googlemaps] Geocoding: {query}")

        results = await asyncio.to_thread(client.geocode, query)
        if results:
            location = results[0]["geometry"]["location"]
            lat, lon = location["lat"], location["lng"]
            logger.info(f"[geocoder:googlemaps] Found: ({lat}, {lon})")
            return (lat, lon)
        else:
            logger.warning(f"[geocoder:googlemaps] No results for: {query}")
    except Exception as e:
        logger.error(f"[geocoder:googlemaps] Error for '{address}': {e}")

    return None


# ─── Public interface ────────────────────────────────────────────────────────

async def geocode_address(address: str) -> Optional[Tuple[float, float]]:
    """
    Convert address to (lat, lon) coordinates.

    Uses backend configured via GEOCODER_BACKEND env var ("rest" or "googlemaps").

    Args:
        address: Address string

    Returns:
        (lat, lon) tuple or None if geocoding fails
    """
    if not address or not address.strip():
        logger.warning("[geocoder] Empty address provided")
        return None

    if GEOCODER_BACKEND == "googlemaps":
        return await _geocode_address_googlemaps(address)
    else:
        # Default to REST
        return await _geocode_address_rest(address)


async def reverse_geocode(lat: float, lon: float) -> Optional[str]:
    """
    Convert (lat, lon) to human-readable address.

    Args:
        lat: Latitude
        lon: Longitude

    Returns:
        Address string or None if reverse geocoding fails
    """
    try:
        client = _get_client()
        results = await asyncio.to_thread(client.reverse_geocode, (lat, lon))
        if results:
            return results[0]["formatted_address"]
    except Exception as e:
        logger.error(f"[geocoder] Reverse geocode error for ({lat}, {lon}): {e}")

    return None


def calculate_distance_km(
    coord1: Tuple[float, float],
    coord2: Tuple[float, float],
) -> float:
    """
    Calculate geodesic (aerial) distance between two coordinates.

    Args:
        coord1: (lat, lon) tuple
        coord2: (lat, lon) tuple

    Returns:
        Distance in kilometers
    """
    return geodesic(coord1, coord2).kilometers


