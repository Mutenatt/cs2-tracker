"""
Transforms de coordenadas del mundo -> radar (pixeles), por mapa del pool
Premier. Constantes derivadas de awpy; NO se depende de awpy en runtime.

Radar estandar 1024x1024:  px = (x - pos_x)/scale ;  py = (pos_y - y)/scale
Devolvemos normalizado 0..1 para que el frontend escale a cualquier tamano.
"""

from __future__ import annotations

RADAR_SIZE = 1024

MAP_TRANSFORMS: dict[str, dict[str, float]] = {
    "de_mirage": {"pos_x": -3230.0, "pos_y": 1713.0, "scale": 5.0},
    "de_ancient": {"pos_x": -2953.0, "pos_y": 2164.0, "scale": 5.0},
    "de_inferno": {"pos_x": -2087.0, "pos_y": 3870.0, "scale": 4.9},
    "de_nuke": {"pos_x": -3453.0, "pos_y": 2887.0, "scale": 7.0},
    "de_dust2": {"pos_x": -2476.0, "pos_y": 3239.0, "scale": 4.4},
    "de_anubis": {"pos_x": -2796.0, "pos_y": 3328.0, "scale": 5.22},
    "de_overpass": {"pos_x": -4831.0, "pos_y": 1781.0, "scale": 5.2},
    "de_vertigo": {"pos_x": -3168.0, "pos_y": 1762.0, "scale": 4.0},
    "de_train": {"pos_x": -2477.0, "pos_y": 2392.0, "scale": 4.7},
}


def to_radar_norm(map_name: str | None, x: float, y: float) -> tuple[float, float] | None:
    """Coordenada del mundo -> (u, v) normalizado 0..1 sobre el radar. None si no hay transform."""
    t = MAP_TRANSFORMS.get(map_name or "")
    if t is None:
        return None
    u = ((x - t["pos_x"]) / t["scale"]) / RADAR_SIZE
    v = ((t["pos_y"] - y) / t["scale"]) / RADAR_SIZE
    return u, v


def has_radar(map_name: str | None) -> bool:
    return (map_name or "") in MAP_TRANSFORMS


GRID_CELLS_PER_AXIS = 64  # resolución del grid de agregación (player_map_zones)


def to_grid_cell(u: float, v: float) -> tuple[int, int]:
    """(u, v) normalizado 0..1 -> celda discreta de grid. Clampeado por si el
    transform del radar deja algún punto justo fuera de [0, 1]."""
    gx = min(max(int(u * GRID_CELLS_PER_AXIS), 0), GRID_CELLS_PER_AXIS - 1)
    gy = min(max(int(v * GRID_CELLS_PER_AXIS), 0), GRID_CELLS_PER_AXIS - 1)
    return gx, gy
