"""Conteo experimental de colonias mediante OpenCV, sin anotaciones ni redes neuronales.

Coordenadas de salida en pixeles de la imagen original. Los resultados requieren revision.
"""
from __future__ import annotations
import argparse
from dataclasses import asdict, dataclass
import json
import math
from pathlib import Path
import time

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.morphology import h_maxima
from skimage.segmentation import watershed

VERSION = '0.2.0'

@dataclass(frozen=True)
class Config:
    max_side: int = 1400
    sensitivity: float = 1.0
    min_area: float = 25.0  # pixels at analysis resolution
    max_area_fraction: float = 0.035
    border_margin: float = 0.005
    polarity: str = 'auto'  # dark: dark colonies on light agar; light: reverse
    split_touching: bool = True
    split_prominence: float = 0.08


def read_image(path: str | Path) -> np.ndarray:
    # Keep stored pixel orientation, matching AGAR coordinates. No automatic EXIF rotation.
    with Image.open(path) as im:
        if im.width * im.height > 60_000_000:
            raise ValueError('Imagen demasiado grande (limite: 60 megapixeles).')
        rgb = np.asarray(im.convert('RGB'))
    if min(rgb.shape[:2]) < 64:
        raise ValueError('La imagen debe medir al menos 64 x 64 pixeles.')
    return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)


def save_image(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, encoded = cv2.imencode(path.suffix, array)
    if not ok:
        raise ValueError(f'No se pudo codificar {path}')
    encoded.tofile(str(path))


def locate_plate(bgr: np.ndarray):
    h, w = bgr.shape[:2]
    scale = min(1.0, 700 / max(h, w))
    small = cv2.resize(bgr, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 1.2)
    sh, sw = gray.shape
    # Perspective and cropped edges make a fitted ellipse more faithful than a circle.
    edges = cv2.Canny(gray,30,90)
    contours,_ = cv2.findContours(edges,cv2.RETR_LIST,cv2.CHAIN_APPROX_NONE)
    ellipses=[]
    for contour in contours:
        if len(contour)<100:
            continue
        (ex,ey),(aw,ah),angle=cv2.fitEllipse(contour)
        if min(aw,ah)<min(sh,sw)*.52 or max(aw,ah)>min(sh,sw)*1.18 or min(aw,ah)/max(aw,ah)<.70:
            continue
        center_distance=math.hypot((ex-sw/2)/sw,(ey-sh/2)/sh)
        if center_distance>.25:
            continue
        points=contour[:,0,:].astype(np.float32)-[ex,ey]
        theta=math.radians(angle)
        u=(points[:,0]*math.cos(theta)+points[:,1]*math.sin(theta))/(aw/2)
        v=(-points[:,0]*math.sin(theta)+points[:,1]*math.cos(theta))/(ah/2)
        residual=float(np.median(np.abs(np.sqrt(u*u+v*v)-1)))
        bins=np.unique(np.int32((np.arctan2(v,u)+math.pi)*36/(2*math.pi)))
        area_fraction=math.pi*aw*ah/4/(sw*sh)
        if residual<.018 and len(bins)>=25 and .25<area_fraction<.90:
            ellipses.append((area_fraction-center_distance*.12,ex,ey,aw/2,ah/2,angle))
    if ellipses:
        _,ex,ey,ra,rb,angle=max(ellipses)
        return (ex/scale,ey/scale,ra/scale,rb/scale,angle),'ellipse'
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, dp=1.2, minDist=min(sh,sw)*0.3,
                               param1=65, param2=35, minRadius=int(min(sh,sw)*0.28),
                               maxRadius=int(min(sh,sw)*0.52))
    choices = []
    if circles is not None:
        for x,y,r in circles[0]:
            center_distance = math.hypot((float(x)-sw/2)/sw, (float(y)-sh/2)/sh)
            if center_distance < 0.25 and x-r > -sw*.08 and x+r < sw*1.08 and y-r > -sh*.08 and y+r < sh*1.08:
                choices.append((float(r)/min(sh,sw) - center_distance*.8, float(x),float(y),float(r)))
    if choices:
        _,x,y,r = max(choices)
        return (x/scale,y/scale,r/scale,r/scale,0.), 'hough'
    # A visible fallback is never treated as a reliable plate detection.
    return (w/2,h/2,min(w,h)*.43,min(w,h)*.43,0.), 'fallback'


def correct_rim_background(smooth, background, cx, cy, rx, ry, angle, radial):
    """Estimate vessel rings along the angular direction, retaining local colony contrast.

    A circular/elliptical rim repeats over angle; a colony is localized. No reference data.
    """
    h,w=smooth.shape[:2]
    nr=max(60,int(max(rx,ry)*.43))
    na=720
    rho=np.linspace(.65,1.08,nr,dtype=np.float32)[:,None]
    phi=np.linspace(0,2*math.pi,na,endpoint=False,dtype=np.float32)[None,:]
    a=math.radians(angle)
    xp=cx+rx*rho*np.cos(phi)*math.cos(a)-ry*rho*np.sin(phi)*math.sin(a)
    yp=cy+rx*rho*np.cos(phi)*math.sin(a)+ry*rho*np.sin(phi)*math.cos(a)
    polar=cv2.remap(smooth,xp.astype(np.float32),yp.astype(np.float32),cv2.INTER_LINEAR,borderMode=cv2.BORDER_REFLECT_101)
    angular=ndi.median_filter(polar,size=(1,61,1),mode='wrap')
    angular=np.concatenate([angular,angular[:,:1]],axis=1)
    yy,xx=np.mgrid[:h,:w].astype(np.float32)
    u=((xx-cx)*math.cos(a)+(yy-cy)*math.sin(a))/rx
    v=(-(xx-cx)*math.sin(a)+(yy-cy)*math.cos(a))/ry
    mp=(np.mod(np.arctan2(v,u),2*math.pi)*na/(2*math.pi)).astype(np.float32)
    mr=np.clip((np.sqrt(radial)-.65)/.43*(nr-1),0,nr-1).astype(np.float32)
    ring_bg=cv2.remap(angular,mp,mr,cv2.INTER_LINEAR)
    weight=np.clip((np.sqrt(radial)-.70)/.12,0,1).astype(np.float32)[:,:,None]
    return background*(1-weight)+ring_bg*weight


def fill_regions(mask: np.ndarray) -> np.ndarray:
    # Fill holes only inside colony-sized components; a closed dish rim must not fill the plate.
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    filled = mask.copy()
    if hierarchy is not None:
        for i, contour in enumerate(contours):
            if hierarchy[0,i,3] == -1 and cv2.contourArea(contour) < mask.size*.035:
                cv2.drawContours(filled,[contour],-1,255,cv2.FILLED)
    return filled


def split_component(component: np.ndarray, split: bool = True, prominence: float = .08):
    """Split shape lobes, suppressing shallow distance peaks within one colony.

    No intensity peaks or labels are used as seeds. Watershed creates disjoint regions.
    """
    mask = component > 0
    distance = ndi.distance_transform_edt(mask).astype(np.float32)
    surface = ndi.gaussian_filter(distance, 1.3)
    surface[~mask] = 0
    maximum = float(surface.max())
    y0,x0 = np.unravel_index(np.argmax(surface),surface.shape)
    if maximum <= 0:
        return [],np.zeros(component.shape,np.int32)
    contours,_=cv2.findContours(component,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    contour=max(contours,key=cv2.contourArea)
    area=float(mask.sum())
    solidity=area/max(cv2.contourArea(cv2.convexHull(contour)),1)
    compactness=area/(math.pi*float(distance.max())**2)
    # Almost round solid colonies are single instances even if the outline is slightly noisy.
    (_, _),(rect_w,rect_h),_=cv2.minAreaRect(contour)
    aspect=max(rect_w,rect_h)/max(min(rect_w,rect_h),1)
    one_colony = (solidity>.94 and compactness<1.25) or (solidity>.80 and compactness<1.65 and aspect<1.22)
    if not split or maximum<3.5 or one_colony:
        return [(int(x0),int(y0),float(distance[y0,x0]))],mask.astype(np.int32)
    height=max(.9,maximum*prominence)
    maxima=h_maxima(surface,height)&mask
    markers,n=ndi.label(maxima)
    if n==0:
        markers[y0,x0]=1
    basins=watershed(-surface,markers,mask=mask,watershed_line=False).astype(np.int32)
    peaks=[]
    for label in range(1,int(basins.max())+1):
        ys,xs=np.where(basins==label)
        best=int(np.argmax(distance[ys,xs]))
        y,x=int(ys[best]),int(xs[best])
        peaks.append((x,y,float(distance[y,x])))
    return peaks,basins


def component_peaks(component: np.ndarray, split: bool):
    return split_component(component,split)[0]


def count_colonies(bgr: np.ndarray, config: Config = Config(), roi: tuple[float,float,float] | None = None):
    if not .2 <= config.sensitivity <= 3:
        raise ValueError('Sensibilidad fuera de rango: usar entre 0.2 y 3.')
    if config.max_side < 256 or not math.isfinite(config.min_area) or config.min_area <= 0 or not 0 <= config.border_margin < .3 or not 0 < config.max_area_fraction < 1:
        raise ValueError('Configuracion de tamano/area/margen invalida.')
    if config.polarity not in {'auto','dark','light'}:
        raise ValueError('Polaridad no reconocida.')
    if not .01 <= config.split_prominence <= .5:
        raise ValueError('Prominencia fuera de rango: usar de 0.01 a 0.5.')
    start = time.perf_counter()
    h0,w0 = bgr.shape[:2]
    scale = min(1.0,config.max_side/max(h0,w0))
    im = cv2.resize(bgr,None,fx=scale,fy=scale,interpolation=cv2.INTER_AREA)
    h,w = im.shape[:2]
    warnings = ['Conteo experimental: revisar visualmente las detecciones. No identifica especies.']
    if roi is None:
        (cx,cy,outer_rx,outer_ry,angle),roi_method = locate_plate(im)
    else:
        x,y,r = roi
        if not all(math.isfinite(v) for v in (x,y,r)) or r<=0 or not (0<=x<w0 and 0<=y<h0):
            raise ValueError('ROI invalida: centro dentro de la imagen y radio positivo.')
        cx,cy,outer_rx,outer_ry,angle = x*scale,y*scale,r*scale,r*scale,0.
        roi_method = 'manual'
    outer_radius = math.sqrt(outer_rx*outer_ry)
    radius = outer_radius*(1-config.border_margin)
    rx,ry=outer_rx*(1-config.border_margin),outer_ry*(1-config.border_margin)
    yy,xx = np.ogrid[:h,:w]
    theta=math.radians(angle)
    u=((xx-cx)*math.cos(theta)+(yy-cy)*math.sin(theta))/rx
    v=(-(xx-cx)*math.sin(theta)+(yy-cy)*math.cos(theta))/ry
    radial=u*u+v*v
    valid = radial <= 1
    roi_mask = (valid.astype(np.uint8)*255)
    if valid.sum() < 100:
        raise ValueError('Region de analisis demasiado pequena.')
    if roi_method == 'fallback':
        warnings.append('No se encontro una placa circular fiable: se uso una region central. Indicar --roi.')
    warnings.append('Verificar el limite de la placa y los candidatos de borde marcados para revision.')
    lab = cv2.cvtColor(im,cv2.COLOR_BGR2LAB).astype(np.float32)
    smooth = cv2.GaussianBlur(lab,(3,3),.7)
    # A coarse median estimates uneven agar illumination without halos around printed ink.
    coarse = cv2.resize(lab.astype(np.uint8),None,fx=.25,fy=.25,interpolation=cv2.INTER_AREA)
    coarse = cv2.medianBlur(coarse,41)
    background = cv2.resize(coarse.astype(np.float32),(w,h),interpolation=cv2.INTER_LINEAR)
    background = cv2.GaussianBlur(background,(0,0),3)
    background=correct_rim_background(smooth,background,cx,cy,rx,ry,angle,radial)
    delta = smooth-background
    luminance = float(np.median(smooth[:,:,0][valid]))
    polarity = config.polarity if config.polarity != 'auto' else ('dark' if luminance>=125 else 'light')
    if polarity == 'dark':
        # Yellow/brown colonies differ from the usually neutral/blue printed ink.
        yellow = np.maximum(delta[:,:,2],0)
        darkness = np.maximum(-delta[:,:,0],0)
        score = yellow*2.0 + darkness*.45
        ink = ((delta[:,:,2] < .5) & (delta[:,:,0] < -8)).astype(np.uint8)
        ink = cv2.dilate(ink,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(5,5)))
        score[ink>0]=0
    else:
        score = np.maximum(delta[:,:,0],0) + np.maximum(delta[:,:,2],0)*.5
    score = cv2.GaussianBlur(score,(3,3),.5)
    values = score[valid]
    med = float(np.median(values))
    mad = float(np.median(np.abs(values-med)))
    threshold = max(6.0,med+4.5*1.4826*mad)/config.sensitivity
    binary = ((score>threshold)&valid).astype(np.uint8)*255
    binary = cv2.morphologyEx(binary,cv2.MORPH_OPEN,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    binary = cv2.morphologyEx(binary,cv2.MORPH_CLOSE,cv2.getStructuringElement(cv2.MORPH_ELLIPSE,(3,3)))
    binary = fill_regions(binary)
    binary[~valid]=0
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary,8)
    # Estimate a conservative size floor from clearly compact objects in this photo.
    # This rejects tiny ink/glare fragments, without assuming a fixed colony size.
    anchor_radii=[]
    for lab_id in range(1,n):
        ax,ay,aw,ah,aa=map(int,stats[lab_id])
        if not 300 <= aa <= valid.sum()*config.max_area_fraction:
            continue
        am=(labels[ay:ay+ah,ax:ax+aw]==lab_id).astype(np.uint8)
        ac,_=cv2.findContours(am,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        ap=cv2.arcLength(max(ac,key=cv2.contourArea),True)
        if 4*math.pi*aa/max(ap*ap,1)>.65:
            ar=float(ndi.distance_transform_edt(np.pad(am,1)).max())
            if ar>8: anchor_radii.append(ar)
    radius_floor=max(2.4,.25*float(np.median(anchor_radii))) if len(anchor_radii)>=2 else 2.4
    kept_mask = np.zeros_like(binary)
    instances=np.zeros_like(binary,dtype=np.uint16)
    detections=[]
    rejected=0
    for label in range(1,n):
        x,y,bw,bh,area = map(int,stats[label])
        if area<config.min_area or area>valid.sum()*config.max_area_fraction or min(bw,bh)<3:
            rejected+=1
            continue
        local = (labels[y:y+bh,x:x+bw]==label).astype(np.uint8)*255
        contours,_ = cv2.findContours(local,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        contour=max(contours,key=cv2.contourArea)
        perimeter=cv2.arcLength(contour,True)
        circularity=4*math.pi*area/max(perimeter**2,1)
        hull=cv2.contourArea(cv2.convexHull(contour))
        solidity=area/max(hull,1)
        if solidity<.30:
            rejected+=1
            continue
        # Padding ensures distance transform sees background for components touching a crop edge.
        padded=cv2.copyMakeBorder(local,2,2,2,2,cv2.BORDER_CONSTANT,value=0)
        peaks,basins=split_component(padded,config.split_touching,config.split_prominence)
        cropped=basins[2:-2,2:-2]
        for segment,(px,py,pr) in enumerate(peaks,1):
            if pr<2.4:
                continue
            dx,dy=x+px-2,y+py-2
            if not (0<=dx<w and 0<=dy<h and valid[dy,dx]):
                continue
            region=cropped==segment
            part_area=int(region.sum())
            if part_area<config.min_area:
                continue
            # Thin arcs and ink strokes have much more area than their inscribed disk.
            fill_ratio=part_area/(math.pi*pr*pr)
            part_contours,_=cv2.findContours(region.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
            pc=max(part_contours,key=cv2.contourArea)
            pp=cv2.arcLength(pc,True)
            roundness=4*math.pi*part_area/max(pp*pp,1)
            near_edge=bool(radial[dy,dx]>.88**2)
            local_floor=max(5.,radius_floor) if near_edge else min(5.,radius_floor)
            if pr<local_floor:
                rejected+=1
                continue
            if fill_ratio>3.2 or roundness<.33 or (near_edge and roundness<.46):
                rejected+=1
                continue
            region_y,region_x=np.where(region)
            bx,by=int(region_x.min())+x,int(region_y.min())+y
            rw,rh=int(region_x.max()-region_x.min()+1),int(region_y.max()-region_y.min()+1)
            ident=len(detections)+1
            instances[y:y+bh,x:x+bw][region]=ident
            kept_mask[y:y+bh,x:x+bw][region]=255
            detections.append({'id':ident,'x':round(dx/scale,2),'y':round(dy/scale,2),
                'radius':round(pr/scale,2),'bbox':[round(v/scale,2) for v in (bx,by,rw,rh)],
                'component_bbox':[round(v/scale,2) for v in (x,y,bw,bh)],
                'component_area':round(area/(scale*scale),2),'instance_area':round(part_area/(scale*scale),2),
                'shared_component':len(peaks)>1,'near_edge':near_edge})
    foreground_fraction=float(np.count_nonzero(kept_mask)/valid.sum())
    if foreground_fraction>.25:
        warnings.append('Mucha superficie segmentada: posible crecimiento denso o iluminacion inadecuada.')
    if not detections:
        warnings.append('No se detectaron candidatos. Esto no demuestra ausencia de colonias.')
    result={'version':VERSION,'method':'opencv_lab_hmax_watershed','count':len(detections),
        'requires_review':True,'image_size':{'width':w0,'height':h0},'analysis_scale':scale,
        'roi':{'x':cx/scale,'y':cy/scale,'outer_radius':outer_radius/scale,'analysis_radius':radius/scale,'analysis_axes':[rx/scale,ry/scale],'angle_degrees':angle,'method':roi_method},
        'polarity_used':polarity,'threshold':threshold,'foreground_fraction':foreground_fraction,
        'minimum_radius_analysis_pixels':radius_floor,'rejected_components':rejected,'config':asdict(config),'detections':detections,
        'warnings':warnings,'processing_seconds':round(time.perf_counter()-start,4)}
    annotated=im.copy()
    cv2.ellipse(annotated,((cx,cy),(2*rx,2*ry),angle),(255,180,0),2)
    for det in detections:
        point=(round(det['x']*scale),round(det['y']*scale))
        contours,_=cv2.findContours((instances==det['id']).astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        color=(0,190,255) if det['near_edge'] else (0,230,80)
        cv2.drawContours(annotated,contours,-1,color,2)
        cv2.circle(annotated,point,2,(0,0,255),-1)
        cv2.putText(annotated,str(det['id']),(point[0]+4,point[1]-4),cv2.FONT_HERSHEY_SIMPLEX,.35,(0,70,255),1,cv2.LINE_AA)
    cv2.rectangle(annotated,(0,0),(w,45),(30,30,30),-1)
    cv2.putText(annotated,f'Candidatos: {len(detections)} | Revisar resultado',(12,30),cv2.FONT_HERSHEY_SIMPLEX,.65,(255,255,255),2,cv2.LINE_AA)
    rng=np.random.default_rng(42)
    palette=rng.integers(55,255,size=(len(detections)+1,3),dtype=np.uint8);palette[0]=0
    debug={'annotated':annotated,'roi':roi_mask,'mask':kept_mask,'contrast':np.uint8(np.clip(score*6,0,255)),
           'threshold':binary,'instances':instances,'segments':palette[instances]}
    return result,debug


def write_result(result: dict, debug: dict, output: Path, stem: str):
    output.mkdir(parents=True,exist_ok=True)
    (output/f'{stem}_resultado.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    save_image(output/f'{stem}_conteo.jpg',debug['annotated'])
    for key in ('mask','contrast','roi','threshold','instances','segments'):
        save_image(output/f'{stem}_{key}.png',debug[key])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image',type=Path)
    parser.add_argument('--output',type=Path,default=Path(__file__).resolve().parent/'resultados'/'individual')
    parser.add_argument('--sensitivity',type=float,default=1.0,help='0.2 a 3; Mayor valor facilita la segmentacion; el conteo no es monotono.')
    parser.add_argument('--min-area',type=float,default=25)
    parser.add_argument('--max-side',type=int,default=1400)
    parser.add_argument('--margin',type=float,default=.005,help='Fraccion del radio que se excluye en el borde.')
    parser.add_argument('--polarity',choices=['auto','dark','light'],default='auto')
    parser.add_argument('--roi',type=float,nargs=3,metavar=('X','Y','RADIO'),help='Circulo en pixeles originales.')
    parser.add_argument('--no-split',action='store_true')
    parser.add_argument('--split-prominence',type=float,default=.08,help='0.01 a 0.5: mayor evita fragmentaciones pero puede fusionar colonias.')
    args=parser.parse_args()
    cfg=Config(max_side=args.max_side,sensitivity=args.sensitivity,min_area=args.min_area,border_margin=args.margin,polarity=args.polarity,split_touching=not args.no_split,split_prominence=args.split_prominence)
    try:
        result,debug=count_colonies(read_image(args.image),cfg,tuple(args.roi) if args.roi else None)
        result['input_image']=str(args.image.resolve())
        write_result(result,debug,args.output,args.image.stem)
    except (ValueError,OSError) as exc:
        parser.exit(2,f'Error: {exc}\n')
    print(json.dumps({'count':result['count'],'seconds':result['processing_seconds'],'output':str(args.output.resolve()),'warnings':result['warnings']},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
