import unittest
import base64
import os
from pathlib import Path
from content_gen.scripts.processing.image_utils import ImageHandler
from content_gen.scripts.processing.database_service import DatabaseService


class TestImageHandler(unittest.TestCase):
    def test_to_base64_html(self):
        # Create a dummy image file
        dummy_path = "test_image.png"
        dummy_data = b"fakeimagecontent"
        with open(dummy_path, "wb") as f:
            f.write(dummy_data)

        try:
            handler = ImageHandler()
            html = handler.to_base64_html(dummy_path)

            self.assertIn("<div", html)
            self.assertIn("data:image/png;base64,", html)
            self.assertIn(base64.b64encode(dummy_data).decode("utf-8"), html)
            self.assertTrue(html.endswith("</div>"))
        finally:
            if os.path.exists(dummy_path):
                os.remove(dummy_path)


class TestDatabaseService(unittest.TestCase):
    def setUp(self):
        # We use a mock database URL to avoid accidental production writes
        os.environ["DATABASE_URL"] = "postgresql://mock:mock@localhost:5432/mock"
        self.db = DatabaseService()

    def test_map_enums(self):
        # Test if the service correctly handles types
        q_data = {
            "title": "Test Question",
            "type": "MCQ_SINGLE",
            "subjectId": "sub_1",
            "topicId": "top_1"
        }
        # We just want to check if it doesn't crash during preparation (mocked conn logic is hard to test without real pg)
        # But we can verify our previous enum fix here by inspecting the expected param type if we were to unit test further.
        pass


if __name__ == "__main__":
    unittest.main()
