"""临时目录中验证真实PDF/索引发布；向量模型以确定性小模型替代。"""
import base64
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import faiss
import numpy as np
import pymupdf
from webui import library
from src.knowledge_base import create_version, load_knowledge_base

class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.patcher=patch.object(library,'ROOT',self.root);self.patcher.start();self.addCleanup(self.patcher.stop)
        index=faiss.IndexFlatIP(3);index.add(np.array([[1,0,0]],dtype='float32'))
        ip=self.root/'old.index';faiss.write_index(index,str(ip))
        cp=self.root/'old.json';cp.write_text(json.dumps([{'chunk_id':0,'source':'old.pdf','title':'Old','page':1,'section':None,'text':'Original evidence remains unchanged.'}]))
        create_version(self.root/'data/processed',library.BASE_VERSION,ip,cp,{'embedding_model':library.EMBEDDING,'source_pdfs':{}})

    def pdf(self, text='A new uploaded paper states that the test device uses seven chambers. The chambers collect clean water independently.'):
        doc=pymupdf.open();page=doc.new_page();page.insert_text((72,72),text,fontsize=9)
        body=doc.tobytes();doc.close();return body

    def payload(self, body=None, name='new.pdf'):
        return {'files':[{'name':name,'data':base64.b64encode(body or self.pdf()).decode()}]}

    def build(self, folder):
        class Model:
            def encode(self, texts, **kwargs): return np.array([[0,1,0] for _ in texts],dtype='float32')
        with patch('src.embedding.load_embedding_model',return_value=Model()):library.build(folder)

    def test_title_uses_large_horizontal_heading_without_metadata(self):
        doc=pymupdf.open();page=doc.new_page()
        page.insert_text((72,72),'Mamba: A test paper title',fontsize=18)
        page.insert_text((72,110),'An author',fontsize=11)
        self.assertEqual(library.paper_title(doc,'file'),'Mamba: A test paper title')
        doc.close()

    def test_batch_failure_keeps_all_new_papers_out(self):
        payload=self.payload()
        payload['files'].append({'name':'blank.pdf','data':base64.b64encode(self.pdf('')).decode()})
        _,folder=library.prepare(payload)
        with self.assertRaises(ValueError):self.build(folder)
        self.assertEqual(library.current()['version'],library.BASE_VERSION)
        self.assertEqual(len(library.catalog()['papers']),1)

    def test_two_same_content_files_in_batch_only_add_one(self):
        payload=self.payload();payload['files'].append({**payload['files'][0],'name':'copy.pdf'})
        _,folder=library.prepare(payload);self.build(folder)
        status=json.loads((folder/'status.json').read_text())
        self.assertEqual(status['added'],['new.pdf']);self.assertEqual(status['skipped'],['copy.pdf'])

    def test_pdf_import_appends_and_preserves_old_pair(self):
        before=(self.root/'data/processed/versions'/library.BASE_VERSION/'faiss.index').read_bytes()
        identity,folder=library.prepare(self.payload());self.build(folder)
        current=library.current()['version']
        index,chunks,_=load_knowledge_base(self.root/'data/processed',current)
        self.assertEqual(index.ntotal,len(chunks));self.assertGreater(len(chunks),1)
        self.assertEqual(chunks[0]['source'],'old.pdf');self.assertEqual(chunks[-1]['source'],'new.pdf')
        self.assertEqual((self.root/'data/processed/versions'/library.BASE_VERSION/'faiss.index').read_bytes(),before)
        self.assertEqual(library.catalog()['kb_version'],current)
        self.assertEqual(json.loads((folder/'status.json').read_text())['status'],'completed')
        _,hits=index.search(np.array([[0,1,0]],dtype='float32'),1)
        self.assertEqual(chunks[hits[0][0]]['source'],'new.pdf')

    def test_duplicate_batch_is_noop(self):
        body=self.pdf();_,folder=library.prepare(self.payload(body));self.build(folder)
        old=library.current();_,again=library.prepare(self.payload(body,'renamed.pdf'));self.build(again)
        self.assertEqual(library.current(),old)
        self.assertEqual(json.loads((again/'status.json').read_text())['skipped'],['renamed.pdf'])

    def test_empty_pdf_failure_keeps_current_version(self):
        _,folder=library.prepare(self.payload(self.pdf('')))
        with self.assertRaises(ValueError):self.build(folder)
        self.assertEqual(library.current()['version'],library.BASE_VERSION)
        self.assertEqual(json.loads((folder/'status.json').read_text())['status'],'failed')

    def test_names_and_non_pdf_rejected(self):
        for data in [self.payload(name='../bad.pdf'),self.payload(b'not a pdf'),{'files':[]}]:
            with self.assertRaises(ValueError):library.prepare(data)

    def test_build_failure_does_not_publish_pointer(self):
        _,folder=library.prepare(self.payload())
        with patch('src.embedding.load_embedding_model',side_effect=RuntimeError('fixture failure')):
            with self.assertRaises(RuntimeError):library.build(folder)
        self.assertFalse((self.root/'data/webui/library.json').exists())

if __name__=='__main__':unittest.main()
