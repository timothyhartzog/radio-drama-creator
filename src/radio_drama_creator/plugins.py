"""Plugin system for registering third-party TTS engines, LLM backends, and SFX packs.

Plugins can be registered in two ways:

1. **Programmatic** — call ``register_renderer``, ``register_script_backend``,
   or ``register_sfx_pack`` directly from Python code.
2. **Entry points** — declare a ``radio_drama_creator`` entry-point group in
   your package's ``pyproject.toml``.  The entry point must be a callable that
   receives the plugin registry and calls the appropriate ``register_*`` method.

   Example ``pyproject.toml`` snippet::

       [project.entry-points."radio_drama_creator"]
       my_tts = "my_package:register"

   Where ``my_package.register`` looks like::

       from radio_drama_creator.plugins import registry

       def register(reg):
           reg.register_renderer("my_tts", MyTTSRenderer)

Usage from the host application::

    from radio_drama_creator.plugins import registry

    # Discover installed entry-point plugins
    registry.discover()

    # Or register manually
    registry.register_renderer("custom_tts", CustomRenderer)

    # Look up at runtime
    renderer_cls = registry.get_renderer("custom_tts")
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from .render import Renderer
from .dramatize import ScriptGenerator

logger = logging.getLogger(__name__)

# Type aliases for plugin factories
RendererFactory = Callable[..., Renderer]
ScriptBackendFactory = Callable[..., ScriptGenerator]


class SFXPack:
    """A named collection of SFX assets that can be overlaid on the built-in catalog."""

    __slots__ = ("name", "directory", "catalog")

    def __init__(self, name: str, directory: Path, catalog: dict[str, str] | None = None):
        self.name = name
        self.directory = directory
        self.catalog = catalog or {}

    def resolve(self, cue_text: str) -> Path | None:
        """Return the path to a WAV asset matching *cue_text*, or ``None``."""
        lowered = cue_text.lower()
        for keyword, filename in self.catalog.items():
            if keyword in lowered:
                candidate = self.directory / filename
                if candidate.exists():
                    return candidate
        return None


class PluginRegistry:
    """Central registry for renderers, script backends, and SFX packs."""

    def __init__(self) -> None:
        self._renderers: dict[str, RendererFactory] = {}
        self._script_backends: dict[str, ScriptBackendFactory] = {}
        self._sfx_packs: dict[str, SFXPack] = {}
        self._discovered = False

    # ── Registration ────────────────────────────────────────────────

    def register_renderer(self, name: str, factory: RendererFactory) -> None:
        """Register a TTS renderer factory under *name*.

        The factory is called with no arguments and must return a ``Renderer`` instance.
        """
        if name in self._renderers:
            logger.warning("Overwriting renderer plugin %r", name)
        self._renderers[name] = factory

    def register_script_backend(self, name: str, factory: ScriptBackendFactory) -> None:
        """Register a script-generation backend factory under *name*.

        The factory is called with no arguments and must return a ``ScriptGenerator``.
        """
        if name in self._script_backends:
            logger.warning("Overwriting script backend plugin %r", name)
        self._script_backends[name] = factory

    def register_sfx_pack(self, pack: SFXPack) -> None:
        """Register an SFX pack so its assets are available during rendering."""
        if pack.name in self._sfx_packs:
            logger.warning("Overwriting SFX pack %r", pack.name)
        self._sfx_packs[pack.name] = pack

    # ── Lookup ──────────────────────────────────────────────────────

    def get_renderer(self, name: str) -> RendererFactory | None:
        """Return the renderer factory for *name*, or ``None``."""
        return self._renderers.get(name)

    def get_script_backend(self, name: str) -> ScriptBackendFactory | None:
        """Return the script-backend factory for *name*, or ``None``."""
        return self._script_backends.get(name)

    def get_sfx_pack(self, name: str) -> SFXPack | None:
        """Return the SFX pack registered under *name*, or ``None``."""
        return self._sfx_packs.get(name)

    def list_renderers(self) -> list[str]:
        return sorted(self._renderers)

    def list_script_backends(self) -> list[str]:
        return sorted(self._script_backends)

    def list_sfx_packs(self) -> list[str]:
        return sorted(self._sfx_packs)

    # ── Discovery ───────────────────────────────────────────────────

    def discover(self) -> None:
        """Load plugins registered via the ``radio_drama_creator`` entry-point group.

        Safe to call multiple times — entry points are only loaded once.
        """
        if self._discovered:
            return
        self._discovered = True

        try:
            from importlib.metadata import entry_points
        except ImportError:
            return

        eps = entry_points()
        # Python 3.12+ returns a SelectableGroups; 3.9+ supports .select()
        if hasattr(eps, "select"):
            group = eps.select(group="radio_drama_creator")
        else:
            group = eps.get("radio_drama_creator", [])

        for ep in group:
            try:
                plugin_init = ep.load()
                plugin_init(self)
                logger.info("Loaded plugin %r from %s", ep.name, ep.value)
            except Exception:
                logger.exception("Failed to load plugin %r", ep.name)

    # ── Helpers ─────────────────────────────────────────────────────

    def resolve_sfx_from_packs(self, cue_text: str) -> Path | None:
        """Search all registered SFX packs for a matching asset."""
        for pack in self._sfx_packs.values():
            result = pack.resolve(cue_text)
            if result is not None:
                return result
        return None

    def clear(self) -> None:
        """Remove all registered plugins (useful for testing)."""
        self._renderers.clear()
        self._script_backends.clear()
        self._sfx_packs.clear()
        self._discovered = False


# Module-level singleton
registry = PluginRegistry()
