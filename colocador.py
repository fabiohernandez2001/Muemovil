"""Coloca un objeto virtual en la imagen en directo de una webcam.

Ejemplo:
    python colocador.py --suelo-ancho 300 --suelo-fondo 250
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from multiagentes import (
    AgenteColisiones,
    AgenteObstaculos,
    AgenteProfundidad,
    AgenteSuelo,
    Cerebro,
    InformeCerebro,
)


VENTANA = "Colocador de objetos"
VERDE_SUELO = (65, 180, 85)
NARANJA_OBSTACULO = (0, 145, 255)
VERDE_LIBRE = (65, 190, 80)
ROJO_COLISION = (30, 40, 230)
ANCHO_OBJETO_CM = 70
ALTO_OBJETO_CM = 70
FONDO_OBJETO_CM = 50
ARCHIVO_IMAGEN_OBJETO = Path(__file__).with_name("sillon_transparente.png")


@dataclass
class DeteccionObstaculo:
    centro_cm: np.ndarray
    radio_cm: float
    etiqueta: str


@dataclass
class Aplicacion:
    opciones: argparse.Namespace
    camara: cv2.VideoCapture
    puntos_suelo: list[tuple[int, int]] = field(default_factory=list)
    matriz_imagen_a_suelo: np.ndarray | None = None
    matriz_suelo_a_imagen: np.ndarray | None = None
    mascara_suelo: np.ndarray | None = None
    obstaculos: list[DeteccionObstaculo] = field(default_factory=list)
    centro_objeto_cm: np.ndarray = field(default_factory=lambda: np.zeros(2, dtype=float))
    arrastre_activo: bool = False
    posicion_raton: tuple[int, int] | None = None
    modelo_suelo: object | None = None
    procesador_suelo: object | None = None
    id_suelo: int | None = None
    modelo_objetos: object | None = None
    torch: object | None = None
    imagen_objeto: np.ndarray | None = None
    cerebro: Cerebro | None = None


def crear_aplicacion(opciones: argparse.Namespace) -> Aplicacion:
    camara = cv2.VideoCapture(opciones.camera)
    if not camara.isOpened():
        raise RuntimeError(f"No se pudo abrir la webcam con índice {opciones.camera}.")
    centro_inicial = np.array([opciones.suelo_ancho / 2, opciones.suelo_fondo / 2], dtype=float)
    return Aplicacion(opciones=opciones, camara=camara, centro_objeto_cm=centro_inicial)


def cargar_modelos(app: Aplicacion) -> None:
    """Prepara el segmentador semántico de suelo y el detector de objetos."""
    try:
        import torch
        from transformers import AutoImageProcessor, SegformerForSemanticSegmentation
        from ultralytics import YOLO
    except ImportError as error:
        raise RuntimeError("Faltan librerías. Instálalas con: pip install -r requirements.txt") from error

    app.torch = torch
    app.procesador_suelo = AutoImageProcessor.from_pretrained(app.opciones.modelo_suelo)
    app.modelo_suelo = SegformerForSemanticSegmentation.from_pretrained(app.opciones.modelo_suelo)
    app.modelo_suelo.eval()
    nombres_clase = app.modelo_suelo.config.id2label
    clases_suelo = [int(clave) for clave, nombre in nombres_clase.items() if "floor" in str(nombre).lower()]
    if not clases_suelo:
        raise RuntimeError("El modelo de segmentación seleccionado no tiene una clase floor.")
    app.id_suelo = clases_suelo[0]
    app.modelo_objetos = YOLO(app.opciones.modelo)
    app.imagen_objeto = cv2.imread(str(ARCHIVO_IMAGEN_OBJETO), cv2.IMREAD_UNCHANGED)
    if app.imagen_objeto is None or app.imagen_objeto.shape[2] != 4:
        raise RuntimeError(f"No se pudo cargar la imagen transparente: {ARCHIVO_IMAGEN_OBJETO}")
    pixeles_visibles = cv2.findNonZero(app.imagen_objeto[:, :, 3])
    if pixeles_visibles is None:
        raise RuntimeError("La imagen del sillón no contiene píxeles visibles.")
    x, y, ancho, alto = cv2.boundingRect(pixeles_visibles)
    app.imagen_objeto = app.imagen_objeto[y:y + alto, x:x + ancho]


def segmentar_suelo(app: Aplicacion, imagen: np.ndarray) -> None:
    imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
    datos = app.procesador_suelo(images=imagen_rgb, return_tensors="pt")
    with app.torch.inference_mode():
        logits = app.modelo_suelo(**datos).logits
        logits = app.torch.nn.functional.interpolate(
            logits, size=imagen.shape[:2], mode="bilinear", align_corners=False
        )
        clases = logits.argmax(dim=1)[0].cpu().numpy()

    mascara = (clases == app.id_suelo).astype(np.uint8)
    elemento = np.ones((5, 5), dtype=np.uint8)
    mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, elemento)
    app.mascara_suelo = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, elemento)


def crear_calibracion(app: Aplicacion) -> None:
    """Calcula la transformación perspectiva usando las cuatro esquinas marcadas."""
    esquinas_imagen = np.float32(app.puntos_suelo)
    esquinas_cm = np.float32([
        [0, 0],
        [app.opciones.suelo_ancho, 0],
        [app.opciones.suelo_ancho, app.opciones.suelo_fondo],
        [0, app.opciones.suelo_fondo],
    ])
    app.matriz_imagen_a_suelo = cv2.getPerspectiveTransform(esquinas_imagen, esquinas_cm)
    app.matriz_suelo_a_imagen = cv2.getPerspectiveTransform(esquinas_cm, esquinas_imagen)


def transformar_a_suelo(app: Aplicacion, punto: tuple[float, float]) -> np.ndarray:
    puntos = np.float32([[punto]])
    resultado = cv2.perspectiveTransform(puntos, app.matriz_imagen_a_suelo)
    return resultado[0, 0].astype(float)


def transformar_a_imagen(app: Aplicacion, puntos_cm: np.ndarray) -> np.ndarray:
    puntos = np.float32(puntos_cm).reshape(1, -1, 2)
    resultado = cv2.perspectiveTransform(puntos, app.matriz_suelo_a_imagen)
    return np.rint(resultado[0]).astype(int)


def recibir_raton(evento: int, x: int, y: int, _banderas: int, app: Aplicacion) -> None:
    app.posicion_raton = (x, y)
    if app.matriz_imagen_a_suelo is None:
        if evento == cv2.EVENT_LBUTTONDOWN and len(app.puntos_suelo) < 4:
            app.puntos_suelo.append((x, y))
            if len(app.puntos_suelo) == 4:
                crear_calibracion(app)
        return

    if evento == cv2.EVENT_LBUTTONDOWN:
        app.arrastre_activo = True
        mover_objeto(app, x, y)
    elif evento == cv2.EVENT_MOUSEMOVE and app.arrastre_activo:
        mover_objeto(app, x, y)
    elif evento == cv2.EVENT_LBUTTONUP:
        app.arrastre_activo = False


def mover_objeto(app: Aplicacion, x_imagen: int, y_imagen: int) -> None:
    app.centro_objeto_cm = transformar_a_suelo(app, (x_imagen, y_imagen))
    mitad_ancho = ANCHO_OBJETO_CM / 2
    mitad_fondo = FONDO_OBJETO_CM / 2
    app.centro_objeto_cm[0] = np.clip(app.centro_objeto_cm[0], mitad_ancho, app.opciones.suelo_ancho - mitad_ancho)
    app.centro_objeto_cm[1] = np.clip(app.centro_objeto_cm[1], mitad_fondo, app.opciones.suelo_fondo - mitad_fondo)


def detectar_obstaculos(app: Aplicacion, imagen: np.ndarray) -> None:
    detecciones = app.modelo_objetos.predict(imagen, conf=app.opciones.confianza, verbose=False)[0]
    resultado: list[DeteccionObstaculo] = []
    for caja in detecciones.boxes:
        x_izq, _y_arriba, x_der, y_abajo = map(float, caja.xyxy[0].tolist())
        base_izquierda = transformar_a_suelo(app, (x_izq, y_abajo))
        base_derecha = transformar_a_suelo(app, (x_der, y_abajo))
        centro = (base_izquierda + base_derecha) / 2
        ancho_estimado = float(np.linalg.norm(base_derecha - base_izquierda))
        radio = max(ancho_estimado / 2, app.opciones.margen)
        etiqueta = detecciones.names[int(caja.cls[0])]
        resultado.append(DeteccionObstaculo(centro, radio, etiqueta))
    app.obstaculos = resultado


def calcular_colision_actual(app: Aplicacion) -> bool:
    """Devuelve si el mueble se solapa con alguno de los obstáculos detectados."""
    huella_objeto = obtener_huella_objeto(app)
    for obstaculo in app.obstaculos:
        x, y = obstaculo.centro_cm
        radio = obstaculo.radio_cm
        huella_obstaculo = np.array([
            [x - radio, y - radio], [x + radio, y - radio],
            [x + radio, y + radio], [x - radio, y + radio],
        ])
        if huellas_se_cruzan(huella_objeto, huella_obstaculo):
            return True
    return False


def crear_cerebro(app: Aplicacion) -> Cerebro:
    """Conecta cada agente especialista con las funciones existentes del colocador."""
    def analizar_obstaculos(imagen: np.ndarray) -> int:
        detectar_obstaculos(app, imagen)
        return len(app.obstaculos)

    return Cerebro(
        agente_suelo=AgenteSuelo(lambda imagen: segmentar_suelo(app, imagen)),
        agente_obstaculos=AgenteObstaculos(analizar_obstaculos),
        agente_colisiones=AgenteColisiones(lambda: calcular_colision_actual(app)),
        agente_profundidad=AgenteProfundidad(
            lambda: float(app.centro_objeto_cm[1])
        ),
    )


def obtener_huella_objeto(app: Aplicacion) -> np.ndarray:
    x, y = app.centro_objeto_cm
    mitad_ancho = ANCHO_OBJETO_CM / 2
    mitad_fondo = FONDO_OBJETO_CM / 2
    return np.array([
        [x - mitad_ancho, y - mitad_fondo], [x + mitad_ancho, y - mitad_fondo],
        [x + mitad_ancho, y + mitad_fondo], [x - mitad_ancho, y + mitad_fondo],
    ])


def huellas_se_cruzan(primera: np.ndarray, segunda: np.ndarray) -> bool:
    """Prueba si dos polígonos convexos se solapan usando sus lados como ejes."""
    for poligono in (primera, segunda):
        for indice in range(len(poligono)):
            lado = poligono[(indice + 1) % len(poligono)] - poligono[indice]
            eje = np.array([-lado[1], lado[0]])
            proyeccion_a = primera @ eje
            proyeccion_b = segunda @ eje
            if proyeccion_a.max() < proyeccion_b.min() or proyeccion_b.max() < proyeccion_a.min():
                return False
    return True


def dibujar_suelo(imagen: np.ndarray, mascara: np.ndarray | None) -> np.ndarray:
    salida = imagen.copy()
    if mascara is not None:
        capa = salida.copy()
        capa[mascara > 0] = VERDE_SUELO
        salida = cv2.addWeighted(capa, 0.35, salida, 0.65, 0)
    return salida


def dibujar_calibracion(salida: np.ndarray, app: Aplicacion) -> np.ndarray:
    for numero, punto in enumerate(app.puntos_suelo, start=1):
        cv2.circle(salida, punto, 7, (0, 220, 255), -1)
        cv2.putText(salida, str(numero), (punto[0] + 9, punto[1]), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    cv2.putText(salida, "Marca 4 esquinas: cerca izquierda, cerca derecha, fondo derecha, fondo izquierda",
                (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 2)
    cv2.putText(salida, f"Puntos marcados: {len(app.puntos_suelo)}/4", (15, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    return salida


def dibujar_imagen_objeto(salida: np.ndarray, app: Aplicacion) -> np.ndarray:
    """Pinta la imagen del sillón a escala aproximada sobre su posición en el suelo."""
    if app.imagen_objeto is None:
        return salida

    centro_x, centro_y = app.centro_objeto_cm
    extremos_ancho = transformar_a_imagen(
        app,
        np.array([
            [centro_x - ANCHO_OBJETO_CM / 2, centro_y],
            [centro_x + ANCHO_OBJETO_CM / 2, centro_y],
        ]),
    )
    ancho_pantalla = max(1, int(np.linalg.norm(extremos_ancho[1] - extremos_ancho[0])))
    alto_pantalla = max(1, round(ancho_pantalla * ALTO_OBJETO_CM / ANCHO_OBJETO_CM))
    sillón = cv2.resize(app.imagen_objeto, (ancho_pantalla, alto_pantalla), interpolation=cv2.INTER_AREA)

    punto_apoyo_cm = np.array([[centro_x, centro_y - FONDO_OBJETO_CM / 2]])
    punto_apoyo = transformar_a_imagen(app, punto_apoyo_cm)[0]
    izquierda = int(punto_apoyo[0] - ancho_pantalla / 2)
    arriba = int(punto_apoyo[1] - alto_pantalla)
    x1, y1 = max(0, izquierda), max(0, arriba)
    x2, y2 = min(salida.shape[1], izquierda + ancho_pantalla), min(salida.shape[0], arriba + alto_pantalla)
    if x1 >= x2 or y1 >= y2:
        return salida

    sprite = sillón[y1 - arriba:y2 - arriba, x1 - izquierda:x2 - izquierda]
    alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
    salida[y1:y2, x1:x2] = (
        sprite[:, :, :3].astype(np.float32) * alpha
        + salida[y1:y2, x1:x2].astype(np.float32) * (1 - alpha)
    ).astype(np.uint8)
    return salida


def dibujar_resultado(imagen: np.ndarray, app: Aplicacion) -> np.ndarray:
    salida = dibujar_suelo(imagen, app.mascara_suelo)
    if app.matriz_imagen_a_suelo is None:
        return dibujar_calibracion(salida, app)

    informe = (
        app.cerebro.revisar_colocacion(suelo_calibrado=True)
        if app.cerebro is not None
        else InformeCerebro(estado="libre", colision=False)
    )
    huella_objeto = obtener_huella_objeto(app)
    capa = salida.copy()
    for obstaculo in app.obstaculos:
        x, y = obstaculo.centro_cm
        r = obstaculo.radio_cm
        huella = np.array([[x-r, y-r], [x+r, y-r], [x+r, y+r], [x-r, y+r]])
        puntos_pantalla = transformar_a_imagen(app, huella)
        cv2.fillPoly(capa, [puntos_pantalla], NARANJA_OBSTACULO)
        cv2.polylines(capa, [puntos_pantalla], True, (0, 80, 230), 2)
        cv2.putText(capa, obstaculo.etiqueta, tuple(puntos_pantalla[0]), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 2)
    salida = cv2.addWeighted(capa, 0.38, salida, 0.62, 0)

    color = ROJO_COLISION if informe.colision else VERDE_LIBRE
    salida = dibujar_imagen_objeto(salida, app)
    objeto_pantalla = transformar_a_imagen(app, huella_objeto)
    cv2.polylines(salida, [objeto_pantalla], True, color, 2)
    aviso = "CONCLUSION: EL SILLON COLISIONA" if informe.colision else "CONCLUSION: EL SILLON NO COLISIONA"
    cv2.putText(salida, aviso, (15, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
    if informe.profundidad_suelo_cm is not None:
        cv2.putText(
            salida,
            f"Profundidad estimada sobre el suelo: {informe.profundidad_suelo_cm:.1f} cm",
            (15, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2,
        )
        cv2.putText(
            salida,
            f"Obstaculos detectados: {informe.cantidad_obstaculos}",
            (15, 84), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2,
        )
    cv2.putText(salida, "Sillon: 70 ancho x 70 alto x 50 fondo cm | arrastra | R: calibrar | Q/Esc: salir",
                (15, salida.shape[0] - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
    if app.posicion_raton is not None:
        cv2.drawMarker(salida, app.posicion_raton, (255, 255, 255), cv2.MARKER_CROSS, 14, 1)
    return salida


def ejecutar(app: Aplicacion) -> None:
    app.cerebro = crear_cerebro(app)
    cv2.namedWindow(VENTANA, cv2.WINDOW_AUTOSIZE)
    cv2.setMouseCallback(VENTANA, recibir_raton, app)
    fotograma = 0
    try:
        while True:
            disponible, imagen = app.camara.read()
            if not disponible:
                print("No se pudo leer un fotograma de la cámara.", file=sys.stderr)
                break
            alto, ancho = imagen.shape[:2]
            escala = min(1.0, 1100 / ancho, 760 / alto)
            if escala < 1:
                imagen = cv2.resize(imagen, (round(ancho * escala), round(alto * escala)))

            fotograma += 1
            if fotograma % app.opciones.cada == 0:
                app.cerebro.analizar_fotograma(
                    imagen,
                    suelo_calibrado=app.matriz_imagen_a_suelo is not None,
                )

            cv2.imshow(VENTANA, dibujar_resultado(imagen, app))
            tecla = cv2.waitKey(1) & 0xFF
            if tecla in (ord("q"), 27):
                break
            if tecla == ord("r"):
                app.puntos_suelo.clear()
                app.matriz_imagen_a_suelo = None
                app.matriz_suelo_a_imagen = None
                app.obstaculos.clear()
                app.cerebro.revisar_colocacion(suelo_calibrado=False)
    finally:
        app.camara.release()
        cv2.destroyAllWindows()


def leer_argumentos() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Colocación virtual de un objeto mediante la webcam.")
    parser.add_argument("--suelo-ancho", type=float, default=300, help="Ancho real del suelo marcado, en cm")
    parser.add_argument("--suelo-fondo", type=float, default=250, help="Fondo real del suelo marcado, en cm")
    parser.add_argument("--camera", type=int, default=0, help="Índice de la webcam")
    parser.add_argument("--modelo", default="yolo11n.pt", help="Modelo YOLO para detectar objetos")
    parser.add_argument("--modelo-suelo", default="nvidia/segformer-b0-finetuned-ade-512-512", help="Modelo SegFormer para segmentar el suelo")
    parser.add_argument("--confianza", type=float, default=0.35, help="Confianza mínima de detección")
    parser.add_argument("--margen", type=float, default=20, help="Margen mínimo de obstáculo en cm")
    parser.add_argument("--cada", type=int, default=5, help="Procesar un fotograma de cada N")
    args = parser.parse_args()
    if min(args.suelo_ancho, args.suelo_fondo, args.margen, args.cada) <= 0:
        parser.error("Las medidas, el margen y --cada deben ser mayores que cero.")
    if ANCHO_OBJETO_CM >= args.suelo_ancho or FONDO_OBJETO_CM >= args.suelo_fondo:
        parser.error("El área de suelo calibrada debe ser mayor que la huella del sillón (70 x 50 cm).")
    return args


if __name__ == "__main__":
    aplicacion = None
    try:
        aplicacion = crear_aplicacion(leer_argumentos())
        cargar_modelos(aplicacion)
        ejecutar(aplicacion)
    except RuntimeError as error:
        print(error, file=sys.stderr)
        sys.exit(1)
    finally:
        if aplicacion is not None:
            aplicacion.camara.release()
