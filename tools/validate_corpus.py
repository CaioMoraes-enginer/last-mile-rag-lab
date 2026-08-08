import hashlib
import json
import re
from pathlib import Path

import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
CORPUS_DIR = ROOT / "data" / "corpus"
DOCUMENTS_DIR = CORPUS_DIR / "documents"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"

EXPECTED_TERMS = {
    "DOC-01": ["ORD-042", "BICICLETA", "DISPATCHED", "19:32", "DSP-042-06"],
    "DOC-02": ["SG-BD", "SG-CF", "SG-CE", "Rota A", "Rota B", "Rota C"],
    "DOC-03": ["INC-Z03-042", "WTH-Z03-018", "SG-BD", "SG-CF", "+6 min"],
    "DOC-04": ["POL-MODAL-CT-3.0", "ACCESS-Z03-017", "SG-CE", "BICICLETA", "DISPATCHED"],
    "DOC-05": ["slack_minutes", "INSUFFICIENT_EVIDENCE", "Cobertura mínima", "RAG"],
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    documents = manifest["documents"]

    assert manifest["synthetic"] is True
    assert manifest["document_count"] == len(documents) == 5

    total_pages = 0
    combined_text = []
    text_by_id = {}

    for document in documents:
        path = DOCUMENTS_DIR / document["filename"]
        assert path.is_file(), f"Documento ausente: {path}"
        assert sha256(path) == document["sha256"], f"Hash inválido: {path.name}"

        with pdfplumber.open(path) as pdf:
            assert len(pdf.pages) == document["pages"], f"Número de páginas inválido: {path.name}"
            pages = [page.extract_text() or "" for page in pdf.pages]

        text = "\n".join(pages)
        assert len(text) > 1000, f"Texto insuficiente ou não extraível: {path.name}"
        for term in EXPECTED_TERMS[document["document_id"]]:
            assert term in text, f"Termo obrigatório ausente em {path.name}: {term}"

        total_pages += len(pages)
        combined_text.append(text)
        text_by_id[document["document_id"]] = text

    assert total_pages == manifest["page_count"] == 42

    email_pattern = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
    assert not email_pattern.findall("\n".join(combined_text)), "E-mail encontrado no corpus"

    # The manual defines the method but cannot disclose the evaluated case.
    assert "ORD-042" not in text_by_id["DOC-05"]

    print("Corpus válido: 5 documentos, 42 páginas, hashes e conteúdo verificados.")


if __name__ == "__main__":
    main()
