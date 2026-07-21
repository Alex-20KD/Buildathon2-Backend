"""Pruebas de la base de conocimiento local sin dependencias externas."""

from app.rag.knowledge_base import find_tramite, load_tramites


def test_knowledge_base_contains_only_the_three_supported_tramites() -> None:
    tramites = load_tramites()

    assert [tramite.nombre for tramite in tramites] == [
        "Permiso de Funcionamiento",
        "Patente Municipal",
        "Certificado de Uso de Suelo",
    ]


def test_find_tramite_ignores_accents_and_case() -> None:
    tramite = find_tramite("certificado de uso de suelo", load_tramites())

    assert tramite is not None
    assert tramite.nombre == "Certificado de Uso de Suelo"
