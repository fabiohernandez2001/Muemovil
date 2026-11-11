"""Pruebas de integración del flujo Designer → Backend → QA y su registro."""
from __future__ import annotations

import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import cv2
import numpy as np
from io import BytesIO

from web_app import crear_aplicacion_web
from multiagentes import AgenteRol, Cerebro, Rol, TareaAtomica


class CajaFalsa:
    def __init__(self, coordenadas: tuple[int, int, int, int], clase: int = 0):
        self.xyxy = np.asarray([coordenadas], dtype=float)
        self.cls = np.asarray([clase], dtype=float)


class ResultadoDetectorFalso:
    names = {0: "silla"}

    def __init__(self):
        self.boxes = [CajaFalsa((255, 130, 315, 215))]


class DetectorFalso:
    def predict(self, _imagen, conf: float, verbose: bool):
        assert conf == 0.35
        assert verbose is False
        return [ResultadoDetectorFalso()]


def segmentar_paredes_falso(imagen: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    alto, ancho = imagen.shape[:2]
    mascara_pared = np.zeros((alto, ancho), dtype=np.uint8)
    mascara_suelo = np.zeros((alto, ancho), dtype=np.uint8)
    limite_pared = int(alto * 0.30)
    mascara_pared[:limite_pared, :] = 1
    mascara_suelo[limite_pared:, :] = 1
    return mascara_pared, mascara_suelo


def crear_imagen_jpeg(ancho: int, alto: int) -> bytes:
    imagen = np.full((alto, ancho, 3), 226, dtype=np.uint8)
    correcto, datos = cv2.imencode(".jpg", imagen)
    if not correcto:
        raise RuntimeError("No se pudo crear la imagen de prueba.")
    return datos.tobytes()


def crear_imagen_png(ancho: int, alto: int, alpha: bool = False) -> bytes:
    canales = 4 if alpha else 3
    imagen = np.full((alto, ancho, canales), 220, dtype=np.uint8)
    if alpha:
        imagen[:, :, 3] = 255
    correcto, datos = cv2.imencode(".png", imagen)
    if not correcto:
        raise RuntimeError("No se pudo crear la imagen PNG de prueba.")
    return datos.tobytes()


class SistemaMultiagenteWebTests(unittest.TestCase):
    def setUp(self):
        self.directorio_temporal = tempfile.TemporaryDirectory()
        self.archivo_log = Path(self.directorio_temporal.name) / "agent_activity.log"
        self.app = crear_aplicacion_web(
            crear_detector=lambda _ruta: DetectorFalso(),
            segmentar_paredes=segmentar_paredes_falso,
            ruta_log=self.archivo_log,
        )
        self.app.testing = True
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.app.extensions["agente_logger"].cerrar()
        self.directorio_temporal.cleanup()

    def test_pagina_designer_se_sirve_y_qa_la_valida(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn(b"imagenEscenario", respuesta.data)
        self.assertIn(b"limiteProfundidad", respuesta.data)
        for asset_path in ("/static/app.js", "/static/style.css"):
            with self.subTest(asset=asset_path):
                respuesta_asset = self.cliente.get(asset_path)
                self.assertEqual(respuesta_asset.status_code, 200)
                respuesta_asset.close()

    def test_api_detecta_obstaculo_propone_ubicacion_y_pasa_qa(self):
        respuesta = self.cliente.post(
            "/api/analizar",
            data={
                "imagenEscenario": (BytesIO(crear_imagen_jpeg(640, 480)), "escenario.jpg"),
                "anchoCm": "45",
                "fondoCm": "35",
                "limiteProfundidadCm": "500",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        resultado = respuesta.get_json()
        self.assertTrue(resultado["qa"]["correcto"])
        self.assertEqual(resultado["cantidad_obstaculos"], 1)
        self.assertGreaterEqual(resultado["cantidad_paredes"], 1)
        self.assertTrue(resultado["paredes_analizadas"])
        self.assertEqual(resultado["obstaculos"][0]["etiqueta"], "silla")
        self.assertTrue(resultado["objetos_existentes_movidos"] is False)
        self.assertTrue(resultado["imagen_anotada"].startswith("data:image/jpeg;base64,"))
        self.assertEqual(resultado["estado"], "colocado")
        self.assertLessEqual(resultado["proporcion_pared_colocacion"], 0.02)

    def test_cerebro_rechaza_ubicacion_dentro_de_una_pared(self):
        agente_backend = self.app.extensions["cerebro"].agentes_por_rol[Rol.BACKEND]

        def toda_la_imagen_es_pared(imagen):
            mascara = np.ones(imagen.shape[:2], dtype=np.uint8)
            return mascara, mascara

        agente_backend._segmentar_paredes = toda_la_imagen_es_pared
        respuesta = self.cliente.post(
            "/api/analizar",
            data={
                "imagenEscenario": (BytesIO(crear_imagen_jpeg(640, 480)), "escenario.jpg"),
                "anchoCm": "45",
                "fondoCm": "35",
                "limiteProfundidadCm": "500",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        resultado = respuesta.get_json()
        self.assertEqual(resultado["estado"], "sin_espacio")
        self.assertIsNone(resultado["colocacion"])
        self.assertTrue(resultado["qa"]["correcto"])

    def test_rechaza_peticion_sin_mueble_ni_dimensiones(self):
        respuesta = self.cliente.post(
            "/api/analizar",
            data={
                "imagenEscenario": (BytesIO(crear_imagen_jpeg(640, 480)), "escenario.jpg"),
                "limiteProfundidadCm": "500",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("Sube una imagen", respuesta.get_json()["error"])
        self.assertIn("evento=error", self.archivo_log.read_text(encoding="utf-8"))

    def test_acepta_imagen_de_mueble_y_aplica_medidas_nominales(self):
        respuesta = self.cliente.post(
            "/api/analizar",
            data={
                "imagenEscenario": (BytesIO(crear_imagen_jpeg(640, 480)), "escenario.jpg"),
                "imagenMueble": (BytesIO(crear_imagen_png(180, 120, alpha=True)), "mueble.png"),
                "limiteProfundidadCm": "500",
            },
            content_type="multipart/form-data",
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.get_json())
        resultado = respuesta.get_json()
        self.assertIn("70 x 50 cm", resultado["advertencia"])
        self.assertTrue(resultado["qa"]["correcto"])

    def test_cerebro_registra_asignacion_y_comunicacion_entre_roles(self):
        self.cliente.get("/")
        self.cliente.post(
            "/api/analizar",
            data={
                "imagenEscenario": (BytesIO(crear_imagen_jpeg(640, 480)), "escenario.jpg"),
                "anchoCm": "45",
                "fondoCm": "35",
                "limiteProfundidadCm": "500",
            },
            content_type="multipart/form-data",
        )
        registro = self.archivo_log.read_text(encoding="utf-8")
        self.assertIn("agente=DESIGNER", registro)
        self.assertIn("agente=BACKEND", registro)
        self.assertIn("operacion=detectar_paredes", registro)
        self.assertIn("agente=QA", registro)
        self.assertIn("evento=comunicacion", registro)

    def test_cerebro_resuelve_dependencias_sin_solapar_tareas(self):
        agente_backend = AgenteRol(
            Rol.BACKEND,
            {
                "preparar": lambda valor_inicial: valor_inicial + 1,
                "finalizar": lambda valor_preparado: valor_preparado * 2,
            },
        )
        cerebro = Cerebro(agentes_por_rol={Rol.BACKEND: agente_backend})
        tareas = [
            TareaAtomica(
                id="backend.finalizar", rol=Rol.BACKEND, operacion="finalizar",
                entradas=("valor_preparado",), salida="resultado",
                depende_de=("backend.preparar",),
            ),
            TareaAtomica(
                id="backend.preparar", rol=Rol.BACKEND, operacion="preparar",
                entradas=("valor_inicial",), salida="valor_preparado",
            ),
        ]
        resultado = cerebro.ejecutar_plan(tareas, {"valor_inicial": 3})
        self.assertEqual(resultado["resultado"], 8)

        contador_activo = 0
        maximo_activo = 0
        candado_contador = threading.Lock()

        def tarea_lenta():
            nonlocal contador_activo, maximo_activo
            with candado_contador:
                contador_activo += 1
                maximo_activo = max(maximo_activo, contador_activo)
            time.sleep(0.03)
            with candado_contador:
                contador_activo -= 1
            return "terminada"

        cerebro_concurrente = Cerebro(agentes_por_rol={
            Rol.BACKEND: AgenteRol(Rol.BACKEND, {"tarea_lenta": tarea_lenta})
        })
        tarea = [TareaAtomica(
            id="backend.atomica", rol=Rol.BACKEND, operacion="tarea_lenta",
            entradas=(), salida="estado",
        )]
        with ThreadPoolExecutor(max_workers=2) as pool:
            resultados = list(pool.map(
                lambda _numero: cerebro_concurrente.ejecutar_plan(tarea, {}),
                range(2),
            ))
        self.assertEqual(maximo_activo, 1)
        self.assertEqual([resultado["estado"] for resultado in resultados], ["terminada"] * 2)

    def test_qa_no_puede_adelantarse_a_tareas_backend(self):
        plan = [
            TareaAtomica(
                id="backend.validar", rol=Rol.BACKEND, operacion="validar",
                entradas=(), salida="datos",
            ),
            TareaAtomica(
                id="backend.procesar", rol=Rol.BACKEND, operacion="procesar",
                entradas=("datos",), salida="resultado", depende_de=("backend.validar",),
            ),
            TareaAtomica(
                id="qa.revisar", rol=Rol.QA, operacion="revisar",
                entradas=("resultado",), salida="qa", depende_de=("backend.procesar",),
            ),
        ]
        with self.assertRaisesRegex(ValueError, "QA debe depender explícitamente"):
            Cerebro().ejecutar_plan(plan, {})


if __name__ == "__main__":
    unittest.main()
