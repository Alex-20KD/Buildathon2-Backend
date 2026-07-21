"""Carga de los tres trámites permitidos para el MVP."""

import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path

DEFAULT_KNOWLEDGE_BASE_PATH = Path(__file__).parent / "data" / "tramites.json"


@dataclass(frozen=True)
class Tramite:
    """Información que el asistente puede comunicar sobre un trámite."""

    nombre: str
    descripcion: str
    requisitos: list[str]
    costo_estimado: str
    tiempo_estimado: str
    palabras_clave: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "Tramite":
        """Convierte el JSON controlado de la base de conocimiento a un trámite."""
        required_fields = {
            "nombre",
            "descripcion",
            "requisitos",
            "costo_estimado",
            "tiempo_estimado",
            "palabras_clave",
        }
        missing_fields = required_fields.difference(data)
        if missing_fields:
            missing = ", ".join(sorted(missing_fields))
            raise ValueError(f"El trámite no contiene los campos requeridos: {missing}")

        requirements = data["requisitos"]
        keywords = data["palabras_clave"]
        if not isinstance(requirements, list) or not isinstance(keywords, list):
            raise ValueError("requisitos y palabras_clave deben ser listas.")

        return cls(
            nombre=str(data["nombre"]),
            descripcion=str(data["descripcion"]),
            requisitos=[str(item) for item in requirements],
            costo_estimado=str(data["costo_estimado"]),
            tiempo_estimado=str(data["tiempo_estimado"]),
            palabras_clave=[str(item) for item in keywords],
        )

    def as_context(self) -> str:
        """Representación textual que se indexa y se entrega al modelo."""
        requirements = "\n".join(f"- {requirement}" for requirement in self.requisitos)
        return (
            f"Trámite: {self.nombre}\n"
            f"Descripción: {self.descripcion}\n"
            f"Requisitos:\n{requirements}\n"
            f"Costo estimado: {self.costo_estimado}\n"
            f"Tiempo estimado: {self.tiempo_estimado}"
        )


def normalize_text(value: str) -> str:
    """Normaliza texto para comparar nombres y palabras clave en español."""
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(character for character in normalized if unicodedata.category(character) != "Mn")


def load_tramites(path: Path = DEFAULT_KNOWLEDGE_BASE_PATH) -> list[Tramite]:
    """Lee y valida la base de conocimiento local."""
    try:
        raw_tramites = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise RuntimeError(f"No se encontró la base de conocimiento: {path}") from error
    except json.JSONDecodeError as error:
        raise RuntimeError(f"La base de conocimiento no es JSON válido: {path}") from error

    if not isinstance(raw_tramites, list):
        raise RuntimeError("tramites.json debe contener una lista de trámites.")

    tramites = [Tramite.from_dict(item) for item in raw_tramites if isinstance(item, dict)]
    if len(tramites) != 3:
        raise RuntimeError("El MVP debe exponer exactamente los tres trámites definidos.")
    return tramites


def find_tramite(name: str, tramites: list[Tramite]) -> Tramite | None:
    """Busca un trámite por su nombre, ignorando mayúsculas y tildes."""
    normalized_name = normalize_text(name)
    return next(
        (tramite for tramite in tramites if normalize_text(tramite.nombre) == normalized_name),
        None,
    )
