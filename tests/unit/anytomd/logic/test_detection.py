"""Detection: whole-content detection for paths and bytes."""

from anytomd.logic.detection import Detection


async def test_detection_path_uses_its_name(path_of) -> None:
    assert Detection().run(path_of("script.py"), None) == "py"


async def test_detection_name_overrides_the_path(path_of) -> None:
    assert Detection().run(path_of("notes.txt"), "notes.csv") == "csv"


async def test_detection_arun(raw) -> None:
    assert await Detection().arun(raw("book.xlsx"), None) == "xlsx"
