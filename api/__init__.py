"""API versionada do Last Mile RAG Lab (KAN-11).

Fronteira HTTP fina sobre os pipelines (KAN-7/8/9): recebe o pedido, escolhe um
pipeline por nome, roda e mapeia o resultado. Nao duplica regras do motor. A
interface (KAN-12) e o Arduino (KAN-13) consomem isto sem importar codigo interno.
"""
