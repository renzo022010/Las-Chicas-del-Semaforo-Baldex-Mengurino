"""Pruebas del calculo de UFC, el registro de muestras y el arranque sin motor neuronal."""
import io,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from fastapi.testclient import TestClient
import api,muestras
from muestras import UfcInput,calcular_ufc

def dil(exponent,a=None,b=None,volume=.1):
    return {'exponent':exponent,'volume_ml':volume,'plate_a':{'count':a},'plate_b':{'count':b}}

class UfcTests(unittest.TestCase):
    def test_uses_dilutions_in_countable_range(self):
        r=calcular_ufc(UfcInput(dilutions=[dil(1,250,260),dil(2,45,48),dil(3,3,5)]))
        # 10^-1: 255*10/0.1=25500; 10^-2: 46.5*100/0.1=46500 -> mean 36000
        self.assertAlmostEqual(r['value'],36000)
        self.assertEqual(r['dilutions_used'],[1,2]);self.assertTrue(r['in_range']);self.assertEqual(r['warnings'],[])

    def test_estimates_with_closest_dilution_when_none_in_range(self):
        r=calcular_ufc(UfcInput(dilutions=[dil(1,12,15),dil(2,1,2),dil(3,0,0)]))
        self.assertFalse(r['in_range']);self.assertEqual(r['dilutions_used'],[1])
        self.assertAlmostEqual(r['value'],13.5*10/.1);self.assertTrue(r['warnings'])

    def test_all_zero_reports_detection_limit(self):
        r=calcular_ufc(UfcInput(dilutions=[dil(1,0,0),dil(2,0,0)],unit='g'))
        self.assertEqual(r['value'],0);self.assertAlmostEqual(r['detection_limit'],100)
        self.assertEqual(r['unit'],'UFC/g')

    def test_single_plate_and_empty_input(self):
        self.assertIsNone(calcular_ufc(UfcInput(dilutions=[dil(1)])))
        r=calcular_ufc(UfcInput(dilutions=[dil(2,100)]))
        self.assertAlmostEqual(r['value'],100000);self.assertTrue(any('una sola placa' in w for w in r['warnings']))

    def test_rejects_inverted_range(self):
        with self.assertRaises(ValueError):UfcInput(count_min=300,count_max=30)

class SampleApiTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        tmp=Path(self.tmp.name)
        self.patches=[patch.object(muestras,'DB',tmp/'m.db'),patch.object(api,'OUTPUT',tmp/'api')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()

    def test_crud_codes_and_result(self):
        with patch.dict('os.environ',{'MOTOR':'clasico'}),TestClient(api.app) as client:
            body={'analyzed_at':'2026-10-28T10:30','sample_type':'Suelo','responsible':'Maria Garcia','dilutions':[dil(2,45,48)]}
            a=client.post('/samples',json=body);self.assertEqual(a.status_code,201,a.text)
            b=client.post('/samples',json=body).json()
            self.assertEqual((a.json()['code'],b['code']),('M-00001','M-00002'))
            self.assertAlmostEqual(a.json()['result']['value'],46500)
            body['dilutions']=[dil(1,30,40)]
            u=client.put(f"/samples/{a.json()['id']}",json=body).json()
            self.assertAlmostEqual(u['result']['value'],3500)
            listed=client.get('/samples').json()
            self.assertEqual([s['code'] for s in listed],['M-00002','M-00001'])
            self.assertEqual(client.delete(f"/samples/{b['id']}").status_code,204)
            self.assertEqual(client.get(f"/samples/{b['id']}").status_code,404)
            self.assertEqual(client.post('/samples',json={**body,'responsible':''}).status_code,422)
            self.assertEqual(client.post('/ufc',json={'dilutions':[dil(1,30,40)]}).json()['value'],3500)

    def test_classic_fallback_when_neural_engine_fails(self):
        def broken():raise RuntimeError('sin pesos')
        with patch.object(api,'HybridCounter',broken),TestClient(api.app) as client:
            health=client.get('/health').json()
            self.assertEqual(health['engines'],['classic']);self.assertIn('sin pesos',health['neural_error'])
            raw=io.BytesIO();Image.new('RGB',(128,96),(180,180,180)).save(raw,format='PNG')
            self.assertEqual(client.post('/analyze?engine=hybrid',files={'file':('p.png',raw.getvalue(),'image/png')}).status_code,503)
            r=client.post('/analyze',files={'file':('p.png',raw.getvalue(),'image/png')})
            self.assertEqual(r.status_code,200,r.text);self.assertEqual(r.json()['engine'],'classic')
            self.assertEqual(client.get(r.json()['original_url']).status_code,200)

if __name__=='__main__':unittest.main(verbosity=2)
