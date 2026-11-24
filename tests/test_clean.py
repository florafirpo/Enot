"""Limpieza HTML → texto (paso 3)."""
from __future__ import annotations

from corpus import clean


def test_html_a_texto_conserva_titulos_y_footer_y_saca_menu():
    html = b"""<html><body><nav><a href='/x'>Menu</a></nav><h1>Domaine</h1>
    <h2>Visite classique</h2><p>Precio: 20 EUR.</p><footer>Ouvert 10h-18h</footer>
    <script>alert(1)</script></body></html>"""
    t = clean.html_a_texto(html)
    assert "### Visite classique" in t
    assert "Ouvert 10h-18h" in t
    assert "Menu" not in t and "alert" not in t


def test_quitar_plantilla_saca_lineas_repetidas_salvo_en_la_home():
    paginas = [{"texto": "Home\nCookies"}, {"texto": "Visitas\nCookies"}, {"texto": "Precios\nCookies"}]
    clean.quitar_plantilla(paginas)
    assert paginas[0]["texto"] == "Home\nCookies"
    assert paginas[1]["texto"] == "Visitas" and paginas[2]["texto"] == "Precios"


def test_quitar_plantilla_no_toca_si_hay_pocas_paginas():
    paginas = [{"texto": "A\nCookies"}, {"texto": "B\nCookies"}]
    clean.quitar_plantilla(paginas)
    assert paginas[1]["texto"] == "B\nCookies"
