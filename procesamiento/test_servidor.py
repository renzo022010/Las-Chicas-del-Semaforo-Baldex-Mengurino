"""Pruebas del servidor unico: PWA compilada, prefijo /api y clave de acceso."""
import tempfile,unittest
from pathlib import Path
from fastapi.testclient import TestClient
from app.main import create_app

class ServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        root=Path(self.tmp.name);self.root=root
        web=root/'web';(web/'assets').mkdir(parents=True)
        (web/'index.html').write_text('<!doctype html><title>PWA</title>',encoding='utf-8')
        (web/'assets'/'app.js').write_text('console.log(1)',encoding='utf-8')
        self.web=web
    def tearDown(self):self.tmp.cleanup()
    def client(self,key=None):
        return TestClient(create_app(output=self.root/'api',samples_db=self.root/'m.db',use_hybrid=False,web_dir=self.web,access_key=key))

    def test_serves_pwa_and_api_on_one_port(self):
        with self.client() as c:
            self.assertIn('PWA',c.get('/').text)
            self.assertIn('PWA',c.get('/resultado/abc').text)  # React resolves client routes
            self.assertEqual(c.get('/assets/app.js').text,'console.log(1)')
            self.assertEqual(c.get('/api/health').json()['engines'],['classic'])
            self.assertEqual(c.get('/health').json()['engines'],['classic'])
            self.assertEqual(c.get('/api/results/'+'a'*32+'/foto_conteo.jpg').status_code,404)

    def test_access_key_protects_api_but_not_pwa_files(self):
        with self.client(key='s3creta') as c:
            self.assertEqual(c.get('/').status_code,200)
            self.assertEqual(c.get('/api/health').status_code,401)
            self.assertEqual(c.get('/health',headers={'X-Clave':'otra'}).status_code,401)
            self.assertEqual(c.get('/docs').status_code,401)
            self.assertEqual(c.get('/api/health',headers={'X-Clave':'s3creta'}).status_code,200)
            self.assertEqual(c.get('/api/health?clave=s3creta').status_code,200)

    def test_without_build_only_api_is_served(self):
        with TestClient(create_app(output=self.root/'api',samples_db=self.root/'m.db',use_hybrid=False,web_dir=self.root/'no-existe')) as c:
            self.assertEqual(c.get('/').status_code,404)
            self.assertEqual(c.get('/health').status_code,200)

if __name__=='__main__':unittest.main(verbosity=2)
