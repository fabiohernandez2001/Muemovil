"""Implementaciones de los roles DESIGNER, BACKEND y QA para la web."""
from __future__ import annotations

import base64
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

import cv2
import numpy as np

from multiagentes import AgenteRol, Rol


class ErrorSolicitud(ValueError):
    """Error causado por un campo o archivo incorrecto enviado por el cliente."""


@dataclass
class EntradaValidada:
    imagen_escenario: np.ndarray
    imagen_mueble: np.ndarray | None
    ancho_mueble_cm: float
    fondo_mueble_cm: float
    limite_profundidad_cm: float
    advertencia: str | None


@dataclass
class AnalisisEscenario:
    entrada: EntradaValidada
    obstaculos: list[dict[str, Any]]


@dataclass
class SegmentacionParedes:
    mascara_paredes: np.ndarray
    mascara_suelo: np.ndarray
    zonas_paredes: list[dict[str, int]]


@dataclass
class PropuestaColocacion:
    analisis: AnalisisEscenario
    segmentacion_paredes: SegmentacionParedes
    colocacion: dict[str, Any] | None
    proporcion_pared_colocacion: float | None


class AgenteDesigner(AgenteRol):
    """Solo lee y entrega la plantilla HTML del diseñador."""

    def __init__(self, archivo_plantilla: str | Path):
        self.archivo_plantilla = Path(archivo_plantilla)
        super().__init__(Rol.DESIGNER, {"leer_plantilla": self.leer_plantilla})

    def leer_plantilla(self) -> str:
        return self.archivo_plantilla.read_text(encoding="utf-8")


class AgenteBackend(AgenteRol):
    """Valida formularios y ejecuta la detección y propuesta de colocación."""

    def __init__(
        self,
        archivo_modelo: str | Path,
        crear_detector: Callable[[Path], Any] | None = None,
        segmentar_paredes: Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]] | None = None,
    ):
        self.archivo_modelo = Path(archivo_modelo)
        self._crear_detector = crear_detector or self._crear_detector_yolo
        self._detector: Any | None = None
        self._segmentar_paredes = segmentar_paredes
        operaciones = {
            "validar_formulario": self.validar_formulario,
            "detectar_obstaculos": self.detectar_obstaculos,
            "detectar_paredes": self.detectar_paredes,
            "buscar_ubicacion": self.buscar_ubicacion,
            "renderizar_resultado": self.renderizar_resultado,
        }
        super().__init__(Rol.BACKEND, operaciones)

    @staticmethod
    def _crear_detector_yolo(ruta_modelo: Path) -> Any:
        from ultralytics import YOLO

        return YOLO(str(ruta_modelo))

    def validar_formulario(self, solicitud: Mapping[str, Any]) -> EntradaValidada:
        """Valida los campos y decodifica imágenes sin ejecutar la detección."""
        datos_escenario = solicitud.get("imagen_escenario")
        if not isinstance(datos_escenario, bytes) or not datos_escenario:
            raise ErrorSolicitud("Selecciona una imagen de escenario.")

        imagen_escenario = self._decodificar_imagen(datos_escenario, "escenario")
        if min(imagen_escenario.shape[:2]) < 64:
            raise ErrorSolicitud("La imagen de escenario debe medir al menos 64 x 64 píxeles.")

        datos_mueble = solicitud.get("imagen_mueble")
        imagen_mueble = None
        if datos_mueble:
            imagen_mueble = self._decodificar_imagen(datos_mueble, "mueble", conservar_alpha=True)

        ancho = self._leer_medida(solicitud.get("ancho_cm"), "ancho")
        fondo = self._leer_medida(solicitud.get("fondo_cm"), "fondo")
        if (ancho is None) != (fondo is None):
            raise ErrorSolicitud("Indica tanto el ancho como el fondo del mueble.")
        advertencia = None
        if ancho is None:
            if imagen_mueble is None:
                raise ErrorSolicitud("Sube una imagen del mueble o indica su ancho y fondo.")
            ancho, fondo = 70.0, 50.0
            advertencia = "Sin medidas físicas, se usa una huella nominal de 70 x 50 cm."

        limite = self._leer_medida(solicitud.get("limite_profundidad_cm"), "límite de profundidad")
        if limite is None:
            raise ErrorSolicitud("Indica la distancia desde la cámara hasta el fondo, en centímetros.")
        if ancho >= limite or fondo >= limite:
            raise ErrorSolicitud("Las medidas del mueble deben ser menores que el límite de profundidad.")

        return EntradaValidada(
            imagen_escenario=imagen_escenario,
            imagen_mueble=imagen_mueble,
            ancho_mueble_cm=ancho,
            fondo_mueble_cm=fondo,
            limite_profundidad_cm=limite,
            advertencia=advertencia,
        )

    @staticmethod
    def _decodificar_imagen(datos: bytes, nombre: str, conservar_alpha: bool = False) -> np.ndarray:
        modo = cv2.IMREAD_UNCHANGED if conservar_alpha else cv2.IMREAD_COLOR
        imagen = cv2.imdecode(np.frombuffer(datos, dtype=np.uint8), modo)
        if imagen is None:
            raise ErrorSolicitud(f"El archivo de {nombre} no contiene una imagen válida.")
        if conservar_alpha and imagen.ndim == 2:
            imagen = cv2.cvtColor(imagen, cv2.COLOR_GRAY2BGRA)
        elif conservar_alpha and imagen.shape[2] == 3:
            imagen = cv2.cvtColor(imagen, cv2.COLOR_BGR2BGRA)
        return imagen

    @staticmethod
    def _leer_medida(valor: Any, nombre: str) -> float | None:
        if valor is None or str(valor).strip() == "":
            return None
        try:
            medida = float(valor)
        except (TypeError, ValueError) as error:
            raise ErrorSolicitud(f"La medida de {nombre} debe ser numérica.") from error
        if not math.isfinite(medida) or medida <= 0:
            raise ErrorSolicitud(f"La medida de {nombre} debe ser mayor que cero.")
        return medida

    def detectar_obstaculos(self, entrada_validada: EntradaValidada) -> AnalisisEscenario:
        """Detecta objetos y asigna a cada uno coordenadas de imagen y profundidad estimada."""
        if self._detector is None:
            self._detector = self._crear_detector(self.archivo_modelo)
        entrada = entrada_validada
        predicciones = self._detector.predict(
            entrada.imagen_escenario,
            conf=0.35,
            verbose=False,
        )[0]
        alto, ancho = entrada.imagen_escenario.shape[:2]
        obstaculos = []
        for caja in predicciones.boxes:
            x1, y1, x2, y2 = map(float, caja.xyxy[0].tolist())
            x1 = int(np.clip(round(x1), 0, ancho - 1))
            x2 = int(np.clip(round(x2), x1 + 1, ancho))
            y1 = int(np.clip(round(y1), 0, alto - 1))
            y2 = int(np.clip(round(y2), y1 + 1, alto))
            clase = int(caja.cls[0])
            nombres = predicciones.names
            etiqueta = nombres.get(clase, str(clase)) if isinstance(nombres, dict) else str(nombres[clase])
            profundidad = self._estimar_profundidad(y2, alto, entrada.limite_profundidad_cm)
            obstaculos.append({
                "etiqueta": etiqueta,
                "x": x1,
                "y": y1,
                "ancho_px": x2 - x1,
                "alto_px": y2 - y1,
                "profundidad_estimada_cm": round(profundidad, 1),
            })
        return AnalisisEscenario(entrada=entrada, obstaculos=obstaculos)

    def detectar_paredes(self, entrada_validada: EntradaValidada) -> SegmentacionParedes:
        """Segmenta paredes y suelo para delimitar la región donde puede ir el mueble."""
        segmentador = self._segmentar_paredes or self._cargar_segmentador_paredes()
        mascara_paredes, mascara_suelo = segmentador(entrada_validada.imagen_escenario)
        forma_esperada = entrada_validada.imagen_escenario.shape[:2]
        if mascara_paredes.shape != forma_esperada or mascara_suelo.shape != forma_esperada:
            raise RuntimeError("El segmentador de paredes devolvió máscaras con tamaño incorrecto.")

        mascara_paredes = (mascara_paredes > 0).astype(np.uint8)
        mascara_suelo = (mascara_suelo > 0).astype(np.uint8)
        alto, ancho = forma_esperada
        tamano_kernel = max(3, int(min(alto, ancho) * 0.012))
        if tamano_kernel % 2 == 0:
            tamano_kernel += 1
        kernel = np.ones((tamano_kernel, tamano_kernel), dtype=np.uint8)
        mascara_paredes = cv2.dilate(mascara_paredes, kernel, iterations=1)

        contornos, _ = cv2.findContours(
            mascara_paredes.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        area_minima = alto * ancho * 0.002
        zonas = []
        for contorno in contornos:
            if cv2.contourArea(contorno) < area_minima:
                continue
            x, y, ancho_zona, alto_zona = cv2.boundingRect(contorno)
            zonas.append({"x": x, "y": y, "ancho_px": ancho_zona, "alto_px": alto_zona})

        return SegmentacionParedes(
            mascara_paredes=mascara_paredes,
            mascara_suelo=mascara_suelo,
            zonas_paredes=sorted(zonas, key=lambda zona: zona["x"]),
        )

    def _cargar_segmentador_paredes(
        self,
    ) -> Callable[[np.ndarray], tuple[np.ndarray, np.ndarray]]:
        """Carga SegFormer ADE20K una sola vez y expone solo la segmentación necesaria."""
        try:
            import torch
            from transformers import AutoImageProcessor, SegformerForSemanticSegmentation
        except ImportError as error:
            raise RuntimeError(
                "Para detectar paredes instala las dependencias con: pip install -r requirements.txt"
            ) from error

        nombre_modelo = "nvidia/segformer-b0-finetuned-ade-512-512"
        procesador = AutoImageProcessor.from_pretrained(nombre_modelo)
        modelo = SegformerForSemanticSegmentation.from_pretrained(nombre_modelo)
        modelo.eval()
        nombres = modelo.config.id2label
        ids_por_nombre = {
            str(nombre).lower(): int(identificador)
            for identificador, nombre in nombres.items()
        }
        id_pared = next((identificador for nombre, identificador in ids_por_nombre.items() if "wall" in nombre), None)
        id_suelo = next((identificador for nombre, identificador in ids_por_nombre.items() if "floor" in nombre), None)
        if id_pared is None or id_suelo is None:
            raise RuntimeError("El modelo ADE20K debe incluir las clases wall y floor.")

        def segmentar(imagen: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
            imagen_rgb = cv2.cvtColor(imagen, cv2.COLOR_BGR2RGB)
            datos = procesador(images=imagen_rgb, return_tensors="pt")
            with torch.inference_mode():
                logits = modelo(**datos).logits
                logits = torch.nn.functional.interpolate(
                    logits, size=imagen.shape[:2], mode="bilinear", align_corners=False
                )
                clases = logits.argmax(dim=1)[0].cpu().numpy()
            return (clases == id_pared).astype(np.uint8), (clases == id_suelo).astype(np.uint8)

        self._segmentar_paredes = segmentar
        return segmentar

    @staticmethod
    def _estimar_profundidad(y_pie: int, alto_imagen: int, limite_cm: float) -> float:
        """Mapeo lineal orientativo: borde superior=fondo; borde inferior=cámara."""
        proporcion = 1.0 - min(max(y_pie / alto_imagen, 0.0), 1.0)
        return max(limite_cm * 0.05, limite_cm * proporcion)

    def buscar_ubicacion(
        self,
        analisis_escenario: AnalisisEscenario,
        segmentacion_paredes: SegmentacionParedes,
    ) -> PropuestaColocacion:
        """Busca una celda libre que esté en suelo y fuera de las paredes."""
        analisis = analisis_escenario
        imagen = analisis.entrada.imagen_escenario
        alto, ancho = imagen.shape[:2]
        limite = analisis.entrada.limite_profundidad_cm
        fov_horizontal = math.radians(60)
        fov_vertical = math.radians(45)
        paso_x = max(16, ancho // 24)
        paso_y = max(16, alto // 24)
        mejor = None
        mejor_puntuacion = float("-inf")
        mejor_proporcion_pared = None

        for centro_y in range(max(1, int(alto * 0.32)), int(alto * 0.88), paso_y):
            profundidad = self._estimar_profundidad(centro_y, alto, limite)
            ancho_px = max(1, round(
                analisis.entrada.ancho_mueble_cm * ancho
                / (2 * profundidad * math.tan(fov_horizontal / 2))
            ))
            alto_px = max(1, round(
                analisis.entrada.fondo_mueble_cm * alto
                / (2 * profundidad * math.tan(fov_vertical / 2))
            ))
            mitad_ancho, mitad_alto = ancho_px // 2, alto_px // 2
            if ancho_px >= ancho or alto_px >= alto:
                continue

            for centro_x in range(max(1, mitad_ancho), ancho - mitad_ancho, paso_x):
                x1, y1 = centro_x - mitad_ancho, centro_y - mitad_alto
                x2, y2 = x1 + ancho_px, y1 + alto_px
                if y1 < 0 or y2 >= alto:
                    continue
                region_pared = segmentacion_paredes.mascara_paredes[y1:y2, x1:x2]
                region_suelo = segmentacion_paredes.mascara_suelo[y1:y2, x1:x2]
                if region_pared.size == 0 or region_suelo.size == 0:
                    continue
                proporcion_pared = np.count_nonzero(region_pared) / region_pared.size
                if proporcion_pared > 0.02:
                    continue
                if np.count_nonzero(region_suelo) / region_suelo.size < 0.55:
                    continue
                if any(self._rectangulos_se_solapan(
                    (x1, y1, x2, y2),
                    (objeto["x"], objeto["y"], objeto["x"] + objeto["ancho_px"], objeto["y"] + objeto["alto_px"]),
                    margen=8,
                ) for objeto in analisis.obstaculos):
                    continue

                distancias_bordes = (x1, ancho - x2, y1, alto - y2)
                despeje_borde = min(distancias_bordes)
                distancia_centro = abs(centro_x - ancho / 2) / max(ancho, 1)
                puntuacion = despeje_borde - distancia_centro * paso_x
                if puntuacion > mejor_puntuacion:
                    mejor_puntuacion = puntuacion
                    mejor = {
                        "x": x1,
                        "y": y1,
                        "ancho_px": ancho_px,
                        "alto_px": alto_px,
                        "profundidad_estimada_cm": round(profundidad, 1),
                    }
                    mejor_proporcion_pared = proporcion_pared

        return PropuestaColocacion(
            analisis=analisis,
            segmentacion_paredes=segmentacion_paredes,
            colocacion=mejor,
            proporcion_pared_colocacion=mejor_proporcion_pared,
        )

    @staticmethod
    def _rectangulos_se_solapan(
        primero: tuple[int, int, int, int],
        segundo: tuple[int, int, int, int],
        margen: int = 0,
    ) -> bool:
        ax1, ay1, ax2, ay2 = primero
        bx1, by1, bx2, by2 = segundo
        return not (
            ax2 + margen <= bx1 or bx2 + margen <= ax1
            or ay2 + margen <= by1 or by2 + margen <= ay1
        )

    def renderizar_resultado(self, propuesta_colocacion: PropuestaColocacion) -> dict[str, Any]:
        """Anota una copia de la escena; los objetos capturados permanecen inmóviles."""
        propuesta = propuesta_colocacion
        analisis = propuesta.analisis
        salida = analisis.entrada.imagen_escenario.copy()
        mascara_paredes = propuesta.segmentacion_paredes.mascara_paredes.astype(bool)
        capa_paredes = salida.copy()
        capa_paredes[mascara_paredes] = (190, 100, 185)
        salida = cv2.addWeighted(capa_paredes, 0.24, salida, 0.76, 0)
        for pared in propuesta.segmentacion_paredes.zonas_paredes:
            cv2.rectangle(
                salida,
                (pared["x"], pared["y"]),
                (pared["x"] + pared["ancho_px"], pared["y"] + pared["alto_px"]),
                (190, 100, 185),
                2,
            )
            cv2.putText(
                salida,
                "Pared detectada",
                (pared["x"], max(18, pared["y"] - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (190, 100, 185),
                2,
            )
        for objeto in analisis.obstaculos:
            esquina = (objeto["x"] + objeto["ancho_px"], objeto["y"] + objeto["alto_px"])
            cv2.rectangle(salida, (objeto["x"], objeto["y"]), esquina, (20, 60, 240), 2)
            cv2.putText(
                salida,
                f"{objeto['etiqueta']} · {objeto['profundidad_estimada_cm']:.0f} cm",
                (objeto["x"], max(18, objeto["y"] - 7)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.48,
                (20, 60, 240),
                2,
            )

        if propuesta.colocacion is not None:
            self._dibujar_mueble(salida, propuesta.colocacion, analisis.entrada.imagen_mueble)

        imagen_ok, imagen_codificada = cv2.imencode(".jpg", salida, [cv2.IMWRITE_JPEG_QUALITY, 88])
        if not imagen_ok:
            raise RuntimeError("No se pudo preparar la imagen de respuesta.")

        return {
            "estado": "colocado" if propuesta.colocacion else "sin_espacio",
            "colision": False if propuesta.colocacion else None,
            "ancho_imagen_px": int(salida.shape[1]),
            "alto_imagen_px": int(salida.shape[0]),
            "obstaculos": analisis.obstaculos,
            "cantidad_obstaculos": len(analisis.obstaculos),
            "paredes": propuesta.segmentacion_paredes.zonas_paredes,
            "cantidad_paredes": len(propuesta.segmentacion_paredes.zonas_paredes),
            "paredes_analizadas": True,
            "proporcion_pared_colocacion": propuesta.proporcion_pared_colocacion,
            "colocacion": propuesta.colocacion,
            "imagen_anotada": "data:image/jpeg;base64," + base64.b64encode(imagen_codificada).decode("ascii"),
            "limite_profundidad_cm": analisis.entrada.limite_profundidad_cm,
            "advertencia": analisis.entrada.advertencia,
            "objetos_existentes_movidos": False,
            "nota_profundidad": (
                "Profundidad aproximada mediante la posición vertical de la imagen y el límite indicado; "
                "no es una medición 3D calibrada."
            ),
        }

    @staticmethod
    def _dibujar_mueble(
        imagen: np.ndarray,
        colocacion: Mapping[str, int | float],
        imagen_mueble: np.ndarray | None,
    ) -> None:
        x, y = int(colocacion["x"]), int(colocacion["y"])
        ancho, alto = int(colocacion["ancho_px"]), int(colocacion["alto_px"])
        x2, y2 = x + ancho, y + alto
        if imagen_mueble is None:
            capa = imagen.copy()
            cv2.rectangle(capa, (x, y), (x2, y2), (60, 190, 105), -1)
            imagen[:] = cv2.addWeighted(capa, 0.28, imagen, 0.72, 0)
        else:
            sprite = cv2.resize(imagen_mueble, (ancho, alto), interpolation=cv2.INTER_AREA)
            alpha = sprite[:, :, 3:4].astype(np.float32) / 255.0
            imagen[y:y2, x:x2] = (
                sprite[:, :, :3].astype(np.float32) * alpha
                + imagen[y:y2, x:x2].astype(np.float32) * (1 - alpha)
            ).astype(np.uint8)
        cv2.rectangle(imagen, (x, y), (x2, y2), (60, 190, 105), 2)
        cv2.putText(imagen, "Mueble propuesto", (x, max(18, y - 7)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (60, 190, 105), 2)


class AgenteQA(AgenteRol):
    """Comprueba las salidas del diseñador y del backend sin alterar sus datos."""

    def __init__(self):
        super().__init__(Rol.QA, {
            "validar_plantilla": self.validar_plantilla,
            "validar_respuesta": self.validar_respuesta,
        })

    @staticmethod
    def validar_plantilla(
        plantilla_html: str,
        hoja_estilos: str,
        textos_interfaz: str,
    ) -> dict[str, bool]:
        elementos = (
            'id="imagenEscenario"',
            'id="imagenMueble"',
            'id="limiteProfundidad"',
            'id="formulario"',
            'name="viewport"',
            '<html lang="es">',
            'id="idioma"',
            '🇪🇸 Español',
            '🇬🇧 English',
            '🇫🇷 Français',
            'aria-live="polite"',
            'data-i18n=',
            'class="language-label"',
        )
        checks = {elemento: elemento in plantilla_html for elemento in elementos}
        checks["hoja_estilos_adaptable"] = "@media (max-width: 800px)" in hoja_estilos and "@media (max-width: 420px)" in hoja_estilos
        checks["foco_visible"] = ":focus-visible" in hoja_estilos
        checks["movimiento_reducido"] = "prefers-reduced-motion" in hoja_estilos
        checks["traducciones_es_en_fr"] = all(f"{idioma}: {{" in textos_interfaz for idioma in ("es", "en", "fr"))
        for termino_interno in ("Cerebro", "Backend", "DESIGNER", "LOGGER", "agente"):
            checks[f"sin_{termino_interno.lower()}"] = termino_interno.lower() not in plantilla_html.lower()
        checks_fallidas = [nombre for nombre, correcto in checks.items() if not correcto]
        if checks_fallidas:
            raise ValueError(
                "La página no cumple estas comprobaciones de diseño, accesibilidad o privacidad: "
                + ", ".join(checks_fallidas)
            )
        return checks

    @staticmethod
    def validar_respuesta(respuesta_api: Mapping[str, Any]) -> dict[str, Any]:
        respuesta = respuesta_api
        obligatorios = {
            "estado", "ancho_imagen_px", "alto_imagen_px", "obstaculos",
            "cantidad_obstaculos", "paredes", "cantidad_paredes", "paredes_analizadas",
            "proporcion_pared_colocacion", "colocacion", "imagen_anotada",
        }
        faltantes = obligatorios - respuesta.keys()
        if faltantes:
            raise ValueError(f"La respuesta del backend no incluye: {sorted(faltantes)}")
        if respuesta["estado"] not in {"colocado", "sin_espacio"}:
            raise ValueError("El backend devolvió un estado de colocación desconocido.")
        if respuesta["cantidad_obstaculos"] != len(respuesta["obstaculos"]):
            raise ValueError("El recuento de obstáculos no coincide con sus coordenadas.")
        if respuesta["cantidad_paredes"] != len(respuesta["paredes"]):
            raise ValueError("El recuento de paredes no coincide con sus coordenadas.")
        if respuesta["paredes_analizadas"] is not True:
            raise ValueError("La segmentación de paredes no se completó.")
        ancho_imagen = int(respuesta["ancho_imagen_px"])
        alto_imagen = int(respuesta["alto_imagen_px"])
        if ancho_imagen <= 0 or alto_imagen <= 0:
            raise ValueError("El tamaño de imagen de la respuesta no es válido.")
        for obstaculo in respuesta["obstaculos"]:
            x1, y1 = int(obstaculo["x"]), int(obstaculo["y"])
            x2 = x1 + int(obstaculo["ancho_px"])
            y2 = y1 + int(obstaculo["alto_px"])
            if x1 < 0 or y1 < 0 or x2 > ancho_imagen or y2 > alto_imagen:
                raise ValueError("Una caja de obstáculo está fuera de la imagen.")

        colocacion = respuesta["colocacion"]
        if colocacion is not None:
            x1, y1 = int(colocacion["x"]), int(colocacion["y"])
            x2 = x1 + int(colocacion["ancho_px"])
            y2 = y1 + int(colocacion["alto_px"])
            if x1 < 0 or y1 < 0 or x2 > ancho_imagen or y2 > alto_imagen:
                raise ValueError("La propuesta de mueble queda fuera de la imagen.")
            proporcion_pared = respuesta["proporcion_pared_colocacion"]
            if proporcion_pared is None or float(proporcion_pared) > 0.02:
                raise ValueError("La ubicación propuesta invade la pared detectada.")
            for obstaculo in respuesta["obstaculos"]:
                ox1, oy1 = int(obstaculo["x"]), int(obstaculo["y"])
                ox2 = ox1 + int(obstaculo["ancho_px"])
                oy2 = oy1 + int(obstaculo["alto_px"])
                if not (x2 <= ox1 or ox2 <= x1 or y2 <= oy1 or oy2 <= y1):
                    raise ValueError("La ubicación propuesta se solapa con un obstáculo.")
        elif respuesta["proporcion_pared_colocacion"] is not None:
            raise ValueError("No debe existir porcentaje de pared sin una propuesta.")

        for pared in respuesta["paredes"]:
            x1, y1 = int(pared["x"]), int(pared["y"])
            x2 = x1 + int(pared["ancho_px"])
            y2 = y1 + int(pared["alto_px"])
            if x1 < 0 or y1 < 0 or x2 > ancho_imagen or y2 > alto_imagen:
                raise ValueError("Una zona de pared está fuera de la imagen.")

        if not str(respuesta["imagen_anotada"]).startswith("data:image/jpeg;base64,"):
            raise ValueError("La imagen anotada no está codificada correctamente.")
        if respuesta.get("objetos_existentes_movidos") is not False:
            raise ValueError("El resultado no garantiza que los objetos existentes permanezcan inmóviles.")
        return {"correcto": True, "comprobaciones": len(obligatorios) + 5}
