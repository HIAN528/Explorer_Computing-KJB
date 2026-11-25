"""
후보역 관련 계산: 하버사인 거리, 후보역 추출, 중심점
(4단계에서는 하버사인 거리만 먼저 만들고, 나머지는 5단계에서 채운다.)
"""

import math

EARTH_RADIUS_KM = 6371  # 지구 반지름 (km)


def haversine_km(lat1, lon1, lat2, lon2):
    """두 지점(위도, 경도) 사이의 직선거리를 km로 구한다.

    지구를 구(球)로 보고 표면을 따라 잰 최단 거리(대원 거리)를 계산하는
    하버사인(haversine) 공식을 쓴다.
    """
    # 각도(도) → 라디안
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)

    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
