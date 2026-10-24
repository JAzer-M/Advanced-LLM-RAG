import unittest

from main import build_context


class ContextMetadataTests(unittest.TestCase):
    def test_existing_paper_title_reaches_the_numbered_source_header(self):
        passage = {'source':'2004.04906v3.pdf', 'title':'Dense Passage Retrieval for Open-Domain Question Answering',
                   'page':3, 'section':'Methods', 'text':'We use two independent BERT networks.'}
        context = build_context([passage])
        self.assertIn('[1] Source: 2004.04906v3.pdf',context)
        self.assertIn('Title: '+passage['title'],context)
        self.assertIn(passage['text'],context)

    def test_missing_title_preserves_legacy_source_header(self):
        passage = {'source':'paper.pdf', 'page':2, 'text':'Original source text.'}
        self.assertEqual(build_context([passage]),
            '[1] Source: paper.pdf | Page: 2 | Section: None\nOriginal source text.')

    def test_title_already_in_filename_does_not_change_legacy_context(self):
        passage = {'source':'VGG.pdf', 'title':'VGG', 'page':2, 'text':'Original source text.'}
        self.assertEqual(build_context([passage]),
            '[1] Source: VGG.pdf | Page: 2 | Section: None\nOriginal source text.')


if __name__=='__main__':
    unittest.main()
