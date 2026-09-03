from asset_manager import ArtStyle, AssetManager, ILLUSTRATED_ASSETS


def test_classic_style_uses_procedural_fallback(tmp_path):
    assets = AssetManager(lambda relative: tmp_path / relative)

    assert assets.get(ArtStyle.CLASSIC, "hero/idle") is None
    assert assets.missing_assets(ArtStyle.CLASSIC) == []


def test_missing_illustrated_assets_are_reported(tmp_path):
    assets = AssetManager(lambda relative: tmp_path / relative)

    assert assets.missing_assets(ArtStyle.ILLUSTRATED) == list(ILLUSTRATED_ASSETS)
