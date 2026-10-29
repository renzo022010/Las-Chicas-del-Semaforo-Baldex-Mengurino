"""Archivos de cada analisis. La prediccion automatica no se modifica; la revision humana se guarda aparte."""
from pathlib import Path
import json,uuid
from app.config import RESULT_FILES

class ResultNotFound(Exception):pass

class ResultStore:
    def __init__(self,root):self.root=Path(root)

    def new_folder(self):
        ident=uuid.uuid4().hex
        return ident,self.root/ident

    def path(self,analysis_id,name):
        if len(analysis_id)!=32 or any(c not in '0123456789abcdef' for c in analysis_id) or name not in RESULT_FILES:
            raise ResultNotFound
        path=self.root/analysis_id/name
        if not path.is_file():raise ResultNotFound
        return path

    def save_review(self,analysis_id,review):
        original=json.loads(self.path(analysis_id,'foto_resultado.json').read_text(encoding='utf-8'))
        w=original['image_size']['width'];h=original['image_size']['height']
        if any(p.x>=w or p.y>=h for p in review.centers):raise ValueError('Centro fuera de imagen')
        record={'automatic_count':original['count'],'reviewed_count':len(review.centers),**review.model_dump(),
                'review_type':'human_submitted_centers_not_model_prediction'}
        (self.root/analysis_id/'revision.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
        return record
