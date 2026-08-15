"""Interface comum dos pipelines de decisao (KAN-7).

Os tres pipelines da v1 respondem a MESMA pergunta e produzem o MESMO contrato
(DecisionResponse). A unica coisa que muda entre eles e COMO recuperam o contexto
entregue ao LLM:

    P1 (KAN-7)  contexto completo, sem recuperacao
    P2 (KAN-8)  RAG vetorial simples
    P3 (KAN-9)  RAG avancado (hibrido + filtros + reranking + ferramentas)

Esta interface captura exatamente essa fronteira via um "template method": o
metodo `retrieve` e ABSTRATO (cada pipeline implementa sua estrategia), e `run`
e o esqueleto COMPARTILHADO que orquestra as etapas na mesma ordem para todos.
So assim o benchmark (KAN-10) compara os pipelines de forma justa.

Separacao de responsabilidades (escopo v1, secao 6):
  - o LLM SUGERE a rota e redige as citacoes (camada probabilistica);
  - o motor deterministico (KAN-4) e a FONTE DE VERDADE dos numeros e da validade.
    O LLM nunca sobrescreve o motor.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from domain.decision import DecisionResponse
from domain.models import Order, RouteCandidate


@dataclass(frozen=True)
class PipelineConfig:
    """Parametros de execucao, versionados para reprodutibilidade (RNF-01).

    Fixar modelo, temperatura e seed faz a mesma configuracao gerar o mesmo
    resultado — requisito de "repeticao controlada para medir variabilidade".
    """
    provider_model: str = "llama3.1"      # modelo do Ollama (provedor local, gratis)
    temperature: float = 0.0              # 0 = o mais deterministico possivel
    seed: int = 42                        # semente registrada no resultado
    max_output_tokens: int = 1536         # teto da resposta (detecta truncamento)
    prompt_version: str = "full_context_v1"


@dataclass
class ContextBundle:
    """O contexto recuperado por um pipeline, pronto para entrar no prompt.

    E o unico artefato que difere entre P1/P2/P3. Carrega tambem a rastreabilidade
    (quais chunks entraram e o hash do corpus) para auditoria e anti-vazamento.
    """
    text: str                             # contexto ja montado (texto dos chunks)
    chunk_ids: list[str]                  # quais chunks entraram, em ordem
    corpus_hash: str                      # hash do corpus usado (integridade, RNF-04)
    char_count: int = 0

    def __post_init__(self) -> None:
        if not self.char_count:
            self.char_count = len(self.text)


@dataclass
class LLMResponse:
    """Resposta crua de um provedor de LLM, com telemetria da chamada."""
    text: str                             # texto devolvido pelo modelo
    model: str                            # modelo efetivamente usado
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    truncated: bool = False               # True se bateu no teto de tokens


@runtime_checkable
class LLMProvider(Protocol):
    """Fronteira com o LLM. O pipeline nao conhece o provedor concreto.

    Implementacoes (Passo 2): OllamaProvider (real) e MockProvider (testes).
    Abstrair atras desta interface e o que permite trocar de modelo/provedor sem
    tocar no pipeline, e rodar os testes sem chamada externa.
    """

    def complete(self, prompt: str, config: PipelineConfig) -> LLMResponse:
        """Envia o prompt e devolve a resposta crua + telemetria."""
        ...


@dataclass
class Telemetry:
    """Metricas obrigatorias por execucao (escopo secao 8)."""
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: float = 0.0
    context_chars: int = 0
    estimated_cost_usd: float = 0.0       # 0.0 no Ollama local; campo geral p/ o harness


@dataclass
class PipelineResult:
    """Saida completa de uma execucao: decisao + evidencias + telemetria + proveniencia.

    A `decision` e o contrato comparavel entre pipelines. Os demais campos existem
    para auditoria e reproducao: prompt/config/hashes e o que o LLM devolveu cru.
    """
    pipeline_name: str
    pipeline_version: str
    decision: DecisionResponse
    telemetry: Telemetry
    context: ContextBundle
    provenance: dict = field(default_factory=dict)   # modelo, params, seed, prompt_version, corpus_hash
    llm_raw: str = ""                                 # texto cru do LLM (auditoria)
    engine_validation: dict | None = None            # etapa do motor registrada A PARTE (requisito 9)
    repair_applied: bool = False                     # se houve estrategia de reparo mensuravel
    errors: list[str] = field(default_factory=list)
    retrieval: list = field(default_factory=list)    # ranking recuperado (chunk_id, rank, score) — P2/P3


class RagPipeline(ABC):
    """Base dos tres pipelines. Subclasses so implementam a recuperacao e o prompt.

    O metodo `run` fixa a ORDEM das etapas para todos os pipelines. Cada subclasse
    define:
      - `retrieve`: a estrategia de recuperacao (a fronteira entre P1/P2/P3);
      - `build_prompt`: como montar o prompt versionado a partir do contexto;
      - `parse_and_validate`: transformar a resposta crua no contrato e validar
        com o motor deterministico (logica compartilhada, definida nos Passos 5-6).
    """

    #: nome curto e estavel do pipeline (ex.: "full_context")
    name: str = "abstract"
    #: versao do pipeline, registrada em cada resultado (RNF-05)
    version: str = "0.0.0"

    @abstractmethod
    def retrieve(self, order: Order, routes: list[RouteCandidate]) -> ContextBundle:
        """Recupera o contexto entregue ao LLM. UNICO ponto que difere por pipeline."""

    def retrieval_records(self) -> list:
        """Ranking recuperado (chunk_id, rank, score, doc, page) para o artefato.

        Vazio no baseline full-context (nao ha ranking); os pipelines com
        recuperacao (P2/P3) sobrescrevem para expor a auditoria da busca.
        """
        return []

    @abstractmethod
    def build_prompt(
        self, context: ContextBundle, order: Order, routes: list[RouteCandidate],
        config: PipelineConfig,
    ) -> str:
        """Monta o prompt versionado (instrucoes + pedido + docs com delimitadores)."""

    @abstractmethod
    def parse_and_validate(
        self, llm: LLMResponse, order: Order, routes: list[RouteCandidate],
    ) -> tuple[DecisionResponse, dict | None, bool, list[str]]:
        """Converte a resposta crua no contrato e valida com o motor.

        Retorna (decisao, registro_da_validacao_do_motor, houve_reparo, erros).
        """

    def run(
        self, order: Order, routes: list[RouteCandidate],
        provider: LLMProvider, config: PipelineConfig | None = None,
    ) -> PipelineResult:
        """Template compartilhado: recupera -> prompt -> LLM -> parseia/valida -> telemetria."""
        config = config or PipelineConfig()

        context = self.retrieve(order, routes)
        prompt = self.build_prompt(context, order, routes, config)
        llm = provider.complete(prompt, config)
        decision, engine_validation, repair_applied, errors = self.parse_and_validate(
            llm, order, routes
        )

        telemetry = Telemetry(
            input_tokens=llm.input_tokens,
            output_tokens=llm.output_tokens,
            latency_ms=llm.latency_ms,
            context_chars=context.char_count,
        )
        provenance = {
            "model": llm.model,
            "temperature": config.temperature,
            "seed": config.seed,
            "prompt_version": config.prompt_version,
            "corpus_hash": context.corpus_hash,
            "chunk_ids": context.chunk_ids,
        }
        return PipelineResult(
            pipeline_name=self.name,
            pipeline_version=self.version,
            decision=decision,
            telemetry=telemetry,
            context=context,
            provenance=provenance,
            llm_raw=llm.text,
            engine_validation=engine_validation,
            repair_applied=repair_applied,
            errors=errors,
            retrieval=self.retrieval_records(),
        )
