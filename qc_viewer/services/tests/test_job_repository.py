import unittest

from qc_viewer.services.job_repository import (
    InMemoryJobRepository,
    SqliteJobRepository,
    get_job_repository,
    set_job_repository,
)


class TestJobRepository(unittest.TestCase):
    def tearDown(self) -> None:
        set_job_repository(None)

    def test_in_memory_put_get_merge(self):
        r = InMemoryJobRepository()
        r.put("j1", {"status": "PROCESSING", "id": "j1"})
        r.merge("j1", {"progress": 50})
        row = r.get("j1")
        if row is None:
            self.fail("Expected row to exist for j1")
        self.assertEqual(row["status"], "PROCESSING")
        self.assertEqual(row["progress"], 50)

    def test_sqlite_roundtrip(self):
        import os
        import tempfile

        fd, path = tempfile.mkstemp(suffix="_jobs.db")
        os.close(fd)
        try:
            r = SqliteJobRepository(path)
            r.put("x", {"a": 1})
            self.assertEqual(r.get("x"), {"a": 1})
            r.merge("x", {"b": 2})
            self.assertEqual(r.get("x"), {"a": 1, "b": 2})
        finally:
            os.unlink(path)

    def test_singleton_reset(self):
        set_job_repository(InMemoryJobRepository())
        get_job_repository().put("singleton", {"ok": True})
        row = get_job_repository().get("singleton")
        if row is None:
            self.fail("Expected singleton row to exist")
        self.assertTrue(row["ok"])


if __name__ == "__main__":
    unittest.main()
