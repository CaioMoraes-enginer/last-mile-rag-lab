"""Gera o artefato de chunks (JSONL) a partir dos PDFs do corpus (KAN-6).

Le o manifest, extrai e chunka cada PDF, anexa metadados (document_id, versao,
pagina, entity_ids, source_hash) e escreve um chunk por linha.

O embedding NAO e gerado aqui de proposito: o artefato e independente de
provedor (decisao do KAN-15). Os vetores 768d entram numa etapa dedicada depois,
com o provedor de embeddings escolhido.

Rode da raiz do projeto:
    python -m ingest.build_jsonl
Depois carregue no banco:
    python -m db.loader data/corpus/chunks.jsonl
"""
import hashlib
import json
from pathlib import Path

from ingest.chunker import chunk_page, extract_entity_ids, extract_pages

CORPUS_DIR = Path("data/corpus")
MANIFEST = CORPUS_DIR / "manifest.json"
DOCS_DIR = CORPUS_DIR / "documents"
OUTPUT = CORPUS_DIR / "chunks.jsonl"


def build_chunks() -> list[dict]:
    """Percorre o manifest e produz a lista de chunks de todos os documentos."""
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    chunks: list[dict] = []

    for doc in manifest["documents"]:
        pdf_path = DOCS_DIR / doc["filename"]
        for page in extract_pages(str(pdf_path)):
            for posicao, content in enumerate(chunk_page(page.text), start=1):
                chunks.append({
                    "chunk_id": f"{doc['document_id']}-P{page.page:02d}-C{posicao:02d}",
                    "document_id": doc["document_id"],
                    "document_title": doc.get("filename"),
                    "document_type": doc.get("document_type"),
                    "page": page.page,
                    "version": doc.get("version"),
                    "entity_ids": extract_entity_ids(content),
                    "content": content,
                    "source_hash": hashlib.sha256(content.encode("utf-8")).hexdigest(),
                })
    return chunks


def main() -> int:
    chunks = build_chunks()
    with OUTPUT.open("w", encoding="utf-8") as saida:
        for chunk in chunks:
            saida.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    documentos = len({c["document_id"] for c in chunks})
    print(f"OK! {len(chunks)} chunks de {documentos} documentos -> {OUTPUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
