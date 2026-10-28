"""Compatibilidad Windows: operaciones PyTorch para atencion deformable, sin nvcc.
Conserva el algoritmo de referencia incluido por GroundingDINO, ejecutado en GPU.
"""
from pathlib import Path
import subprocess,json
root=Path(__file__).resolve().parent
p=root/'vendor/GroundingDINO/groundingdino/models/GroundingDINO/ms_deform_attn.py'
s=p.read_text(encoding='utf-8')
old='if torch.cuda.is_available() and value.is_cuda:'
new='if torch.cuda.is_available() and value.is_cuda and "_C" in globals():'
if old in s:
    p.write_text(s.replace(old,new),encoding='utf-8')
elif new not in s:
    raise RuntimeError('Version de GroundingDINO no compatible con el parche esperado')
s=p.read_text(encoding='utf-8').replace('Failed to load custom C++ ops. Running on CPU mode Only!','Custom C++ ops unavailable; using PyTorch attention on the selected device.')
p.write_text(s,encoding='utf-8')
manifest={}
for name in ['GroundingDINO','sam2','ColonyGroundedSAM2']:
    manifest[name]=subprocess.check_output(['git','-C',str(root/'vendor'/name),'rev-parse','HEAD'],text=True).strip()
manifest['patch']='GroundingDINO: usar implementacion PyTorch cuando no exista extension _C; SAM2 sin extension opcional.'
(root/'vendor/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
