"""Compatibilidad Windows: operaciones PyTorch para atencion deformable, sin nvcc.
Conserva el algoritmo de referencia incluido por GroundingDINO, ejecutado en GPU.
"""
from pathlib import Path
import json
from instalar import REPOS,vendored_commit,when_unlocked
root=Path(__file__).resolve().parent
p=root/'vendor/GroundingDINO/groundingdino/models/GroundingDINO/ms_deform_attn.py'
s=p.read_text(encoding='utf-8')
old='if torch.cuda.is_available() and value.is_cuda:'
new='if torch.cuda.is_available() and value.is_cuda and "_C" in globals():'
if old in s:
    when_unlocked(lambda:p.write_text(s.replace(old,new),encoding='utf-8'))
elif new not in s:
    raise RuntimeError('Version de GroundingDINO no compatible con el parche esperado')
s=p.read_text(encoding='utf-8').replace('Failed to load custom C++ ops. Running on CPU mode Only!','Custom C++ ops unavailable; using PyTorch attention on the selected device.')
when_unlocked(lambda:p.write_text(s,encoding='utf-8'))
manifest={name:vendored_commit(root/'vendor'/name) for name in REPOS}
manifest['patch']='GroundingDINO: usar implementacion PyTorch cuando no exista extension _C; SAM2 sin extension opcional.'
(root/'vendor/manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(manifest,indent=2))
