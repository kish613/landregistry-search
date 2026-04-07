"""Tests for the download_dataset resource parsing in update_data.py."""

import os
import sys
import tempfile
import unittest
from unittest.mock import patch, MagicMock

# Make the scripts directory importable
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Patch env vars before importing the module
with patch.dict(os.environ, {'DATABASE_URL': 'fake', 'LAND_REGISTRY_API_KEY': 'fake-key'}):
    import update_data


class TestDownloadDatasetParsing(unittest.TestCase):
    """Test that download_dataset correctly parses the Land Registry API response."""

    @patch('update_data.requests.get')
    def test_resources_under_result_key(self, mock_get):
        """API wraps resources under 'result' — should find them."""
        api_response = {
            'result': {
                'resources': [
                    {
                        'file_name': 'CCOD_FULL_2026_04.zip',
                        'name': 'Full dataset',
                        'file_size': '5 GB',
                    }
                ]
            }
        }
        metadata_resp = MagicMock()
        metadata_resp.json.return_value = api_response

        download_resp = MagicMock()
        download_resp.__enter__ = MagicMock(return_value=download_resp)
        download_resp.__exit__ = MagicMock(return_value=False)
        download_resp.iter_content.return_value = [b'fake-csv-data']

        mock_get.side_effect = [metadata_resp, download_resp]

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            dest = f.name

        try:
            update_data.download_dataset('ccod', dest)
        finally:
            os.unlink(dest)

        # The download URL should be constructed from file_name
        download_call = mock_get.call_args_list[1]
        self.assertIn('ccod', download_call[0][0])
        self.assertIn('CCOD_FULL_2026_04.zip', download_call[0][0])

    @patch('update_data.requests.get')
    def test_public_resources_fallback(self, mock_get):
        """Should fall back to 'public_resources' if 'resources' is empty."""
        api_response = {
            'result': {
                'resources': [],
                'public_resources': [
                    {
                        'file_name': 'CCOD_FULL_2026_04.zip',
                        'name': 'Full file',
                    }
                ]
            }
        }
        metadata_resp = MagicMock()
        metadata_resp.json.return_value = api_response

        download_resp = MagicMock()
        download_resp.__enter__ = MagicMock(return_value=download_resp)
        download_resp.__exit__ = MagicMock(return_value=False)
        download_resp.iter_content.return_value = [b'fake-csv-data']

        mock_get.side_effect = [metadata_resp, download_resp]

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            dest = f.name

        try:
            update_data.download_dataset('ccod', dest)
        finally:
            os.unlink(dest)

        download_call = mock_get.call_args_list[1]
        self.assertIn('CCOD_FULL_2026_04.zip', download_call[0][0])

    @patch('update_data.requests.get')
    def test_selects_full_file_by_file_name(self, mock_get):
        """Should prefer the resource whose file_name contains 'full'."""
        api_response = {
            'result': {
                'resources': [
                    {'file_name': 'CCOD_COU_2026_04.zip', 'name': 'Change only'},
                    {'file_name': 'CCOD_FULL_2026_04.zip', 'name': 'Full dataset'},
                ]
            }
        }
        metadata_resp = MagicMock()
        metadata_resp.json.return_value = api_response

        download_resp = MagicMock()
        download_resp.__enter__ = MagicMock(return_value=download_resp)
        download_resp.__exit__ = MagicMock(return_value=False)
        download_resp.iter_content.return_value = [b'fake-csv-data']

        mock_get.side_effect = [metadata_resp, download_resp]

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            dest = f.name

        try:
            update_data.download_dataset('ccod', dest)
        finally:
            os.unlink(dest)

        download_call = mock_get.call_args_list[1]
        self.assertIn('CCOD_FULL_2026_04.zip', download_call[0][0])

    @patch('update_data.requests.get')
    def test_explicit_url_takes_priority(self, mock_get):
        """If resource has an explicit 'url', it should be used directly."""
        api_response = {
            'result': {
                'resources': [
                    {
                        'file_name': 'CCOD_FULL_2026_04.zip',
                        'name': 'Full dataset',
                        'url': 'https://example.com/direct-download/CCOD_FULL.zip',
                    }
                ]
            }
        }
        metadata_resp = MagicMock()
        metadata_resp.json.return_value = api_response

        download_resp = MagicMock()
        download_resp.__enter__ = MagicMock(return_value=download_resp)
        download_resp.__exit__ = MagicMock(return_value=False)
        download_resp.iter_content.return_value = [b'fake-csv-data']

        mock_get.side_effect = [metadata_resp, download_resp]

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            dest = f.name

        try:
            update_data.download_dataset('ccod', dest)
        finally:
            os.unlink(dest)

        download_call = mock_get.call_args_list[1]
        self.assertEqual(download_call[0][0], 'https://example.com/direct-download/CCOD_FULL.zip')

    @patch('update_data.requests.get')
    def test_no_resources_raises_error(self, mock_get):
        """Should raise RuntimeError when no resources are available."""
        api_response = {
            'result': {
                'resources': [],
                'public_resources': [],
            }
        }
        metadata_resp = MagicMock()
        metadata_resp.json.return_value = api_response

        mock_get.return_value = metadata_resp

        with self.assertRaises(RuntimeError) as ctx:
            update_data.download_dataset('ccod', '/tmp/test.csv')

        self.assertIn('No downloadable resource', str(ctx.exception))

    @patch('update_data.requests.get')
    def test_legacy_flat_response_still_works(self, mock_get):
        """Backward compat: if API returns resources at top level (no 'result'), still works."""
        api_response = {
            'resources': [
                {
                    'file_name': 'CCOD_FULL_2026_04.zip',
                    'name': 'Full dataset',
                }
            ]
        }
        metadata_resp = MagicMock()
        metadata_resp.json.return_value = api_response

        download_resp = MagicMock()
        download_resp.__enter__ = MagicMock(return_value=download_resp)
        download_resp.__exit__ = MagicMock(return_value=False)
        download_resp.iter_content.return_value = [b'fake-csv-data']

        mock_get.side_effect = [metadata_resp, download_resp]

        with tempfile.NamedTemporaryFile(suffix='.csv', delete=False) as f:
            dest = f.name

        try:
            update_data.download_dataset('ccod', dest)
        finally:
            os.unlink(dest)

        download_call = mock_get.call_args_list[1]
        self.assertIn('CCOD_FULL_2026_04.zip', download_call[0][0])


if __name__ == '__main__':
    unittest.main()
