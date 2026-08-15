"""Comando do benchmark comparativo (KAN-10).

Roda os tres pipelines sobre os casos e persiste relatorio legivel por maquina
(JSON) e por humanos (Markdown).

Exemplos (da raiz do projeto):
    python -m eval.run --provider mock                      # offline, deterministico
    python -m eval.run --provider ollama --repeats 3        # real, com variabilidade
    python -m eval.run --provider mock --ablations          # inclui ablacoes do avancado
"""
import argparse
import json
from datetime import datetime
from pathlib import Path

from eval.report import to_json, to_markdown
from eval.runner import RunConfig, run_harness

OUTPUT_DIR = Path("output")


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark comparativo dos pipelines (KAN-10)")
    parser.add_argument("--provider", choices=["mock", "ollama"], default="mock")
    parser.add_argument("--model", default="llama3")
    parser.add_argument("--embedding-model", default="nomic-embed-text")
    parser.add_argument("--host", default="http://localhost:11434")
    parser.add_argument("--repeats", type=int, default=1)
    parser.add_argument("--ablations", action="store_true")
    parser.add_argument("--out-dir", default=str(OUTPUT_DIR))
    args = parser.parse_args()

    cfg = RunConfig(
        provider=args.provider, model=args.model, embedding_model=args.embedding_model,
        host=args.host, n_repeats=args.repeats, include_ablations=args.ablations,
    )
    out = run_harness(cfg)

    markdown = to_markdown(out)
    print(markdown)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    (out_dir / f"benchmark_{stamp}.json").write_text(
        json.dumps(to_json(out), ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / f"benchmark_{stamp}.md").write_text(markdown, encoding="utf-8")
    print(f"artefatos -> {out_dir}/benchmark_{stamp}.(json|md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
