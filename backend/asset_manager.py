"""Theme selection and lazy loading for optional game artwork."""

from enum import Enum
from pathlib import Path
from typing import Callable

import pygame


class ArtStyle(str, Enum):
    CLASSIC = "classic"
    ILLUSTRATED = "illustrated"


ILLUSTRATED_ASSETS = (
    "hero/idle",
    "hero/walk",
    "dragon/sleeping",
    "dragon/awake",
    "dragon/phantom",
    "tiles/floor_1",
    "tiles/floor_2",
    "tiles/wall_horizontal",
    "tiles/wall_vertical",
    "portal",
    "treasure_open",
    "scorch",
    "fog",
)


class AssetManager:
    """Load themed PNG assets once and return None when a fallback is needed."""

    def __init__(self, resource_path: Callable[[str], Path]) -> None:
        self._resource_path = resource_path
        self._cache: dict[
            tuple[ArtStyle, str, tuple[int, int] | None, bool, bool],
            pygame.Surface | None,
        ] = {}

    def get(
        self,
        style: ArtStyle,
        name: str,
        size: tuple[int, int] | None = None,
        fit: bool = False,
        trim: bool = False,
    ) -> pygame.Surface | None:
        if style is ArtStyle.CLASSIC:
            return None
        key = (style, name, size, fit, trim)
        if key in self._cache:
            return self._cache[key]
        path = self._resource_path(f"frontend/assets/{style.value}/{name}.png")
        try:
            image = pygame.image.load(path).convert_alpha()
        except (FileNotFoundError, pygame.error):
            self._cache[key] = None
            return None
        if trim:
            bounds = image.get_bounding_rect(min_alpha=8)
            if bounds.width and bounds.height:
                image = image.subsurface(bounds).copy()
        if size is not None and image.get_size() != size:
            if fit:
                scale = min(size[0] / image.get_width(), size[1] / image.get_height())
                target_size = (
                    max(1, round(image.get_width() * scale)),
                    max(1, round(image.get_height() * scale)),
                )
            else:
                target_size = size
            image = pygame.transform.smoothscale(image, target_size)
        self._cache[key] = image
        return image

    def missing_assets(self, style: ArtStyle) -> list[str]:
        """List expected source files that have not been created yet."""
        if style is ArtStyle.CLASSIC:
            return []
        return [
            name
            for name in ILLUSTRATED_ASSETS
            if not self._resource_path(
                f"frontend/assets/{style.value}/{name}.png"
            ).is_file()
        ]
