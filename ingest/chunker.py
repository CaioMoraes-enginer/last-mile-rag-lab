"""Extracao e chunking dos PDFs do corpus (KAN-6 + KAN-16).

Le cada PDF com Docling (parsing consciente de layout + reconhecimento de
estrutura de tabela), exporta o conteudo de cada pagina como Markdown — o que
preserva as tabelas no formato `| col | col |` em vez de achatá-las — quebra o
texto em blocos coerentes de tamanho alvo (sem cortar linha no meio) e anexa os
IDs de entidade encontrados (SG-BD, ORD-042, ACCESS-Z03-017, ...).

O extrator anterior (pdfplumber) fica registrado como baseline no historico do
KAN-6 para comparacao no harness de avaliacao (KAN-10).
"""
import os
import re
from dataclasses import dataclass
from functools import lru_cache

# Docling usa torch; em Windows sem headers de OpenMP o torch.compile/inductor
# tenta compilar C++ e falha (omp.h ausente). Rodar em modo eager evita isso.
os.environ.setdefault("TORCHDYNAMO_DISABLE", "1")
os.environ.setdefault("TORCH_COMPILE_DISABLE", "1")

# IDs canonicos do corpus: MAIUSCULAS com um ou mais hifens (SG-BD, ORD-042,
# INC-Z03-042, ACCESS-Z03-017, POL-MODAL-CT-3.0, ZONA-03, NET-Z03-12...).
ENTITY_ID_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9.]+)+\b")

# Tamanho alvo de um chunk, em caracteres (agrupamos linhas ate chegar perto).
TARGET_CHARS = 800


@dataclass
class PageText:
    """Texto (Markdown) de uma pagina (numero comeca em 1)."""
    page: int
    text: str


@lru_cache(maxsize=1)
def _converter():
    """Conversor Docling reutilizado entre documentos (carrega modelos 1x).

    OCR desligado: os PDFs do corpus sao nativos digitais (gerados por
    reportlab), entao o texto vem direto da camada textual, sem erro de OCR.
    Reconhecimento de estrutura de tabela ligado (default) para preservar as
    tabelas no Markdown.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    options = PdfPipelineOptions()
    options.do_ocr = False
    options.do_table_structure = True

    return DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=options)}
    )


def extract_pages(pdf_path: str) -> list[PageText]:
    """Markdown de cada pagina nao vazia do PDF, via Docling."""
    document = _converter().convert(pdf_path).document
    pages: list[PageText] = []
    for numero in range(1, document.num_pages() + 1):
        markdown = document.export_to_markdown(
            page_no=numero, image_placeholder=""
        ).strip()
        if markdown:
            pages.append(PageText(page=numero, text=markdown))
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
