"""Aplicación web/API cuyo flujo de agentes siempre lo dirige Cerebro."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from flask import Flask, Response, jsonify, request
from werkzeug.exceptions import RequestEntityTooLarge

from agentes_web import AgenteBackend, AgenteDesigner, AgenteQA, ErrorSolicitud
from multiagentes import AgenteLogger, Cerebro, Rol, TareaAtomica


DIRECTORIO_PROYECTO = Path(__file__).resolve().parent
LIMITE_SUBIDA_BYTES = 16 * 1024 * 1024


def crear_aplicacion_web(
    crear_detector: Callable[[Path], Any] | None = None,
    segmentar_paredes: Callable[[Any], tuple[Any, Any]] | None = None,
    ruta_log: str | Path | None = None,
) -> Flask:
    """Construye la web y configura el plan de agentes sin cargar modelos aún."""
    aplicacion = Flask(
        __name__,
        template_folder=str(DIRECTORIO_PROYECTO / "templates"),
        static_folder=str(DIRECTORIO_PROYECTO / "static"),
    )
    aplicacion.config["MAX_CONTENT_LENGTH"] = LIMITE_SUBIDA_BYTES

    agente_logger = AgenteLogger(ruta_log or DIRECTORIO_PROYECTO / "agent_activity.log")
    cerebro = Cerebro(
        agentes_por_rol={
            Rol.DESIGNER: AgenteDesigner(DIRECTORIO_PROYECTO / "templates" / "index.html"),
            Rol.BACKEND: AgenteBackend(
                DIRECTORIO_PROYECTO / "yolo11n.pt",
                crear_detector=crear_detector,
                segmentar_paredes=segmentar_paredes,
            ),
            Rol.QA: AgenteQA(),
        },
        logger=agente_logger,
    )
    aplicacion.extensions["cerebro"] = cerebro
    aplicacion.extensions["agente_logger"] = agente_logger

    @aplicacion.get("/")
    def mostrar_pagina() -> Response:
        hoja_estilos = (DIRECTORIO_PROYECTO / "static" / "style.css").read_text(encoding="utf-8")
        textos_interfaz = (DIRECTORIO_PROYECTO / "static" / "app.js").read_text(encoding="utf-8")
        plan = [
            TareaAtomica(
                id="designer.leer_plantilla",
                rol=Rol.DESIGNER,
                operacion="leer_plantilla",
                entradas=(),
                salida="plantilla_html",
            ),
            TareaAtomica(
                id="qa.validar_plantilla",
                rol=Rol.QA,
                operacion="validar_plantilla",
                entradas=("plantilla_html", "hoja_estilos", "textos_interfaz"),
                salida="resultado_qa_pagina",
                depende_de=("designer.leer_plantilla",),
            ),
        ]
        resultados = cerebro.ejecutar_plan(plan, {
            "hoja_estilos": hoja_estilos,
            "textos_interfaz": textos_interfaz,
        })
        return Response(resultados["plantilla_html"], mimetype="text/html")

    @aplicacion.post("/api/analizar")
    def analizar_escenario():
        solicitud = {
            "imagen_escenario": _leer_archivo("imagenEscenario"),
            "imagen_mueble": _leer_archivo("imagenMueble"),
            "ancho_cm": request.form.get("anchoCm"),
            "fondo_cm": request.form.get("fondoCm"),
            "limite_profundidad_cm": request.form.get("limiteProfundidadCm"),
        }
        plan = [
            TareaAtomica(
                id="backend.validar_formulario", rol=Rol.BACKEND,
                operacion="validar_formulario", entradas=("solicitud",),
                salida="entrada_validada",
            ),
            TareaAtomica(
                id="backend.detectar_obstaculos", rol=Rol.BACKEND,
                operacion="detectar_obstaculos", entradas=("entrada_validada",),
                salida="analisis_escenario", depende_de=("backend.validar_formulario",),
            ),
            TareaAtomica(
                id="backend.detectar_paredes", rol=Rol.BACKEND,
                operacion="detectar_paredes", entradas=("entrada_validada",),
                salida="segmentacion_paredes", depende_de=("backend.validar_formulario",),
            ),
            TareaAtomica(
                id="backend.buscar_ubicacion", rol=Rol.BACKEND,
                operacion="buscar_ubicacion",
                entradas=("analisis_escenario", "segmentacion_paredes"),
                salida="propuesta_colocacion",
                depende_de=("backend.detectar_obstaculos", "backend.detectar_paredes"),
            ),
            TareaAtomica(
                id="backend.renderizar_resultado", rol=Rol.BACKEND,
                operacion="renderizar_resultado", entradas=("propuesta_colocacion",),
                salida="respuesta_api", depende_de=("backend.buscar_ubicacion",),
            ),
            TareaAtomica(
                id="qa.validar_respuesta", rol=Rol.QA,
                operacion="validar_respuesta", entradas=("respuesta_api",),
                salida="informe_qa",
                depende_de=(
                    "backend.validar_formulario",
                    "backend.detectar_obstaculos",
                    "backend.detectar_paredes",
                    "backend.buscar_ubicacion",
                    "backend.renderizar_resultado",
                ),
            ),
        ]
        try:
            resultados = cerebro.ejecutar_plan(plan, {"solicitud": solicitud})
        except ErrorSolicitud as error:
            return jsonify(error=str(error)), 400
        except Exception as error:
            agente_logger.registrar(
                "error_http",
                f"ruta=/api/analizar tipo={type(error).__name__} detalle={error}",
            )
            return jsonify(error="El análisis no pudo completarse. Revisa agent_activity.log."), 500

        respuesta = dict(resultados["respuesta_api"])
        respuesta["qa"] = resultados["informe_qa"]
        return jsonify(respuesta)

    @aplicacion.errorhandler(RequestEntityTooLarge)
    def manejar_archivo_grande(_error):
        agente_logger.registrar("error_http", "ruta=/api/analizar tipo=archivo_demasiado_grande")
        return jsonify(error="El envío supera el límite de 16 MB."), 413

    return aplicacion


def _leer_archivo(nombre_campo: str) -> bytes | None:
    archivo = request.files.get(nombre_campo)
    return archivo.read() if archivo else None


app = crear_aplicacion_web()


if __name__ == "__main__":
    # Escuchar en todas las interfaces para que el navegador integrado pueda
    # alcanzar el servicio local a través del reenvío del puerto 8000.
    app.run(host="0.0.0.0", port=8000, debug=False, threaded=True)
