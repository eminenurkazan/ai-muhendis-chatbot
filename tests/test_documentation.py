import copy
import unittest
from pathlib import Path
from database.import_documentation import load_record, embedding_text, digest, load_vector
from rag_sources import source_reference
import tempfile, json

class DocumentationTests(unittest.TestCase):
    def setUp(self):
        self.path = Path(__file__).resolve().parents[1] / 'data_sources/official_guides/microsoft_ad_replication.json'
        self.row = load_record(self.path)

    def test_whole_procedure_keeps_prerequisites_command_and_limitations(self):
        text = embedding_text(self.row)
        for value in [self.row['product_version_environment'], self.row['limitations'], *self.row['commands']]:
            self.assertIn(value, text)
        self.assertFalse(self.row['execution_tested'])

    def test_source_attribution_and_false_execution_flag_survive(self):
        reference = source_reference({**self.row, 'issueid': self.row['source_record_id']})
        self.assertEqual(reference['license'], 'CC-BY-4.0')
        self.assertEqual(reference['source_author'], 'Microsoft')
        self.assertIs(reference['execution_tested'], False)

    def test_missing_conditions_or_mismatched_cache_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'record.json'
            row = copy.deepcopy(self.row)
            row.pop('product_version_environment')
            path.write_text(json.dumps(row), encoding='utf-8')
            with self.assertRaises(ValueError): load_record(path)
            path.write_text(json.dumps({'record_hash': 'wrong'}), encoding='utf-8')
            with self.assertRaises(ValueError): load_vector(self.row, path)
