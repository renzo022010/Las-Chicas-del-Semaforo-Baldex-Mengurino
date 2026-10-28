# Resultado del motor híbrido v0.3

- 38 imágenes AGAR conocidas, con posible solapamiento con el entrenamiento del modelo. No es una validación independiente.
- Error absoluto medio del clásico: 9.45 colonias/foto. Híbrido: 1.97.
- Mejoran 31, empeoran 2, mantienen error 5.
- Coincidencias uno a uno centro/caja: precisión 0.9818, recuperación 0.9574. No son mAP/IoU ni precisión validada en fotos propias.
- Tiempo medio: 1.51 s/foto; carga del modelo en esta ejecución: 13.25 s.
- GPU: NVIDIA GeForce RTX 5060; máximo de memoria asignada por PyTorch: 2538.9 MB. No incluye toda la memoria del proceso/contexto CUDA o del escritorio.
- Placa 5271: clásico 41, híbrido 42, referencia 43; 42 coincidencias, 0 extras y 1 omisiones.

No se entrenó ni ajustó una red con estas fotos durante esta integración. Los pesos de los autores sí se ajustaron con AGAR. El modelo puede seguir omitiendo colonias juntas, pequeñas o periféricas; revisar cada resultado. Se conserva el motor clásico y la predicción automática original al guardar correcciones humanas.

SHA256 del motor: 4f67908026070b48889bc093631b63ffb7ab658d6884910662d9303729c2a3d0
