"""Pruebas funcionales con imagenes sinteticas; no son evidencia de precision biologica."""
import tempfile,unittest
from pathlib import Path
import cv2
import numpy as np
from contador import Config,count_colonies,read_image,write_result,split_component

class ProcessingTests(unittest.TestCase):
    def test_separate_light_colonies_and_original_coordinates(self):
        im=np.full((800,1000,3),(45,55,55),dtype=np.uint8)
        centers=[(300,300),(500,300),(700,300),(400,500),(650,500)]
        for point in centers:cv2.circle(im,point,16,(170,195,195),-1)
        result,_=count_colonies(im,Config(max_side=700,polarity='light'),roi=(500,400,350))
        self.assertEqual(result['count'],5)
        for x,y in centers:
            self.assertLess(min(np.hypot(d['x']-x,d['y']-y) for d in result['detections']),4)

    def test_separate_dark_colonies(self):
        im=np.full((640,640,3),(170,200,200),dtype=np.uint8)
        centers=[(220,210),(420,210),(220,430),(420,430)]
        for point in centers:cv2.circle(im,point,14,(40,90,110),-1)
        result,_=count_colonies(im,Config(polarity='dark'),roi=(320,320,260))
        self.assertEqual(result['count'],4)

    def test_empty_image_requires_review(self):
        im=np.full((640,640,3),180,dtype=np.uint8)
        result,_=count_colonies(im,roi=(320,320,250))
        self.assertEqual(result['count'],0)
        self.assertTrue(result['requires_review'])
        self.assertTrue(any('ausencia' in warning for warning in result['warnings']))

    def test_touching_colonies(self):
        im=np.full((640,640,3),45,dtype=np.uint8)
        for point in [(290,320),(330,320)]:cv2.circle(im,point,25,(180,190,190),-1)
        result,_=count_colonies(im,Config(polarity='light'),roi=(320,320,260))
        self.assertEqual(result['count'],2)

    def test_three_touching_colonies_have_disjoint_instances(self):
        im=np.full((640,640,3),45,dtype=np.uint8)
        for point in [(280,320),(320,320),(360,320)]:
            cv2.circle(im,point,25,(180,190,190),-1)
        result,debug=count_colonies(im,Config(polarity='light'),roi=(320,320,260))
        self.assertEqual(result['count'],3)
        self.assertEqual(set(np.unique(debug['instances'])),{0,1,2,3})

    def test_irregular_single_colony_is_not_fragmented(self):
        mask=np.zeros((180,180),np.uint8)
        angles=np.linspace(0,2*np.pi,180,endpoint=False)
        radius=43+2*np.sin(angles*9)+np.sin(angles*17)
        points=np.column_stack((90+radius*np.cos(angles),90+radius*np.sin(angles))).astype(np.int32)
        cv2.fillPoly(mask,[points],255)
        peaks,basins=split_component(mask)
        self.assertEqual(len(peaks),1)
        self.assertEqual(int(basins.max()),1)

    def test_colony_near_boundary_is_included(self):
        im=np.full((640,640,3),(170,200,200),np.uint8)
        cv2.circle(im,(562,320),10,(40,90,110),-1)
        result,_=count_colonies(im,Config(polarity='dark'),roi=(320,320,260))
        self.assertEqual(result['count'],1)
        self.assertTrue(result['detections'][0]['near_edge'])

    def test_export_and_unicode_path(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'placa de prueba á.png'
            Image.new('RGB',(128,128),(180,180,180)).save(path)
            im=read_image(path)
            result,debug=count_colonies(im,roi=(64,64,50))
            output=Path(tmp)/'salida'
            write_result(result,debug,output,'placa')
            self.assertTrue((output/'placa_resultado.json').exists())
            with Image.open(output/'placa_conteo.jpg') as exported:
                self.assertEqual(exported.size,(128,128))

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            count_colonies(np.zeros((200,200,3),dtype=np.uint8),Config(sensitivity=0))

if __name__=='__main__':unittest.main(verbosity=2)
