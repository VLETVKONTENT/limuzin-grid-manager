from __future__ import annotations

from functools import lru_cache

from pyproj import CRS, Transformer


def infer_gk_zone(y: float) -> int:
    return int(abs(y) // 1_000_000)


@lru_cache(maxsize=32)
def make_transformer_for_zone(zone: int) -> Transformer:
    if zone < 1 or zone > 32:
        raise ValueError(f"Некорректная зона Гаусса-Крюгера: {zone}. Ожидается 1..32.")

    epsg = 28400 + zone
    try:
        crs_src = CRS.from_epsg(epsg)
    except Exception as exc:
        raise ValueError(f"Не удалось создать CRS EPSG:{epsg} для зоны {zone}: {exc}") from exc

    crs_dst = CRS.from_epsg(4326)
    return Transformer.from_crs(crs_src, crs_dst, always_xy=True)


def ck42_to_wgs84(x: float, y: float, transformer: Transformer) -> tuple[float, float]:
    lon, lat = transformer.transform(y, x)
    return lon, lat
