"""Jerarquía de agentes, planificación atómica y análisis de cámara."""
from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Mapping

import numpy as np


class Rol(str, Enum):
    DESIGNER = "DESIGNER"
    LOGGER = "LOGGER"
    BACKEND = "BACKEND"
    QA = "QA"


@dataclass(frozen=True)
class TareaAtomica:
    """Una sola operación, un agente responsable y dependencias explícitas."""

    id: str
    rol: Rol
    operacion: str
    entradas: tuple[str, ...]
    salida: str
    depende_de: tuple[str, ...] = ()


class AgenteRol:
    """Agente con una lista cerrada de operaciones (sus herramientas permitidas)."""

    def __init__(self, rol: Rol, operaciones: Mapping[str, Callable[..., Any]]):
        self.rol = rol
        self._operaciones = dict(operaciones)

    def ejecutar(self, operacion: str, entradas: Mapping[str, Any]) -> Any:
        if operacion not in self._operaciones:
            raise ValueError(f"{self.rol.value} no tiene permiso para '{operacion}'.")
        return self._operaciones[operacion](**entradas)


class AgenteLogger:
    """Registra asignaciones, entregas entre agentes y errores sin guardar cargas."""

    def __init__(self, archivo: str | Path):
        self.archivo = Path(archivo)
        self.archivo.parent.mkdir(parents=True, exist_ok=True)
        self._logger = logging.getLogger(f"muemovil.agentes.{self.archivo.resolve()}")
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False
        if not self._logger.handlers:
            manejador = logging.FileHandler(self.archivo, encoding="utf-8")
            manejador.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
            self._logger.addHandler(manejador)

    def registrar(self, evento: str, detalle: str) -> None:
        self._logger.info("evento=%s %s", evento, detalle)

    def cerrar(self) -> None:
        """Libera los archivos abiertos al apagar el servicio o cerrar una prueba."""
        for manejador in self._logger.handlers[:]:
            self._logger.removeHandler(manejador)
            manejador.close()


@dataclass(frozen=True)
class InformeCerebro:
    """Informe del análisis de cámara que recibe la interfaz de escritorio."""

    estado: str
    colision: bool | None = None
    profundidad_suelo_cm: float | None = None
    cantidad_obstaculos: int = 0


class AgenteSuelo:
    """Agente especialista de la aplicación de cámara existente."""

    def __init__(self, analizar_suelo: Callable[[np.ndarray], None]):
        self._analizar_suelo = analizar_suelo

    def ejecutar(self, imagen: np.ndarray) -> None:
        self._analizar_suelo(imagen)


class AgenteObstaculos:
    """Agente especialista de la aplicación de cámara existente."""

    def __init__(self, detectar_obstaculos: Callable[[np.ndarray], int]):
        self._detectar_obstaculos = detectar_obstaculos

    def ejecutar(self, imagen: np.ndarray) -> int:
        return self._detectar_obstaculos(imagen)


class AgenteColisiones:
    """Agente especialista de la aplicación de cámara existente."""

    def __init__(self, comprobar_colision: Callable[[], bool]):
        self._comprobar_colision = comprobar_colision

    def ejecutar(self) -> bool:
        return self._comprobar_colision()


class AgenteProfundidad:
    """Agente especialista de la aplicación de cámara existente."""

    def __init__(self, estimar_profundidad: Callable[[], float]):
        self._estimar_profundidad = estimar_profundidad

    def ejecutar(self) -> float:
        return self._estimar_profundidad()


class Cerebro:
    """Orquestador de mayor jerarquía; asigna y valida todas las tareas."""

    def __init__(
        self,
        agentes_por_rol: Mapping[Rol, AgenteRol] | None = None,
        logger: AgenteLogger | None = None,
        agente_suelo: AgenteSuelo | None = None,
        agente_obstaculos: AgenteObstaculos | None = None,
        agente_colisiones: AgenteColisiones | None = None,
        agente_profundidad: AgenteProfundidad | None = None,
    ):
        self.agentes_por_rol = dict(agentes_por_rol or {})
        self.logger = logger
        self.agente_suelo = agente_suelo
        self.agente_obstaculos = agente_obstaculos
        self.agente_colisiones = agente_colisiones
        self.agente_profundidad = agente_profundidad
        self.informe_actual = InformeCerebro(estado="pendiente_calibracion")
        self._candado_orquestacion = threading.Lock()

    def ejecutar_plan(
        self,
        tareas: tuple[TareaAtomica, ...] | list[TareaAtomica],
        entradas_iniciales: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Resuelve dependencias y ejecuta una tarea cada vez, sin solapamientos."""
        with self._candado_orquestacion:
            return self._ejecutar_plan_en_serie(tareas, entradas_iniciales)

    def _ejecutar_plan_en_serie(
        self,
        tareas: tuple[TareaAtomica, ...] | list[TareaAtomica],
        entradas_iniciales: Mapping[str, Any],
    ) -> dict[str, Any]:
        tareas_por_id = {tarea.id: tarea for tarea in tareas}
        if len(tareas_por_id) != len(tareas):
            raise ValueError("El plan contiene identificadores de tarea duplicados.")
        if any(not tarea.id or not tarea.salida for tarea in tareas):
            raise ValueError("Cada tarea necesita un identificador y una salida.")
        if any(not tarea.operacion for tarea in tareas):
            raise ValueError("Cada tarea debe realizar una operación atómica.")
        ids_tarea = set(tareas_por_id)
        for tarea in tareas:
            desconocidas = set(tarea.depende_de) - ids_tarea
            if desconocidas:
                raise ValueError(f"Dependencias desconocidas en '{tarea.id}': {sorted(desconocidas)}")
            if tarea.id in tarea.depende_de:
                raise ValueError(f"La tarea '{tarea.id}' no puede depender de sí misma.")
        self._validar_qa_final(tareas)

        contexto = dict(entradas_iniciales)
        completadas: set[str] = set()
        pendientes = list(tareas)
        salidas_asignadas: set[str] = set()

        while pendientes:
            tarea_lista = next(
                (tarea for tarea in pendientes if set(tarea.depende_de) <= completadas),
                None,
            )
            if tarea_lista is None:
                raise ValueError("El plan tiene dependencias circulares o imposibles de resolver.")
            tarea = tarea_lista
            pendientes.remove(tarea)
            agente = self.agentes_por_rol.get(tarea.rol)
            if agente is None or agente.rol != tarea.rol:
                raise ValueError(f"No hay un agente autorizado para el rol {tarea.rol.value}.")
            if tarea.salida in contexto or tarea.salida in salidas_asignadas:
                raise ValueError(f"La salida '{tarea.salida}' ya está asignada.")
            faltantes = set(tarea.entradas) - contexto.keys()
            if faltantes:
                raise ValueError(f"Faltan entradas para '{tarea.id}': {sorted(faltantes)}")

            if self.logger:
                self.logger.registrar(
                    "asignacion",
                    f"tarea={tarea.id} agente={tarea.rol.value} operacion={tarea.operacion}",
                )
                for dependencia in tarea.depende_de:
                    self.logger.registrar(
                        "comunicacion",
                        f"origen={dependencia} destino={tarea.id} agente_destino={tarea.rol.value}",
                    )
                self.logger.registrar("inicio", f"tarea={tarea.id} agente={tarea.rol.value}")

            entradas_agente = {clave: contexto[clave] for clave in tarea.entradas}
            try:
                resultado = agente.ejecutar(tarea.operacion, entradas_agente)
            except Exception as error:
                if self.logger:
                    self.logger.registrar(
                        "error",
                        f"tarea={tarea.id} agente={tarea.rol.value} tipo={type(error).__name__} detalle={error}",
                    )
                raise

            contexto[tarea.salida] = resultado
            salidas_asignadas.add(tarea.salida)
            completadas.add(tarea.id)
            if self.logger:
                self.logger.registrar(
                    "fin",
                    f"tarea={tarea.id} agente={tarea.rol.value} salida={tarea.salida}",
                )

        return contexto

    @staticmethod
    def _validar_qa_final(tareas: list[TareaAtomica] | tuple[TareaAtomica, ...]) -> None:
        ids_backend = {tarea.id for tarea in tareas if tarea.rol == Rol.BACKEND}
        for tarea in tareas:
            if tarea.rol == Rol.QA and not ids_backend <= set(tarea.depende_de):
                raise ValueError("QA debe depender explícitamente de todas las tareas BACKEND.")

    def analizar_fotograma(self, imagen: np.ndarray, suelo_calibrado: bool) -> InformeCerebro:
        """Mantiene la coordinación de visión usada por el colocador de escritorio."""
        if self.agente_suelo is None:
            raise RuntimeError("Cerebro no tiene configurado el agente de suelo.")
        self.agente_suelo.ejecutar(imagen)
        if not suelo_calibrado:
            self.informe_actual = InformeCerebro(estado="pendiente_calibracion")
            return self.informe_actual
        if self.agente_obstaculos is None:
            raise RuntimeError("Cerebro no tiene configurado el agente de obstáculos.")
        cantidad = self.agente_obstaculos.ejecutar(imagen)
        return self.revisar_colocacion(True, cantidad)

    def revisar_colocacion(
        self,
        suelo_calibrado: bool,
        cantidad_obstaculos: int | None = None,
    ) -> InformeCerebro:
        if not suelo_calibrado:
            self.informe_actual = InformeCerebro(estado="pendiente_calibracion")
            return self.informe_actual
        if self.agente_colisiones is None or self.agente_profundidad is None:
            raise RuntimeError("Cerebro necesita agentes de colisión y profundidad.")
        colision = self.agente_colisiones.ejecutar()
        profundidad = self.agente_profundidad.ejecutar()
        self.informe_actual = InformeCerebro(
            estado="colision" if colision else "libre",
            colision=colision,
            profundidad_suelo_cm=profundidad,
            cantidad_obstaculos=(
                self.informe_actual.cantidad_obstaculos
                if cantidad_obstaculos is None
                else cantidad_obstaculos
            ),
        )
        return self.informe_actual
