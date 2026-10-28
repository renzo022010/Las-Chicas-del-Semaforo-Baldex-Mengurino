"""Pruebas de geometria y contrato API; no sustituyen la evaluacion neuronal."""
import asyncio,io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
from PIL import Image
from fastapi.testclient import TestClient
from contador_hibrido import NeuralConfig,plate_region,compact_mask,duplicate_mask
import api

class HybridTests(unittest.TestCase):
    def test_manual_roi_scaling(self):
        im=np.zeros((200,300,3),np.uint8)
        valid,radial,ellipse,method,crop=plate_region(im,0,(300,200,150),.5)
        self.assertEqual(ellipse,(150,100,75,75,0.))
        self.assertEqual(method,'manual');self.assertTrue(valid[100,220]);self.assertFalse(valid[100,230])
        self.assertGreater(crop[2],220)
    def test_duplicate_masks_preserve_distinct_neighbors(self):
        a=np.zeros((100,100),bool);a[20:40,20:40]=True
        b=np.zeros_like(a);b[20:40,35:55]=True
        c=np.zeros_like(a);c[70:90,70:90]=True
        self.assertTrue(duplicate_mask(compact_mask(a),[compact_mask(a)],.8))
        self.assertFalse(duplicate_mask(compact_mask(b),[compact_mask(a)],.8))
        self.assertFalse(duplicate_mask(compact_mask(c),[compact_mask(a)],.8))

    def test_invalid_roi_and_config(self):
        for threshold in [0,-1,2,float('nan')]:
            with self.assertRaises(ValueError):NeuralConfig(box_threshold=threshold).validate()
        with self.assertRaises(ValueError):plate_region(np.zeros((200,200,3),np.uint8),0,(10,10,-1))
    def test_upload_validation_and_manual_review(self):
        class FakeCounter:
            hardware='test-double'
        with tempfile.TemporaryDirectory() as tmp,patch.object(api,'OUTPUT',Path(tmp)),patch.object(api,'HybridCounter',FakeCounter):
            with TestClient(api.app) as client:
                self.assertTrue(client.get('/health').json()['ready'])
                self.assertEqual(client.post('/analyze',files={'file':('x.jpg',b'invalid','image/jpeg')}).status_code,400)
                raw=io.BytesIO();Image.new('RGB',(128,128),(180,180,180)).save(raw,format='PNG')
                response=client.post('/analyze?engine=classic',files={'file':('photo.png',raw.getvalue(),'image/png')})
                self.assertEqual(response.status_code,200,response.text)
                record=response.json();ident=record['analysis_id']
                self.assertEqual(record['count'],0)
                self.assertEqual(client.get(record['annotated_url']).status_code,200)
                original=(Path(tmp)/ident/'foto_resultado.json').read_bytes()
                r=client.post(f'/results/{ident}/review',json={'centers':[{'x':64,'y':64}],'note':'correccion de prueba'})
                self.assertEqual(r.json()['reviewed_count'],1)
                self.assertEqual(original,(Path(tmp)/ident/'foto_resultado.json').read_bytes())
                bad=client.post(f'/results/{ident}/review',json={'centers':[{'x':200,'y':64}]})
                self.assertEqual(bad.status_code,400)
                self.assertEqual(client.get('/results/'+'a'*32+'/contador.py').status_code,404)
if __name__=='__main__':unittest.main(verbosity=2)
