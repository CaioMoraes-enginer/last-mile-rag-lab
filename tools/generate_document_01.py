from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "corpus" / "documents" / "01-dossie-operacional-de-pedidos.pdf"

INK = colors.HexColor("#172A35")
NAVY = colors.HexColor("#0B2635")
TEAL = colors.HexColor("#138A8A")
CYAN = colors.HexColor("#38C6C6")
AMBER = colors.HexColor("#F2A93B")
RED = colors.HexColor("#C94C4C")
GREEN = colors.HexColor("#28866B")
PAPER = colors.HexColor("#F3F0E7")
WHITE = colors.HexColor("#FFFFFF")
MUTED = colors.HexColor("#62737C")
LINE = colors.HexColor("#CDD4D3")
SOFT_TEAL = colors.HexColor("#DCECE8")
SOFT_AMBER = colors.HexColor("#F6E7C7")
SOFT_RED = colors.HexColor("#F3DADA")


pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))


styles = getSampleStyleSheet()
styles.add(
    ParagraphStyle(
        name="CoverKicker",
        fontName="Arial-Bold",
        fontSize=9,
        leading=12,
        textColor=CYAN,
        tracking=1.8,
        spaceAfter=9,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverTitle",
        fontName="Arial-Bold",
        fontSize=31,
        leading=34,
        textColor=WHITE,
        spaceAfter=12,
    )
)
styles.add(
    ParagraphStyle(
        name="CoverSubtitle",
        fontName="Arial",
        fontSize=12,
        leading=18,
        textColor=colors.HexColor("#C9D7DB"),
        spaceAfter=20,
    )
)
styles.add(
    ParagraphStyle(
        name="SectionKicker",
        fontName="Arial-Bold",
        fontSize=7.5,
        leading=10,
        textColor=TEAL,
        tracking=1.2,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="H1Custom",
        fontName="Arial-Bold",
        fontSize=22,
        leading=26,
        textColor=INK,
        spaceAfter=8,
    )
)
styles.add(
    ParagraphStyle(
        name="H2Custom",
        fontName="Arial-Bold",
        fontSize=13,
        leading=16,
        textColor=INK,
        spaceBefore=8,
        spaceAfter=6,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyCustom",
        fontName="Arial",
        fontSize=9.2,
        leading=13.5,
        textColor=INK,
        spaceAfter=7,
    )
)
styles.add(
    ParagraphStyle(
        name="BodyBold",
        fontName="Arial-Bold",
        fontSize=9.2,
        leading=13.5,
        textColor=INK,
        spaceAfter=4,
    )
)
styles.add(
    ParagraphStyle(
        name="Small",
        fontName="Arial",
        fontSize=7.5,
        leading=10.2,
        textColor=MUTED,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallDark",
        fontName="Arial",
        fontSize=7.5,
        leading=10.2,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="SmallBold",
        fontName="Arial-Bold",
        fontSize=7.5,
        leading=10.2,
        textColor=INK,
    )
)
styles.add(
    ParagraphStyle(
        name="TableHeader",
        fontName="Arial-Bold",
        fontSize=7.5,
        leading=10.2,
        textColor=WHITE,
    )
)
styles.add(
    ParagraphStyle(
        name="Callout",
        fontName="Arial",
        fontSize=9.5,
        leading=14,
        textColor=INK,
        leftIndent=8,
        rightIndent=8,
        spaceBefore=5,
        spaceAfter=5,
    )
)
styles.add(
    ParagraphStyle(
        name="MetricValue",
        fontName="Arial-Bold",
        fontSize=19,
        leading=21,
        textColor=NAVY,
        alignment=TA_CENTER,
    )
)
styles.add(
    ParagraphStyle(
        name="MetricLabel",
        fontName="Arial-Bold",
        fontSize=7,
        leading=9,
        textColor=MUTED,
        alignment=TA_CENTER,
    )
)


def p(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def cell(text, header=False):
    return Paragraph(str(text), styles["TableHeader" if header else "SmallDark"])


def section(kicker, title, intro=None):
    items = [p(kicker.upper(), "SectionKicker"), p(title, "H1Custom")]
    if intro:
        items.append(p(intro))
    return items


def data_table(rows, widths, aligns=None, font_size=7.2):
    prepared = []
    for row_index, row in enumerate(rows):
        prepared.append([cell(value, row_index == 0) for value in row])
    table = Table(prepared, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), WHITE),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), WHITE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, colors.HexColor("#EAEDE8")]),
        ("GRID", (0, 0), (-1, -1), 0.45, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]
    if aligns:
        for col, align in enumerate(aligns):
            commands.append(("ALIGN", (col, 1), (col, -1), align))
    table.setStyle(TableStyle(commands))
    return table


def callout(title, body, background=SOFT_TEAL, accent=TEAL):
    content = Table(
        [[p(title, "BodyBold")], [p(body, "Callout")]],
        colWidths=[169 * mm],
    )
    content.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), background),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#BACCC8")),
                ("LINEBEFORE", (0, 0), (0, -1), 4, accent),
                ("LEFTPADDING", (0, 0), (-1, -1), 10),
                ("RIGHTPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, 0), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 8),
            ]
        )
    )
    return content


def metric_cards(metrics):
    cards = []
    for value, label in metrics:
        cards.append([p(value, "MetricValue"), p(label.upper(), "MetricLabel")])
    table = Table([cards], colWidths=[42.2 * mm] * len(cards), rowHeights=[29 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), WHITE),
                ("BOX", (0, 0), (-1, -1), 0.5, LINE),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, LINE),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    return table


def on_page(canvas, doc):
    width, height = A4
    page = doc.page
    canvas.saveState()
    if page == 1:
        canvas.setFillColor(NAVY)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#103B4A"))
        canvas.circle(width + 18 * mm, height - 32 * mm, 55 * mm, fill=1, stroke=0)
        canvas.setFillColor(colors.HexColor("#0F5260"))
        canvas.circle(width - 5 * mm, 10 * mm, 35 * mm, fill=1, stroke=0)
        canvas.setStrokeColor(CYAN)
        canvas.setLineWidth(1.2)
        canvas.line(21 * mm, 29 * mm, 57 * mm, 29 * mm)
        canvas.setFont("Arial-Bold", 7)
        canvas.setFillColor(colors.HexColor("#BCD0D5"))
        canvas.drawString(21 * mm, 20 * mm, "LAST MILE RAG LAB  /  DOCUMENTO SINTETICO")
        canvas.drawRightString(width - 18 * mm, 20 * mm, "CORPUS V0.1")
    else:
        canvas.setFillColor(PAPER)
        canvas.rect(0, 0, width, height, fill=1, stroke=0)
        canvas.setFillColor(NAVY)
        canvas.rect(0, height - 15 * mm, width, 15 * mm, fill=1, stroke=0)
        canvas.setFillColor(CYAN)
        canvas.rect(0, height - 15 * mm, 6 * mm, 15 * mm, fill=1, stroke=0)
        canvas.setFont("Arial-Bold", 7.5)
        canvas.setFillColor(WHITE)
        canvas.drawString(13 * mm, height - 9.5 * mm, "NEXUS LOGISTICS  /  INTELIGENCIA OPERACIONAL")
        canvas.drawRightString(width - 15 * mm, height - 9.5 * mm, "DOC-01  |  TURNO 08 AGO 2026")
        canvas.setStrokeColor(LINE)
        canvas.setLineWidth(0.5)
        canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
        canvas.setFont("Arial", 7)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 9.5 * mm, "Dado integralmente sintetico. Nao representa operacao, pedido ou pessoa real.")
        canvas.drawRightString(width - 18 * mm, 9.5 * mm, f"Pagina {page - 1} de 9")
    canvas.restoreState()


def build_story():
    story = []

    # Cover
    story.extend(
        [
            Spacer(1, 38 * mm),
            p("DOSSIÊ OPERACIONAL  /  DOCUMENTO 01", "CoverKicker"),
            p("Pedidos e eventos<br/>do turno", "CoverTitle"),
            p(
                "Snapshot consolidado para análise operacional, auditoria temporal e experimentos de recuperação de conhecimento.",
                "CoverSubtitle",
            ),
            Spacer(1, 12 * mm),
        ]
    )
    cover_meta = Table(
        [
            [p("JANELA ANALISADA", "Small"), p("GERADO EM", "Small"), p("CLASSIFICAÇÃO", "Small")],
            [
                Paragraph("18:30 - 19:15 BRT", ParagraphStyle("cw1", parent=styles["BodyBold"], textColor=WHITE)),
                Paragraph("08/08/2026 19:15", ParagraphStyle("cw2", parent=styles["BodyBold"], textColor=WHITE)),
                Paragraph("SINTÉTICO / PÚBLICO", ParagraphStyle("cw3", parent=styles["BodyBold"], textColor=CYAN)),
            ],
        ],
        colWidths=[56 * mm, 56 * mm, 56 * mm],
    )
    cover_meta.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#123746")),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#3B6470")),
                ("INNERGRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#3B6470")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(cover_meta)
    story.append(PageBreak())

    # Page 1
    story.extend(
        section(
            "Escopo do artefato",
            "O que este dossiê representa",
            "Este relatório consolida pedidos e eventos recebidos durante um turno fictício de uma operação de entrega. Ele funciona como fonte humana de consulta e como documento de entrada para o experimento de RAG.",
        )
    )
    story.append(
        callout(
            "Regra de separação de conhecimento",
            "Este documento registra o que aconteceu com cada pedido. Ele não contém mapa viário, incidentes externos, políticas de acesso ou cálculo de rota. Essas evidências pertencem aos documentos 02 a 05.",
        )
    )
    story.append(Spacer(1, 5 * mm))
    story.append(p("Conteúdo incluído", "H2Custom"))
    scope_rows = [
        ["Bloco", "Conteúdo", "Uso no experimento"],
        ["Pedidos", "Identificador, zona, modal, prioridade e promessa", "Filtragem por metadados"],
        ["Eventos", "Linha do tempo e estado operacional", "Raciocínio temporal"],
        ["Qualidade", "Duplicidades, atrasos de ingestão e lacunas", "Robustez e deduplicação"],
        ["Distratores", "Pedidos semelhantes e registros históricos", "Precisão de recuperação"],
    ]
    story.append(data_table(scope_rows, [35 * mm, 66 * mm, 68 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(p("Pergunta âncora do benchmark", "H2Custom"))
    story.append(
        callout(
            "Caso ORD-042",
            "Considerando o pedido, seu estado, modal e janela prometida, qual rota é operacionalmente válida e minimiza o tempo estimado? A resposta completa exige combinar este dossiê com os demais documentos do corpus.",
            SOFT_AMBER,
            AMBER,
        )
    )
    story.append(Spacer(1, 6 * mm))
    story.append(
        p(
            "Nota metodológica: nomes, IDs, horários e métricas foram criados exclusivamente para este laboratório. Nenhum endereço ou dado pessoal é utilizado.",
            "Small",
        )
    )
    story.append(PageBreak())

    # Page 2
    story.extend(section("Visão geral", "Panorama do turno", "Snapshot às 19:15 BRT, antes da conclusão dos pedidos ainda em rota."))
    story.append(
        metric_cards(
            [
                ("28", "pedidos ativos"),
                ("11", "em preparação"),
                ("9", "despachados"),
                ("3", "com atenção"),
            ]
        )
    )
    story.append(Spacer(1, 8 * mm))
    story.append(p("Distribuição operacional", "H2Custom"))
    summary_rows = [
        ["Zona", "Ativos", "Bicicleta", "Moto", "Automóvel", "Prioritários"],
        ["ZONA-01", "6", "2", "3", "1", "1"],
        ["ZONA-02", "7", "1", "5", "1", "0"],
        ["ZONA-03", "9", "4", "4", "1", "3"],
        ["ZONA-04", "6", "1", "3", "2", "1"],
    ]
    story.append(data_table(summary_rows, [32 * mm, 23 * mm, 28 * mm, 25 * mm, 31 * mm, 30 * mm], ["LEFT", "CENTER", "CENTER", "CENTER", "CENTER", "CENTER"]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Alertas do snapshot", "H2Custom"))
    alerts = [
        ["Severidade", "Referência", "Resumo"],
        ["ALTA", "ORD-042", "Pedido prioritário despachado; depende de decisão de rota atualizada."],
        ["MÉDIA", "ORD-204", "Evento READY_TO_PICKUP recebido com atraso de ingestão."],
        ["MÉDIA", "ORD-420", "Duas mensagens DISPATCHED com o mesmo event_id."],
        ["BAIXA", "ORD-024", "Promessa revisada após confirmação; versão anterior preservada."],
    ]
    story.append(data_table(alerts, [27 * mm, 29 * mm, 113 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(
        callout(
            "Atenção à similaridade de IDs",
            "ORD-042, ORD-024, ORD-204 e ORD-420 aparecem no mesmo turno. Consultas que ignoram o identificador exato podem recuperar o pedido errado.",
            SOFT_RED,
            RED,
        )
    )
    story.append(PageBreak())

    # Page 3
    story.extend(section("Pedido de referência", "Ficha operacional - ORD-042", "Registro consolidado do pedido usado no cenário principal do laboratório."))
    order_rows = [
        ["Campo", "Valor", "Origem"],
        ["order_id", "ORD-042", "order_snapshot"],
        ["display_id", "#8042", "order_snapshot"],
        ["categoria", "FOOD / DELIVERY", "order_snapshot"],
        ["região", "ZONA-03", "merchant_profile"],
        ["merchant_id", "MRC-Z03-07", "order_snapshot"],
        ["modal atribuído", "BICICLETA", "driver_assignment"],
        ["prioridade", "PRIORITY-1", "sla_classification"],
        ["criado em", "08/08/2026 18:48:12 BRT", "event_stream"],
        ["prometido até", "08/08/2026 19:32:00 BRT", "order_snapshot v3"],
        ["estado no snapshot", "DISPATCHED", "event reducer"],
        ["despachado em", "08/08/2026 19:08:31 BRT", "event DSP-042-06"],
        ["setor operacional", "Z03-NORTE", "dispatch_context"],
    ]
    story.append(data_table(order_rows, [42 * mm, 69 * mm, 58 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(
        callout(
            "Evidência útil para recuperação",
            "O pedido está despachado, utiliza bicicleta, pertence à ZONA-03 e possui promessa para 19:32. Nenhuma dessas informações determina sozinha a melhor rota.",
        )
    )
    story.append(Spacer(1, 7 * mm))
    story.append(p("Campos propositalmente ausentes", "H2Custom"))
    story.append(
        p(
            "Este documento não informa bloqueios, condições meteorológicas, corredores temporários, permissões de acesso ou tempos de cada rota. O pipeline deve recuperar essas informações em fontes externas do corpus.",
        )
    )
    story.append(PageBreak())

    # Page 4
    story.extend(section("Raciocínio temporal", "Linha do tempo - ORD-042", "Eventos apresentados por horário de ocorrência, não por horário de ingestão."))
    event_rows = [
        ["Ocorrido", "Ingerido", "Código", "event_id", "Descrição"],
        ["18:48:12", "18:48:13", "PLACED", "PLC-042-01", "Pedido criado"],
        ["18:50:04", "18:50:05", "CONFIRMED", "CFM-042-02", "Pedido confirmado"],
        ["18:54:20", "18:54:22", "PREPARATION_STARTED", "PRS-042-03", "Preparo iniciado"],
        ["19:03:44", "19:03:46", "READY_TO_PICKUP", "RTP-042-04", "Pedido pronto"],
        ["19:05:17", "19:05:18", "ASSIGN_DRIVER", "ADR-042-05", "Bicicleta atribuída"],
        ["19:08:31", "19:08:32", "DISPATCHED", "DSP-042-06", "Saída registrada"],
        ["19:08:31", "19:08:36", "DISPATCHED", "DSP-042-06", "Redelivery duplicado"],
    ]
    story.append(data_table(event_rows, [24 * mm, 24 * mm, 36 * mm, 31 * mm, 54 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Estado derivado", "H2Custom"))
    reducer_rows = [
        ["Regra", "Resultado"],
        ["Ordenar por occurred_at", "Evita interpretar atraso de ingestão como mudança temporal"],
        ["Deduplicar por event_id", "DSP-042-06 é processado uma única vez"],
        ["Aplicar máquina de estados", "READY_TO_PICKUP -> ASSIGN_DRIVER -> DISPATCHED"],
        ["Estado final às 19:15", "DISPATCHED"],
    ]
    story.append(data_table(reducer_rows, [55 * mm, 114 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(
        callout(
            "Por que não deixar isso para a LLM?",
            "Deduplicação e redução de eventos são operações determinísticas. A LLM recebe o estado calculado e concentra seu raciocínio nas evidências documentais e na explicação da decisão.",
            SOFT_AMBER,
            AMBER,
        )
    )
    story.append(PageBreak())

    # Page 5
    story.extend(section("Qualidade dos dados", "Ocorrências de ingestão", "Problemas controlados que simulam comportamentos comuns em pipelines orientados a eventos."))
    quality_rows = [
        ["ID", "Pedido", "Tipo", "Impacto", "Tratamento esperado"],
        ["DQ-018", "ORD-042", "DUPLICATE", "Baixo", "Deduplicar DSP-042-06"],
        ["DQ-019", "ORD-204", "LATE_ARRIVAL", "Médio", "Ordenar por occurred_at"],
        ["DQ-020", "ORD-420", "DUPLICATE", "Médio", "Manter primeira ocorrência válida"],
        ["DQ-021", "ORD-024", "VERSION_CONFLICT", "Médio", "Usar promessa da versão v3"],
        ["DQ-022", "ORD-043", "MISSING_OPTIONAL", "Baixo", "Não inferir driver_position"],
    ]
    story.append(data_table(quality_rows, [23 * mm, 25 * mm, 35 * mm, 23 * mm, 63 * mm]))
    story.append(Spacer(1, 9 * mm))
    story.append(p("Registro fora de ordem - ORD-204", "H2Custom"))
    late_rows = [
        ["occurred_at", "ingested_at", "evento", "observação"],
        ["18:56:02", "18:56:03", "CONFIRMED", "Fluxo normal"],
        ["19:02:11", "19:11:54", "READY_TO_PICKUP", "Atraso de 9 min 43 s"],
        ["19:08:06", "19:08:08", "ASSIGN_DRIVER", "Chegou antes no pipeline"],
    ]
    story.append(data_table(late_rows, [34 * mm, 34 * mm, 42 * mm, 59 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(
        callout(
            "Critério de verdade",
            "Para reconstruir o ciclo do pedido, occurred_at tem precedência temporal. ingested_at permanece disponível para medir atraso e investigar a saúde do pipeline.",
        )
    )
    story.append(PageBreak())

    # Page 6
    story.extend(section("Fila do turno", "Pedidos ativos e distratores", "Recorte operacional com identificadores e atributos semanticamente próximos ao caso principal."))
    active_rows = [
        ["Pedido", "Zona", "Estado", "Modal", "Promessa", "Prioridade"],
        ["ORD-024", "ZONA-03", "CONFIRMED", "MOTO", "19:40", "STANDARD"],
        ["ORD-038", "ZONA-02", "DISPATCHED", "MOTO", "19:27", "PRIORITY-2"],
        ["ORD-041", "ZONA-03", "READY_TO_PICKUP", "BICICLETA", "19:35", "STANDARD"],
        ["ORD-042", "ZONA-03", "DISPATCHED", "BICICLETA", "19:32", "PRIORITY-1"],
        ["ORD-043", "ZONA-04", "DISPATCHED", "AUTOMÓVEL", "19:44", "STANDARD"],
        ["ORD-142", "ZONA-01", "PREPARATION_STARTED", "MOTO", "19:52", "STANDARD"],
        ["ORD-204", "ZONA-03", "ASSIGN_DRIVER", "BICICLETA", "19:38", "PRIORITY-2"],
        ["ORD-240", "ZONA-02", "DISPATCHED", "MOTO", "19:29", "STANDARD"],
        ["ORD-402", "ZONA-04", "CONFIRMED", "AUTOMÓVEL", "20:05", "STANDARD"],
        ["ORD-420", "ZONA-03", "DISPATCHED", "MOTO", "19:36", "PRIORITY-1"],
    ]
    story.append(data_table(active_rows, [27 * mm, 26 * mm, 42 * mm, 30 * mm, 23 * mm, 31 * mm], ["LEFT", "LEFT", "LEFT", "LEFT", "CENTER", "LEFT"]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Observações da central", "H2Custom"))
    notes = [
        ["19:09", "ORD-041", "Aguardando retirada; não confundir com ORD-042."],
        ["19:10", "ORD-420", "Duplicidade detectada no evento de despacho."],
        ["19:12", "ORD-042", "Recalcular rota antes de confirmar previsão ao suporte."],
        ["19:14", "ORD-204", "Estado em revisão por chegada tardia de evento."],
    ]
    story.append(data_table([["Hora", "Pedido", "Nota"]] + notes, [24 * mm, 30 * mm, 115 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(
        p(
            "Os registros próximos foram incluídos para avaliar busca por identificador exato, filtragem por zona e resistência a similaridade lexical.",
            "Small",
        )
    )
    story.append(PageBreak())

    # Page 7
    story.extend(section("Contexto regional", "Operação da ZONA-03", "Visão agregada utilizada para priorização, sem informações de trânsito ou malha viária."))
    story.append(metric_cards([("9", "pedidos ativos"), ("4", "bicicletas"), ("3", "prioritários"), ("2", "alertas de dados")]))
    story.append(Spacer(1, 8 * mm))
    zone_rows = [
        ["Pedido", "Setor", "Estado", "Modal", "Slack até promessa"],
        ["ORD-024", "Z03-SUL", "CONFIRMED", "MOTO", "+25 min"],
        ["ORD-041", "Z03-NORTE", "READY_TO_PICKUP", "BICICLETA", "+20 min"],
        ["ORD-042", "Z03-NORTE", "DISPATCHED", "BICICLETA", "+17 min"],
        ["ORD-204", "Z03-CENTRO", "ASSIGN_DRIVER", "BICICLETA", "+23 min"],
        ["ORD-420", "Z03-NORTE", "DISPATCHED", "MOTO", "+21 min"],
    ]
    story.append(data_table(zone_rows, [29 * mm, 33 * mm, 43 * mm, 31 * mm, 33 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Nota de despacho", "H2Custom"))
    story.append(
        callout(
            "Reavaliação pendente",
            "ORD-042 foi marcado para reavaliação às 19:12. A central conhece o modal e a janela prometida, mas ainda precisa consultar malha, incidentes e políticas antes de recomendar uma rota.",
            SOFT_AMBER,
            AMBER,
        )
    )
    story.append(Spacer(1, 7 * mm))
    story.append(p("Limite semântico deste documento", "H2Custom"))
    story.append(
        p(
            "A expressão 'recalcular rota' não identifica uma alternativa. Recuperar este trecho sem consultar as outras fontes deve resultar em evidência insuficiente, não em uma escolha inventada.",
        )
    )
    story.append(PageBreak())

    # Page 8
    story.extend(section("Ruído controlado", "Histórico e versões", "Registros verdadeiros em seu contexto, porém inadequados para responder ao cenário atual."))
    historical_rows = [
        ["Referência", "Data", "Registro histórico", "Por que é distrator"],
        ["ORD-042", "02/08/2026", "Entrega concluída por moto na ZONA-01", "Mesmo ID reaproveitado em ambiente legado"],
        ["#8042", "05/08/2026", "Retirada no balcão", "Mesmo display_id em outro merchant"],
        ["ORD-024", "08/08/2026", "Promessa original 19:34", "Versão substituída pela v3"],
        ["ORD-420", "08/08/2026", "Dois despachos registrados", "Um único evento entregue duas vezes"],
        ["ORD-042", "08/08/2026", "Previsão preliminar 19:28", "Estimativa anterior ao despacho"],
    ]
    story.append(data_table(historical_rows, [27 * mm, 28 * mm, 59 * mm, 55 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Política de seleção temporal", "H2Custom"))
    version_rows = [
        ["Condição", "Ação"],
        ["Mesmo order_id, ambientes diferentes", "Filtrar environment = SIM-2026-A"],
        ["Mesmo display_id, merchants diferentes", "Priorizar order_id e merchant_id"],
        ["Múltiplos snapshots", "Selecionar maior version com effective_at válido"],
        ["Eventos repetidos", "Deduplicar por event_id"],
        ["Estimativas preliminares", "Não tratar como promessa contratual"],
    ]
    story.append(data_table(version_rows, [68 * mm, 101 * mm]))
    story.append(Spacer(1, 7 * mm))
    story.append(
        callout(
            "Teste esperado",
            "Uma consulta por 'pedido 8042' é ambígua. O sistema deve solicitar order_id ou merchant_id, em vez de combinar registros incompatíveis.",
            SOFT_RED,
            RED,
        )
    )
    story.append(PageBreak())

    # Page 9
    story.extend(section("Apêndice técnico", "Dicionário e metadados de ingestão", "Contrato mínimo para extração, chunking, rastreabilidade e avaliação."))
    dictionary_rows = [
        ["Campo", "Tipo", "Definição"],
        ["order_id", "string", "Identificador canônico do pedido no ambiente sintético"],
        ["event_id", "string", "Chave usada para deduplicação de eventos"],
        ["occurred_at", "datetime", "Momento em que o fato operacional ocorreu"],
        ["ingested_at", "datetime", "Momento em que o pipeline recebeu o evento"],
        ["effective_at", "datetime", "Início da validade de uma versão"],
        ["modal", "enum", "BICICLETA, MOTO ou AUTOMÓVEL"],
        ["priority", "enum", "STANDARD, PRIORITY-2 ou PRIORITY-1"],
        ["region", "string", "Zona operacional usada em filtros de recuperação"],
    ]
    story.append(data_table(dictionary_rows, [39 * mm, 32 * mm, 98 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Metadados recomendados por chunk", "H2Custom"))
    metadata_text = (
        "document_id=DOC-01; document_type=order_dossier; environment=SIM-2026-A; "
        "shift_date=2026-08-08; generated_at=2026-08-08T19:15:00-03:00; "
        "synthetic=true; language=pt-BR; version=0.1"
    )
    story.append(callout("Manifesto de ingestão", metadata_text))
    story.append(Spacer(1, 8 * mm))
    story.append(p("Critérios para o pipeline", "H2Custom"))
    criteria_rows = [
        ["Critério", "Expectativa"],
        ["Extração", "Texto pesquisável preservando títulos, tabelas e páginas"],
        ["Chunking", "Orientado por seção, com vínculo ao bloco pai"],
        ["Citação", "document_id, página, seção e trecho"],
        ["Privacidade", "Nenhum dado pessoal real no corpus"],
        ["Avaliação", "Gold chunks definidos fora do índice consultável"],
    ]
    story.append(data_table(criteria_rows, [48 * mm, 121 * mm]))
    story.append(Spacer(1, 8 * mm))
    story.append(
        p(
            "Fim do Documento 01. As demais fontes do corpus complementam este dossiê com malha, incidentes, políticas e critérios de SLA.",
            "Small",
        )
    )

    return story


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(
        str(OUTPUT),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=21 * mm,
        title="Dossiê Operacional de Pedidos - Documento 01",
        author="Last Mile RAG Lab",
        subject="Corpus sintético para experimento de RAG em logística",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=on_page)])
    doc.build(build_story())
    print(OUTPUT)


if __name__ == "__main__":
    main()
