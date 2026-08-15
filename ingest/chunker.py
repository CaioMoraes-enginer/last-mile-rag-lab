"""Extracao e chunking dos PDFs do corpus (KAN-6).

Le cada PDF pagina a pagina (pdfplumber), quebra o texto em blocos coerentes de
tamanho alvo (sem cortar paragrafo no meio) e anexa os IDs de entidade
encontrados (SG-BD, ORD-042, ACCESS-Z03-017, ...). O texto ja sai com os acentos
corretos — o `?` que aparece no terminal e so a exibicao do console do Windows.
"""
import re
from dataclasses import dataclass

import pdfplumber

# IDs canonicos do corpus: MAIUSCULAS com um ou mais hifens (SG-BD, ORD-042,
# INC-Z03-042, ACCESS-Z03-017, POL-MODAL-CT-3.0, ZONA-03, NET-Z03-12...).
ENTITY_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9.]+)+\b")

# Tamanho alvo de um chunk, em caracteres (agrupamos linhas ate chegar perto).
TARGET_CHARS = 800


@dataclass
class PageText:
    """Texto bruto de uma pagina (numero comeca em 1)."""
    page: int
    text: str


def extract_pages(pdf_path: str) -> list[PageText]:
    """Texto de cada pagina nao vazia do PDF."""
    pages: list[PageText] = []
    with pdfplumber.open(pdf_path) as pdf:
        for numero, page in enumerate(pdf.pages, start=1):
            texto = (page.extract_text() or "").strip()
            if texto:
                pages.append(PageText(page=numero, text=texto))
    return pages


def chunk_page(text: str, target_chars: int = TARGET_CHARS) -> list[str]:
    """Quebra o texto de uma pagina em blocos ~target_chars, sem cortar linha."""
    linhas = [linha.strip() for linha in text.split("\n") if linha.strip()]
    chunks: list[str] = []
    atual = ""
    for linha in linhas:
        if atual and len(atual) + len(linha) + 1 > target_chars:
            chunks.append(atual)
            atual = linha
        else:
            atual = f"{atual}\n{linha}" if atual else linha
    if atual:
        chunks.append(atual)
    return chunks


def extract_entity_ids(text: str) -> list[str]:
    """IDs de entidade unicos no texto, em ordem de aparicao."""
    vistos: list[str] = []
    for encontrado in ENTITY_ID_RE.findall(text):
        if encontrado not in vistos:
            vistos.append(encontrado)
    return vistos
