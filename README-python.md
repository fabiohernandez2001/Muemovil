# Muemovil: colocación de muebles con sistema multiagente

El proyecto ofrece una interfaz web para enviar una imagen de una habitación y proponer una posición libre para un mueble. También conserva el colocador de cámara de escritorio.

## Roles y jerarquía

**Cerebro** es el único orquestador y está por encima de los agentes especialistas. Recibe un plan de tareas atómicas, resuelve las dependencias, pasa a cada agente solo las entradas que necesita, y acepta sus resultados. Un candado serializa los planes para que nunca se ejecuten tareas a la vez.

- **DESIGNER:** solo puede leer la plantilla HTML. Define la interfaz del formulario y su sistema visual.
- **BACKEND:** solo puede validar entradas, detectar obstáculos, buscar una ubicación y generar la imagen anotada.
- **QA:** comprueba la plantilla y valida cada respuesta de la API. La suite de integración también verifica que la aplicación completa funciona.
- **LOGGER:** registra asignaciones, inicio y fin de tareas, comunicaciones mediadas por Cerebro y errores. No escribe imágenes ni archivos subidos.

Los agentes no se comunican directamente. Cada tarea declara sus dependencias y salidas. Cerebro la inicia cuando sus entradas están disponibles, y pasa las salidas a la siguiente tarea. Si faltan agentes, entradas o dependencias, el orquestador detiene el plan y registra el error.

## Diseño visual

La portada usa una ilustración SVG de copas de árboles con grano suave y un degradado de verde bosque a blanco cálido. DESIGNER establece una jerarquía editorial con Fraunces para titulares y Atkinson Hyperlegible Next para controles y lectura; si no hay conexión, se usan fuentes del sistema. El texto principal parte de 17 px y las indicaciones de 15 px. La composición se adapta a escritorio, tablet y móvil; mantiene el selector de idioma, foco de teclado y preferencia de movimiento reducido.

## 1. Inicio

Desde PowerShell, en esta carpeta:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python web_app.py
```

Abre `http://127.0.0.1:8000/` y mantén abierta la terminal mientras uses la web. `yolo11n.pt` detecta obstáculos. SegFormer ADE20K segmenta paredes y suelo; en el primer análisis se descarga a la caché local y requiere conexión a Internet.

## 2. Entrada

El formulario acepta:

1. Una imagen de escenario en JPG, PNG o WEBP.
2. Una imagen del mueble, o sus medidas de ancho y fondo en centímetros.
3. La distancia desde la cámara hasta el fondo visible de la escena, en centímetros.

La petición `POST /api/analizar` envía los archivos y medidas como `multipart/form-data`. El tamaño total máximo es 16 MB. Si se envía solo la imagen del mueble, se utiliza una huella nominal de 70 × 50 cm; para dimensionarlo mejor, indica su ancho y fondo.

## 3. Procedimiento

Cerebro ejecuta en serie este plan:

1. **BACKEND — validar:** decodifica imágenes y revisa medidas.
2. **BACKEND — detectar obstáculos:** obtiene sus cajas y coordenadas en píxeles.
3. **BACKEND — segmentar paredes y suelo:** localiza los límites para excluir la pared y exigir apoyo suficiente sobre el suelo.
4. **BACKEND — proponer:** busca una ubicación en suelo visible que no invada paredes ni se solape con obstáculos y tenga holgura respecto a los bordes.
5. **BACKEND — anotar:** dibuja paredes, obstáculos y el mueble propuesto sobre una copia de la imagen original.
6. **QA — validar:** comprueba la respuesta, las coordenadas, el porcentaje de pared bajo el mueble y que los objetos originales permanezcan inmóviles.

La distancia se estima linealmente a partir de la posición vertical de los objetos y el límite indicado. La proyección usa un campo de visión supuesto; sin calibración intrínseca de la cámara, el resultado de profundidad y la ubicación son aproximados. La segmentación de pared y suelo puede fallar si la escena es oscura, está tapada o no muestra suelo suficiente; en ese caso, el sistema no propone una ubicación. La API no mueve ni reescribe los objetos existentes.

## 4. Salida y terminación

La API devuelve el estado de colocación, las coordenadas de cada obstáculo, la distancia estimada del mueble, una imagen anotada en base64 y el resultado QA. Los eventos y errores quedan en `agent_activity.log`; las imágenes subidas no se guardan en disco. Cierra la terminal para detener el servidor web.

## Pruebas QA

Ejecuta la suite de integración con un detector simulado:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Las pruebas cubren el formulario Designer, la API Backend, las comprobaciones de QA, los registros de Logger, la resolución de dependencias y la ejecución sin solapamientos.

## Aplicación de escritorio

Para abrir el colocador de cámara anterior en vez de la web:

```powershell
python colocador.py --suelo-ancho 300 --suelo-fondo 250
```

Haz clic en las cuatro esquinas del suelo (cerca izquierda, cerca derecha, fondo derecha y fondo izquierda) y luego arrastra el sillón para cambiarlo de posición. Pulsa `R` para calibrar otra vez y `Q` o `Esc` para salir.
