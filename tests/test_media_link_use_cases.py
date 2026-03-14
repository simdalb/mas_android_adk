from pathlib import Path
import tempfile

from app.domain.models import MediaLink
from app.services.storage import DuplicateMediaLinkError, LocalMediaRepository
from app.use_cases.media_links import MediaLinkUseCases


def test_media_link_use_cases_crud_and_search():
    with tempfile.TemporaryDirectory() as tmp:
        repo = LocalMediaRepository(path=str(Path(tmp) / "media_links.json"))
        use_cases = MediaLinkUseCases(repository=repo)

        created = use_cases.create_link(
            title="Example item",
            url="https://example.com/watch",
            tags=["sample", "video"],
            description="demo",
        )
        assert created.link_id

        loaded = use_cases.get_link(created.link_id)
        assert loaded is not None
        assert loaded.title == "Example item"

        loaded.title = "Updated item"
        use_cases.update_link(loaded)

        results = use_cases.search_links("updated")
        assert len(results) == 1
        assert results[0].title == "Updated item"

        deleted = use_cases.delete_link(created.link_id)
        assert deleted is True
        assert use_cases.get_link(created.link_id) is None


def test_media_link_use_cases_normalize_tags_and_reject_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        repo = LocalMediaRepository(path=str(Path(tmp) / "media_links.json"))
        use_cases = MediaLinkUseCases(repository=repo)

        created = use_cases.create_link(
            title="Example item",
            url="https://example.com/watch",
            tags=[" sample ", "", "video"],
            description="demo",
        )
        assert created.tags == ["sample", "video"]

        try:
            use_cases.create_link(
                title="Example item",
                url="https://example.com/watch",
                tags=["sample"],
            )
            assert False, "Expected DuplicateMediaLinkError"
        except DuplicateMediaLinkError:
            assert True


def test_media_link_use_cases_safe_create_returns_error_payload():
    with tempfile.TemporaryDirectory() as tmp:
        repo = LocalMediaRepository(path=str(Path(tmp) / "media_links.json"))
        use_cases = MediaLinkUseCases(repository=repo)

        result = use_cases.create_link_safe(title="", url="")
        assert result["ok"] is False
        assert result["link"] is None
        assert result["error"]


def test_media_link_use_cases_safe_update_returns_error_payload():
    with tempfile.TemporaryDirectory() as tmp:
        repo = LocalMediaRepository(path=str(Path(tmp) / "media_links.json"))
        use_cases = MediaLinkUseCases(repository=repo)

        created = use_cases.create_link(
            title="Example item",
            url="https://example.com/watch",
            tags=["sample"],
        )

        conflicting = use_cases.create_link(
            title="Another item",
            url="https://example.com/other",
            tags=["sample"],
        )

        conflicting.title = created.title
        conflicting.url = created.url

        result = use_cases.update_link_safe(conflicting)
        assert result["ok"] is False
        assert result["link"] is None
        assert result["error"]

        broken = MediaLink(
            title="",
            url="",
            link_id=created.link_id,
        )
        result2 = use_cases.update_link_safe(broken)
        assert result2["ok"] is False
        assert result2["error"]