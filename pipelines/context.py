"""Carregamento do corpus e montagem de contexto (KAN-7).

Le o artefato da ingestao (data/corpus/chunks.jsonl, saida do KAN-6/16) — nunca
caminhos ad hoc. Aplica a politica anti-vazamento (escopo secao 11): so entram
chunks de documentos aprovados no manifest; README/docs/escopo/testes NUNCA.

O contexto e montado de forma DETERMINISTICA (ordem por chunk_id = doc, pagina,
posicao) para que a mesma configuracao produza o mesmo prompt. Cada chunk e
rotulado com seu chunk_id para o LLM poder cita-lo.
"""
import hashlib
import json
from pathlib import Path

from pipelines.base import ContextBundle

CORPUS_DIR = Path("data/corpus")
CHUNKS_PATH = CORPUS_DIR / "chunks.jsonl"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"


def _approved_document_ids(manifest_path: Path) -> set[str]:
    """IDs dos documentos aprovados para recuperacao (fonte: manifest)."""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    return {doc["document_id"] for doc in manifest["documents"]}


def load_corpus(
    chunks_path: Path = CHUNKS_PATH,
    manifest_path: Path = MANIFEST_PATH,
) -> list[dict]:
    """Chunks aprovados, ordenados de forma estavel por chunk_id."""
    approved = _approved_document_ids(manifest_path)
    chunks: list[dict] = []
    with chunks_path.open(encoding="utf-8") as arquivo:
        for linha in arquivo:
            linha = linha.strip()
            if not linha:
                continue
            chunk = json.loads(linha)
            if chunk.get("document_id") in approved:
                chunks.append(chunk)
    chunks.sort(key=lambda c: c["chunk_id"])
    return chunks


def build_chunk_index(chunks: list[dict]) -> dict[str, dict]:
    """Indice chunk_id -> chunk, para resolver citacoes a fontes reais."""
    return {c["chunk_id"]: c for c in chunks}


def corpus_hash(chunks: list[dict]) -> str:
    """Hash estavel do corpus usado (integridade + rastreabilidade, RNF-04/05)."""
    h = hashlib.sha256()
    for c in sorted(chunks, key=lambda c: c["chunk_id"]):
        h.update(c["chunk_id"].encode("utf-8"))
        h.update(c.get("source_hash", "").encode("utf-8"))
    return h.hexdigest()


def render_chunk(chunk: dict) -> str:
    """Um chunk rotulado, pronto para o prompt (permite citacao rastreavel)."""
    cab = f"[chunk_id={chunk['chunk_id']} | doc={chunk['document_id']} | page={chunk.get('page')}]"
    return f"{cab}\n{chunk['content']}"


def full_context_bundle(
    chunks_path: Path = CHUNKS_PATH,
    manifest_path: Path = MANIFEST_PATH,
) -> ContextBundle:
    """Monta o contexto COMPLETO (todos os chunks aprovados) — a estrategia do P1.

    Sem selecao, sem top-k: e o baseline de forca bruta. As demais estrategias
    (P2/P3) substituem apenas esta montagem.
    """
    chunks = load_corpus(chunks_path, manifest_path)
    text = "\n\n".join(render_chunk(c) for c in chunks)
    return ContextBundle(
        text=text,
        chunk_ids=[c["chunk_id"] for c in chunks],
        corpus_hash=corpus_hash(chunks),
    )
