"""Instalacion sin Git y lanzador que no se cae si falla el motor IA. No descarga nada."""
import json,subprocess,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
import instalar,lanzador

COMMIT='a'*40

def fake_download(comment=COMMIT,top='repo-'+COMMIT):
    def retrieve(url,dest):
        with zipfile.ZipFile(dest,'w') as bundle:
            bundle.comment=comment.encode()
            bundle.writestr(top+'/',b'')
            bundle.writestr(top+'/setup.py','# setup')
            bundle.writestr(top+'/pkg/mod.py','x=1')
            bundle.writestr(top+'/demo/frontend/app.ts','skip')
            bundle.writestr(top+'/notebooks/n.ipynb','skip')
    return retrieve

class FetchRepoTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.vendor=Path(self.tmp.name)/'vendor'
    def tearDown(self):self.tmp.cleanup()
    def fetch(self,retrieve=None):
        with patch('urllib.request.urlretrieve',retrieve or fake_download()) as _:
            instalar.fetch_repo('repo','org/repo',COMMIT,self.vendor)

    def test_downloads_pinned_commit_without_top_folder(self):
        self.fetch()
        path=self.vendor/'repo'
        self.assertEqual((path/'pkg/mod.py').read_text(),'x=1')
        self.assertTrue((path/'setup.py').is_file())
        self.assertEqual(instalar.vendored_commit(path),COMMIT)
        self.assertFalse((path/'demo').exists());self.assertFalse((path/'notebooks').exists())
        self.assertEqual(sorted(p.name for p in self.vendor.iterdir()),['repo'])  # no leftovers

    def test_rejects_zip_of_another_commit_and_leaves_nothing_installed(self):
        with self.assertRaises(RuntimeError):self.fetch(fake_download(comment='b'*40))
        self.assertIsNone(instalar.vendored_commit(self.vendor/'repo'))
        self.assertFalse((self.vendor/'repo').exists())

    def test_same_commit_is_not_downloaded_again(self):
        self.fetch()
        def fail(*_):raise AssertionError('no debe descargar')
        self.fetch(fail)

    def test_recognizes_installs_made_with_git(self):
        head=self.vendor/'repo/.git/HEAD';head.parent.mkdir(parents=True);head.write_text(COMMIT+'\n')
        def fail(*_):raise AssertionError('no debe descargar')
        self.fetch(fail)

    def test_different_commit_is_not_overwritten(self):
        mark=self.vendor/'repo'/instalar.COMMIT_FILE;mark.parent.mkdir(parents=True);mark.write_text('c'*40)
        with self.assertRaises(RuntimeError):self.fetch()
        self.assertEqual(mark.read_text(),'c'*40)

    def test_partial_folder_is_replaced(self):
        (self.vendor/'repo').mkdir(parents=True);(self.vendor/'repo/resto.txt').write_text('x')
        self.fetch()
        self.assertFalse((self.vendor/'repo/resto.txt').exists())
        self.assertEqual(instalar.vendored_commit(self.vendor/'repo'),COMMIT)

    def test_antivirus_lock_on_the_zip_does_not_stop_the_install(self):
        real=Path.unlink
        calls=[]
        def locked(path,*args,**kwargs):
            calls.append(path)
            if len(calls)==1:raise PermissionError(32,'en uso')
            return real(path,*args,**kwargs)
        with patch.object(Path,'unlink',locked),patch('time.sleep'):
            self.fetch()
        self.assertEqual(len(calls),2)
        self.assertEqual(instalar.vendored_commit(self.vendor/'repo'),COMMIT)
        self.assertFalse((self.vendor/'.repo.zip').exists())

    def test_zip_that_stays_locked_is_left_behind(self):
        def locked(*_a,**_k):raise PermissionError(32,'en uso')
        with patch.object(Path,'unlink',locked),patch.object(instalar.time,'sleep'),\
             patch.object(instalar.time,'monotonic',side_effect=[0,1000]):
            self.fetch()
        self.assertEqual(instalar.vendored_commit(self.vendor/'repo'),COMMIT)

    def test_when_unlocked_gives_up_after_the_limit(self):
        def locked():raise PermissionError(32,'en uso')
        with patch.object(instalar.time,'sleep'),patch.object(instalar.time,'monotonic',side_effect=[0,1,1000]):
            with self.assertRaises(PermissionError):instalar.when_unlocked(locked,seconds=5)

    def test_install_code_never_calls_git(self):
        for name in ('instalar.py','preparar_compatibilidad_neural.py'):
            source=(Path(instalar.__file__).parent/name).read_text(encoding='utf-8')
            self.assertNotIn("'git'",source,name)

class RequirementsTests(unittest.TestCase):
    def test_uses_uv_when_available_and_pip_otherwise(self):
        with patch.object(instalar,'run') as run,patch.dict('os.environ',{'UV_EXE':'uv.exe'}):
            instalar.install_requirements('py.exe','req.txt')
        self.assertEqual(run.call_args.args[:2],('uv.exe','pip'))
        self.assertIn('unsafe-best-match',run.call_args.args)
        cache=run.call_args.args[run.call_args.args.index('--cache-dir')+1]
        self.assertNotIn(instalar.ROOT,cache.parents)  # builds from source need a short path
        with patch.object(instalar,'run') as run,patch.dict('os.environ',{'UV_EXE':''}),patch('shutil.which',return_value=None):
            instalar.install_requirements('py.exe','req.txt')
        self.assertEqual(run.call_args.args,('py.exe','-m','pip','install','-r','req.txt'))

class WindowStaysOpenTests(unittest.TestCase):
    def test_launcher_pauses_on_any_nonzero_exit_code(self):
        # "if errorlevel 1" misses the negative codes of a native crash, and the window would close without a message.
        cmd=(instalar.ROOT.parent/'INICIAR.cmd').read_text(encoding='utf-8')
        self.assertIn('if not "%errorlevel%"=="0" goto :error',cmd)
        self.assertNotIn('if errorlevel 1',cmd)
        self.assertIn('pause',cmd.split(':error')[-1])

class CppRuntimeTests(unittest.TestCase):
    def test_runtime_is_copied_next_to_torch(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=Path(tmp);lib=env/'Lib/site-packages/torch/lib';lib.mkdir(parents=True)
            (env/'msvcp140.dll').write_text('dll');(env/'msvcp140_1.dll').write_text('dll');(env/'otra.dll').write_text('x')
            instalar.place_cpp_runtime(env)
            self.assertEqual(sorted(p.name for p in lib.iterdir()),['msvcp140.dll','msvcp140_1.dll'])

    def test_antivirus_lock_on_the_runtime_is_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            env=Path(tmp);lib=env/'Lib/site-packages/torch/lib';lib.mkdir(parents=True)
            (env/'msvcp140.dll').write_text('dll')
            real=instalar.shutil.copy2;calls=[]
            def locked(src,dst):
                calls.append(src)
                if len(calls)==1:raise PermissionError(32,'en uso')
                return real(src,dst)
            with patch.object(instalar.shutil,'copy2',locked),patch.object(instalar.time,'sleep'):
                instalar.place_cpp_runtime(env)
            self.assertTrue((lib/'msvcp140.dll').is_file())

    def test_runtime_is_pinned_for_both_torch_builds(self):
        common=(instalar.ROOT/'requirements-neural-common.txt').read_text(encoding='utf-8')
        self.assertIn('msvc-runtime==',common)
        for name in ('requirements-neural.txt','requirements-neural-cpu.txt'):
            self.assertIn('-r requirements-neural-common.txt',(instalar.ROOT/name).read_text(encoding='utf-8'))

class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
        self.proc=root/'procesamiento';self.rt=root/'runtime'
        self.proc.mkdir();self.rt.mkdir()
        self.patches=[patch.object(lanzador,'PROC',self.proc),patch.object(lanzador,'RT',self.rt),patch.object(lanzador,'say')]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in self.patches:p.stop()
        self.tmp.cleanup()
    def prefs(self):
        path=self.rt/'preferencias.json'
        return json.loads(path.read_text()) if path.is_file() else {}
    def neural_env(self):
        py=lanzador.venv_python(self.proc/'.venv-neural');py.parent.mkdir(parents=True);py.touch()
        (self.proc/'modelos').mkdir();(self.proc/'modelos/manifest.json').touch()

    def test_failed_install_keeps_app_running_and_stops_asking(self):
        failure=subprocess.CalledProcessError(2,'instalar')
        with patch.object(lanzador,'has_nvidia_gpu',return_value=False),patch('builtins.input',return_value='s'),\
             patch('subprocess.run',side_effect=failure) as run:
            lanzador.maybe_install_neural(False)
        self.assertEqual(run.call_count,1)
        self.assertEqual(self.prefs(),{'instalar_ia':'no'})

    def test_forced_install_failure_does_not_raise(self):
        with patch('subprocess.run',side_effect=subprocess.CalledProcessError(1,'instalar')):
            lanzador.maybe_install_neural(True,'cpu')

    def test_answer_no_is_remembered_without_installing(self):
        with patch.object(lanzador,'has_nvidia_gpu',return_value=False),patch('builtins.input',return_value=''),\
             patch('subprocess.run') as run:
            lanzador.maybe_install_neural(False)
            lanzador.maybe_install_neural(False)
        run.assert_not_called()
        self.assertEqual(self.prefs(),{'instalar_ia':'no'})

    def test_downloads_trust_bundled_certificates(self):
        import certifi,os,ssl
        with patch.dict('os.environ'):
            os.environ.pop('SSL_CERT_FILE',None)
            lanzador.trust_bundled_certificates()
            self.assertEqual(os.environ['SSL_CERT_FILE'],certifi.where())
            self.assertEqual(ssl.get_default_verify_paths().cafile,certifi.where())
        with patch.dict('os.environ',{'SSL_CERT_FILE':'propio.pem'}):
            lanzador.trust_bundled_certificates()
            self.assertEqual(os.environ['SSL_CERT_FILE'],'propio.pem')  # a corporate bundle is respected

    def test_half_installed_environment_is_ignored(self):
        self.neural_env()
        self.assertIsNotNone(lanzador.neural_python())
        (self.proc/'.venv-neural/instalacion-en-curso').touch()
        self.assertIsNone(lanzador.neural_python())

if __name__=='__main__':unittest.main(verbosity=2)
