"""Regression checks for favorites persistence and edits."""

import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "allmon_favorites", Path(__file__).resolve().parents[1] / "src/asl_allmon/favorites/__init__.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
FavoritesStore = module.FavoritesStore
FavoritesError = module.FavoritesError


class FavoritesTest(unittest.TestCase):
    def test_save_rename_delete_and_reload_per_source(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "favorites.json"
            store = FavoritesStore(path)
            self.assertEqual(store.list(1999), [])
            store.change(1999, "save", "62154", "Starbase 4")
            store.change(2000, "save", "3002560", "WINS 100%")
            self.assertEqual(FavoritesStore(path).list(1999), [
                {"node": "62154", "label": "Starbase 4"}])
            store.change(1999, "save", "62155", "New name", original_node="62154")
            self.assertEqual(store.list(1999), [
                {"node": "62155", "label": "New name"}])
            store.change(1999, "delete", "62155")
            self.assertEqual(store.list(1999), [])
            self.assertEqual(store.list(2000), [
                {"node": "3002560", "label": "WINS 100%"}])
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)

    def test_conflict_and_invalid_input_do_not_erase_favorites(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            store = FavoritesStore(Path(temp_dir) / "favorites.json")
            store.change(1999, "save", "111", "First")
            store.change(1999, "save", "222", "Second")
            with self.assertRaisesRegex(FavoritesError, "already a favorite"):
                store.change(1999, "save", "222", "Oops", original_node="111")
            with self.assertRaisesRegex(FavoritesError, "numeric node"):
                store.change(1999, "save", "*3222", "Invalid")
            with self.assertRaisesRegex(FavoritesError, "Favorite changed"):
                store.change(1999, "save", "333", "Stale", original_node="444")
            self.assertEqual(store.list(1999), [
                {"node": "111", "label": "First"},
                {"node": "222", "label": "Second"}])

    def test_damaged_file_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "favorites.json"
            path.write_text("{not json")
            store = FavoritesStore(path)
            with self.assertRaises(FavoritesError):
                store.change(1999, "save", "111", "New")
            self.assertEqual(path.read_text(), "{not json")


if __name__ == "__main__":
    unittest.main()
