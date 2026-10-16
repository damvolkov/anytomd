"""Vision model settings from the environment (`ANYTOMD_VISION_*`); needs the `vlm` extra."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from anytomd.infra.specs import VisionSpec


class VisionSettings(BaseSettings):
    """`ANYTOMD_VISION_MODEL` switches the vision fallback on; the rest refines it."""

    model_config = SettingsConfigDict(env_prefix="ANYTOMD_VISION_")

    model: str | None = None
    base_url: str | None = None
    api_key: str | None = None
    prompt: str | None = None
    max_tokens: int | None = None
    concurrency: int | None = None

    def spec(self) -> VisionSpec | None:
        """The configured model as a spec, or None when no model is set."""
        overrides = {key: value for key, value in self.model_dump(exclude={"model"}).items() if value is not None}
        return VisionSpec(model=self.model, **overrides) if self.model else None
