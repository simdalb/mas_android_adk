from pathlib import Path
import tempfile

from app.domain.models import MediaLink
from app.services.storage import LocalMediaRepository


def test_storage_crud_cycle():
    with tempfile.TemporaryDirectory() as tmp:
        repo_path = str(Path(tmp) / "media_links.json")
        repo = LocalMediaRepository(path=repo_path)

        created = repo.add(
            MediaLink(
                title="Example",
                url="https://example.com",
                tags=["video", "sample"],
                description="A sample item",
            )
        )
        assert repo.get(created.link_id) is not None

        created.title = "Updated Example"
        repo.update(created)
        loaded = repo.get(created.link_id)
        assert loaded is not None
        assert loaded.title == "Updated Example"

        results = repo.search("updated")
        assert len(results) == 1
        assert results[0].link_id == created.link_id

        deleted = repo.delete(created.link_id)
        assert deleted is True
        assert repo.get(created.link_id) is None