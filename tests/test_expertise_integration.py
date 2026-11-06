"""Karışık kaynakların kapsamını, atfını ve uygulama sınırını ağsız sınar."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from database import import_expertise as importer
from database.search import search_chunks
import rag_repository
import rag_service
import rag_ticket_pilotu as rag


def example():
    original={
        'source_record_id':'dba:q1:a2','domain':'oracle_db','question_id':1,'answer_id':2,
        'answer_accepted':True,'problem':'Problem','solution':'Unreviewed DROP TABLE secret_table;',
        'source_url':'https://dba.stackexchange.com/questions/1/example','answer_url':'https://dba.stackexchange.com/a/2',
        'question_license':'CC BY-SA 3.0','answer_license':'CC BY-SA 4.0',
        'question_license_url':'https://creativecommons.org/licenses/by-sa/3.0/','answer_license_url':'https://creativecommons.org/licenses/by-sa/4.0/',
        'question_author':{'name':'Question Author','url':'https://dba.stackexchange.com/users/1'},
        'answer_author':{'name':'Answer Author','url':'https://dba.stackexchange.com/users/2'},
    }
    row=copy.deepcopy(original)
    row.update({'original_source':original,'review_decision':'uygun_sinirli_kapsam',
        'official_verification_status':'partially_supported_scoped','resolution_confirmed':None,
        'title':'A source','source_name':'Database Administrators','source_version':'test',
        'solution':'Scoped explanation only.','resolution':'No separate confirmation.',
        'limitations':'Explanation only; no commands.','solution_scope':'explanation',
        'official_sources':[{'title':'Oracle','url':'https://docs.oracle.com/'}],
        'official_context':'Separate official note.','product_version_environment':'Not specified',
        'source_evidence':[{'field':'problem','quote':'Problem'}],'whole_answer_approved':False})
    return row


class ExpertiseIntegrationTests(unittest.TestCase):
    def write_input(self,path,row):
        path.write_text(json.dumps({'format_version':1,'records':[row]}),encoding='utf-8')

    def test_import_checks_pair_attribution_and_confirmation(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'records.json'
            self.write_input(path,example())
            self.assertEqual(len(importer.load_records(path)),1)
            for key,value in [('source_record_id','dba:q1:a999'),('answer_license','other'),('resolution_confirmed',True)]:
                row=example(); row[key]=value; self.write_input(path,row)
                with self.subTest(key=key),self.assertRaises(ValueError): importer.load_records(path)

    def test_only_curated_scope_is_embedded(self):
        text=importer.embedding_text(example())
        self.assertIn('Scoped explanation only',text)
        self.assertIn('Explanation only; no commands',text)
        self.assertIn('Separate official note',text)
        self.assertNotIn('DROP TABLE',text)

    def test_changed_curated_text_rejects_stale_cache(self):
        row=example()
        cache={'model':importer.vectors.MODEL,'dimensions':1024,'record_hashes':[importer.digest(row)],
            'text_hashes':[importer.digest(importer.embedding_text(row))],'vectors':[[1.0]+[0.0]*1023]}
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'cache.json'; path.write_text(json.dumps(cache),encoding='utf-8')
            self.assertEqual(len(importer.load_vectors(path,[row])[0]),1024)
            row['limitations']='Changed scope'
            with self.assertRaises(ValueError): importer.load_vectors(path,[row])

    def test_specialist_mode_keeps_general_cases_and_excludes_other_specialty(self):
        with patch.object(rag,'database_matches',return_value=[]) as search:
            rag_repository.search_matches([1.0],expertise_mode='oracle_db')
            search.assert_called_once_with([1.0],domains=('general_it','oracle_db'))
        with patch.object(rag,'database_matches',return_value=[]) as search:
            rag_repository.search_matches([1.0],expertise_mode='windows_server')
            search.assert_called_once_with([1.0],domains=('general_it','windows_server'))

    def test_search_exposes_curated_answer_and_per_post_attribution(self):
        row=example()
        metadata={k:row[k] for k in ['answer_url','question_author','answer_author','question_license','answer_license']}
        metadata['question_url']=row['source_url']
        metadata['raw_secret']='Unreviewed DROP TABLE secret_table;'
        dbrow=(.9,'chunk','Database Administrators','https://dba.stackexchange.com',row['source_record_id'],
            row['problem'],'oracle_db',row['solution'],row['resolution'],None,None,'explanation',row['limitations'],
            'qa','oracle_db',row['title'],metadata)
        connection=MagicMock(); connection.execute.return_value.fetchall.return_value=[dbrow]
        with patch('database.search.connect') as factory:
            factory.return_value.__enter__.return_value=connection
            matches=search_chunks([1.0]+[0.0]*1023,embedding_model=importer.vectors.MODEL,domains=('general_it','oracle_db'))
        record=matches[0][1]
        self.assertEqual(record['source_url'],row['source_url'])
        self.assertEqual(record['answer_license'],'CC BY-SA 4.0')
        self.assertEqual(record['source_comment_seq'],{})
        context=json.loads(rag.request_body('question',matches)['input'][0]['content'])
        self.assertNotIn('DROP TABLE',json.dumps(context))
        sql,params=connection.execute.call_args.args
        self.assertIn('r.domain=ANY',sql)
        self.assertEqual(params[2:4],(['general_it','oracle_db'],['general_it','oracle_db']))

    def test_answer_sources_are_selected_from_used_records_only(self):
        qa=example(); qa['issueid']=qa['source_record_id']; qa['record_type']='qa'
        matches=[(.9,qa),(.8,{'issueid':'1007444.0','record_type':'ticket'})]
        answer={'answer':'dba:q1:a2 için açıklama','used_ticket_ids':['dba:q1:a2'],'insufficient_context':False}
        with (patch('rag_provider.embed_question',return_value=[1.0]),
              patch('rag_repository.search_matches',return_value=matches) as search,
              patch('rag_provider.answer_from_matches',return_value=answer)):
            result=rag_service.ask_question('Oracle question',expertise_mode='oracle_db')
        search.assert_called_once_with([1.0],expertise_mode='oracle_db')
        self.assertEqual(result['used_source_ids'],['dba:q1:a2'])
        self.assertEqual(len(result['sources']),1)
        self.assertEqual(result['sources'][0]['question_license'],'CC BY-SA 3.0')
        self.assertEqual(result['sources'][0]['answer_license'],'CC BY-SA 4.0')
        self.assertNotIn('original_source',result['sources'][0])


if __name__=='__main__': unittest.main()
