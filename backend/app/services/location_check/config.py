"""
Location check configuration.
"""

import os

# Distance thresholds in kilometers (tiered)
PASS_MAX_KM = 15      # 0-15 km: pass
REVIEW_MAX_KM = 30    # 15-30 km: needs_review, > 30 km: fail

# Google Maps API key
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Geocoder backend: "rest" (direct REST API) or "googlemaps" (googlemaps client)
GEOCODER_BACKEND = os.getenv("GEOCODER_BACKEND", "rest")
