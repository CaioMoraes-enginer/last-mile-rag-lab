from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "corpus" / "documents"

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
for style in [
    ParagraphStyle(name="CoverKicker", fontName="Arial-Bold", fontSize=9, leading=12, textColor=CYAN, tracking=1.8, spaceAfter=9),
    ParagraphStyle(name="CoverTitle", fontName="Arial-Bold", fontSize=30, leading=33, textColor=WHITE, spaceAfter=12),
    ParagraphStyle(name="CoverSubtitle", fontName="Arial", fontSize=11.5, leading=17, textColor=colors.HexColor("#C9D7DB"), spaceAfter=20),
    ParagraphStyle(name="SectionKicker", fontName="Arial-Bold", fontSize=7.5, leading=10, textColor=TEAL, tracking=1.2, spaceAfter=4),
    ParagraphStyle(name="H1Custom", fontName="Arial-Bold", fontSize=22, leading=26, textColor=INK, spaceAfter=8),
    ParagraphStyle(name="H2Custom", fontName="Arial-Bold", fontSize=13, leading=16, textColor=INK, spaceBefore=8, spaceAfter=6),
    ParagraphStyle(name="BodyCustom", fontName="Arial", fontSize=9.2, leading=13.5, textColor=INK, spaceAfter=7),
    ParagraphStyle(name="BodyBold", fontName="Arial-Bold", fontSize=9.2, leading=13.5, textColor=INK, spaceAfter=4),
    ParagraphStyle(name="Small", fontName="Arial", fontSize=7.5, leading=10.2, textColor=MUTED),
    ParagraphStyle(name="SmallDark", fontName="Arial", fontSize=7.5, leading=10.2, textColor=INK),
    ParagraphStyle(name="TableHeader", fontName="Arial-Bold", fontSize=7.5, leading=10.2, textColor=WHITE),
    ParagraphStyle(name="Callout", fontName="Arial", fontSize=9.4, leading=14, textColor=INK, leftIndent=8, rightIndent=8, spaceBefore=5, spaceAfter=5),
    ParagraphStyle(name="MetricValue", fontName="Arial-Bold", fontSize=19, leading=21, textColor=NAVY, alignment=TA_CENTER),
    ParagraphStyle(name="MetricLabel", fontName="Arial-Bold", fontSize=7, leading=9, textColor=MUTED, alignment=TA_CENTER),
]:
    styles.add(style)


def p(text, style="BodyCustom"):
    return Paragraph(text, styles[style])


def data_table(rows, widths, aligns=None):
    prepared = []
    for row_index, row in enumerate(rows):
        style = styles["TableHeader" if row_index == 0 else "SmallDark"]
        prepared.append([Paragraph(str(value), style) for value in row])
    table = Table(prepared, colWidths=widths, repeatRows=1, hAlign="LEFT")
    commands = [
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
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
    table = Table([[p(title, "BodyBold")], [p(body, "Callout")]], colWidths=[169 * mm])
    table.setStyle(
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
    return table


def metric_cards(metrics):
    cards = [[p(value, "MetricValue"), p(label.upper(), "MetricLabel")] for value, label in metrics]
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


def section(story, kicker, title, intro=None):
    story.extend([p(kicker.upper(), "SectionKicker"), p(title, "H1Custom")])
    if intro:
        story.append(p(intro))


def add_page(story, kicker, title, intro, blocks, final=False):
    section(story, kicker, title, intro)
    for block in blocks:
        story.append(block)
    if not final:
        story.append(PageBreak())


def decorator(doc_id, short_title, total_regular_pages):
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
            canvas.drawRightString(width - 15 * mm, height - 9.5 * mm, f"{doc_id}  |  {short_title}")
            canvas.setStrokeColor(LINE)
            canvas.setLineWidth(0.5)
            canvas.line(18 * mm, 15 * mm, width - 18 * mm, 15 * mm)
            canvas.setFont("Arial", 7)
            canvas.setFillColor(MUTED)
            canvas.drawString(18 * mm, 9.5 * mm, "Dado integralmente sintetico. Nao representa operacao, pedido ou pessoa real.")
            canvas.drawRightString(width - 18 * mm, 9.5 * mm, f"Pagina {page - 1} de {total_regular_pages}")
        canvas.restoreState()

    return on_page


def cover(story, doc_id, title, subtitle, window):
    story.extend(
        [
            Spacer(1, 38 * mm),
            p(f"{doc_id}  /  FONTE OPERACIONAL", "CoverKicker"),
            p(title, "CoverTitle"),
            p(subtitle, "CoverSubtitle"),
            Spacer(1, 12 * mm),
        ]
    )
    white_bold = ParagraphStyle("WhiteBold", parent=styles["BodyBold"], textColor=WHITE)
    meta = Table(
        [
            [p("JANELA ANALISADA", "Small"), p("VERSÃO", "Small"), p("CLASSIFICAÇÃO", "Small")],
            [Paragraph(window, white_bold), Paragraph("0.1", white_bold), Paragraph("SINTÉTICO / PÚBLICO", ParagraphStyle("WhiteTeal", parent=white_bold, textColor=CYAN))],
        ],
        colWidths=[56 * mm, 56 * mm, 56 * mm],
    )
    meta.setStyle(
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
    story.extend([meta, PageBreak()])


def build_pdf(filename, doc_id, title, short_title, subtitle, window, story, total_regular_pages=7):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output = OUTPUT_DIR / filename
    full_story = []
    cover(full_story, doc_id, title, subtitle, window)
    full_story.extend(story)
    doc = BaseDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=25 * mm,
        bottomMargin=21 * mm,
        title=title.replace("<br/>", " "),
        author="Last Mile RAG Lab",
        subject="Corpus sintético para experimento de RAG em logística",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="content")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorator(doc_id, short_title, total_regular_pages))])
    doc.build(full_story)
    print(output)


def document_02():
    story = []
    add_page(
        story,
        "Escopo da fonte",
        "Malha logística e candidatos de rota",
        "Catálogo versionado de nós, segmentos e rotas homologadas. Custos são tempos-base e não incorporam incidentes, clima ou permissões operacionais.",
        [
            callout("Separação de responsabilidades", "Este documento descreve onde é possível circular e quanto cada segmento custa em condições normais. Validade circunstancial e elegibilidade são resolvidas por outras fontes."),
            Spacer(1, 6 * mm),
            p("Candidatos homologados - ZONA-03", "H2Custom"),
            data_table(
                [
                    ["Rota", "Sequência", "Tempo-base", "Distância", "Controle"],
                    ["A", "O-B-D-X", "8 min", "3,8 km", "Padrão"],
                    ["B", "O-B-C-F-D-X", "14 min", "5,9 km", "Padrão"],
                    ["C", "O-B-C-E-X", "11 min", "4,4 km", "Inclui segmento controlado"],
                ],
                [22 * mm, 55 * mm, 29 * mm, 28 * mm, 35 * mm],
            ),
            Spacer(1, 8 * mm),
            callout("Importante", "O catálogo não afirma que uma rota está disponível agora. Uma rota homologada pode ficar inválida por bloqueio, janela temporal ou restrição de modal.", SOFT_AMBER, AMBER),
        ],
    )
    add_page(
        story,
        "Topologia",
        "Nós e segmentos da ZONA-03",
        "Recorte relevante da versão NET-Z03-12, efetiva desde 01/08/2026.",
        [
            data_table(
                [
                    ["Segmento", "Origem", "Destino", "Custo", "Classe", "Observação"],
                    ["SG-OB", "O", "B", "3 min", "LOCAL", "Acesso comum"],
                    ["SG-BD", "B", "D", "2 min", "EXPRESS", "Trecho da rota A"],
                    ["SG-DX", "D", "X", "3 min", "LOCAL", "Acesso comum"],
                    ["SG-BC", "B", "C", "3 min", "LOCAL", "Trecho de B e C"],
                    ["SG-CF", "C", "F", "4 min", "ARTERIAL", "Desvio convencional"],
                    ["SG-FD", "F", "D", "1 min", "LOCAL", "Reconexão com D"],
                    ["SG-CE", "C", "E", "2 min", "CT-BIKE", "Acesso controlado"],
                    ["SG-EX", "E", "X", "3 min", "LOCAL", "Saída alternativa"],
                ],
                [26 * mm, 18 * mm, 18 * mm, 22 * mm, 29 * mm, 56 * mm],
            ),
            Spacer(1, 8 * mm),
            callout("Limite da fonte", "SG-CE existe no grafo e reduz o custo da rota C. Este catálogo não informa quais pedidos estão autorizados a utilizá-lo."),
        ],
    )
    add_page(
        story,
        "Candidato A",
        "Rota A - caminho padrão",
        "Menor custo do mapa-base entre a origem O e o destino X.",
        [
            metric_cards([("8 min", "tempo-base"), ("3,8 km", "distância"), ("3", "segmentos"), ("0", "restrições no mapa")]),
            Spacer(1, 8 * mm),
            data_table(
                [["Ordem", "Segmento", "Trecho", "Custo acumulado"], ["1", "SG-OB", "O -> B", "3 min"], ["2", "SG-BD", "B -> D", "5 min"], ["3", "SG-DX", "D -> X", "8 min"]],
                [28 * mm, 40 * mm, 50 * mm, 51 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Limitação", "A rota A é ótima somente sob a hipótese de que todos os segmentos estejam disponíveis. SG-BD precisa ser validado contra boletins operacionais.", SOFT_RED, RED),
        ],
    )
    add_page(
        story,
        "Candidato B",
        "Rota B - desvio convencional",
        "Alternativa homologada que evita o segmento expresso SG-BD.",
        [
            metric_cards([("14 min", "tempo-base"), ("5,9 km", "distância"), ("5", "segmentos"), ("Padrão", "controle")]),
            Spacer(1, 8 * mm),
            data_table(
                [["Ordem", "Segmento", "Trecho", "Custo acumulado"], ["1", "SG-OB", "O -> B", "3 min"], ["2", "SG-BC", "B -> C", "6 min"], ["3", "SG-CF", "C -> F", "10 min"], ["4", "SG-FD", "F -> D", "11 min"], ["5", "SG-DX", "D -> X", "14 min"]],
                [28 * mm, 40 * mm, 50 * mm, 51 * mm],
            ),
            Spacer(1, 8 * mm),
            callout("Custo dinâmico", "O tempo-base não incorpora chuva, congestionamento ou fila operacional. Penalidades precisam ser recuperadas no Documento 03."),
        ],
    )
    add_page(
        story,
        "Candidato C",
        "Rota C - corredor controlado",
        "Alternativa curta que utiliza o segmento CT-BIKE SG-CE.",
        [
            metric_cards([("11 min", "tempo-base"), ("4,4 km", "distância"), ("4", "segmentos"), ("CT-BIKE", "controle")]),
            Spacer(1, 8 * mm),
            data_table(
                [["Ordem", "Segmento", "Trecho", "Custo acumulado"], ["1", "SG-OB", "O -> B", "3 min"], ["2", "SG-BC", "B -> C", "6 min"], ["3", "SG-CE", "C -> E", "8 min"], ["4", "SG-EX", "E -> X", "11 min"]],
                [28 * mm, 40 * mm, 50 * mm, 51 * mm],
            ),
            Spacer(1, 8 * mm),
            callout("Condição não resolvida", "A presença de SG-CE no mapa não concede acesso. O pipeline precisa verificar janela, modal e estado do pedido no Documento 04.", SOFT_AMBER, AMBER),
        ],
    )
    add_page(
        story,
        "Ruído controlado",
        "Rotas semelhantes em outras zonas",
        "Entradas reais dentro do ambiente sintético, mas incompatíveis com o pedido ORD-042.",
        [
            data_table(
                [
                    ["Versão", "Zona", "Rota", "Sequência", "Tempo", "Validade"],
                    ["NET-Z01-08", "ZONA-01", "C", "O-J-K-X", "9 min", "Atual"],
                    ["NET-Z02-11", "ZONA-02", "A", "O-B-G-X", "7 min", "Atual"],
                    ["NET-Z03-09", "ZONA-03", "C", "O-B-H-E-X", "16 min", "Revogada"],
                    ["NET-Z04-05", "ZONA-04", "B", "O-M-N-X", "12 min", "Atual"],
                    ["NET-Z03-12", "ZONA-03", "C", "O-B-C-E-X", "11 min", "Atual"],
                ],
                [31 * mm, 27 * mm, 20 * mm, 46 * mm, 22 * mm, 23 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Filtro obrigatório", "Rótulos A, B e C não são globais. Uma recuperação correta deve combinar zona e versão da malha, não apenas o nome da rota.", SOFT_RED, RED),
        ],
    )
    add_page(
        story,
        "Apêndice técnico",
        "Versões e metadados",
        "Contrato de ingestão para o catálogo da malha.",
        [
            data_table(
                [["Versão", "Efetiva desde", "Status", "Mudança"], ["NET-Z03-09", "10/07/2026", "REVOGADA", "Rota C via nó H"], ["NET-Z03-11", "25/07/2026", "REVOGADA", "Inclusão preliminar de SG-CE"], ["NET-Z03-12", "01/08/2026", "ATUAL", "SG-CE classificado como CT-BIKE"]],
                [37 * mm, 38 * mm, 34 * mm, 60 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Manifesto", "document_id=DOC-02; type=network_catalog; region=ZONA-03; version=NET-Z03-12; effective_at=2026-08-01; synthetic=true"),
            Spacer(1, 8 * mm),
            p("Critério de citação", "H2Custom"),
            p("Toda recomendação deve citar a página da rota e os segmentos utilizados. Custos ajustados devem citar também a fonte externa que alterou o peso do grafo."),
        ],
        final=True,
    )
    build_pdf("02-catalogo-da-malha-logistica.pdf", "DOC-02", "Catálogo da malha<br/>logística", "MALHA ZONA-03", "Nós, segmentos, custos-base e rotas homologadas para o ambiente simulado.", "VERSÃO EFETIVA 01 AGO 2026", story)


def document_03():
    story = []
    add_page(
        story,
        "Escopo da fonte",
        "Boletins do turno",
        "Eventos externos que alteram disponibilidade ou custo da malha logística.",
        [
            metric_cards([("17", "boletins"), ("6", "ativos"), ("4", "zonas"), ("3", "alta severidade")]),
            Spacer(1, 8 * mm),
            data_table(
                [["Boletim", "Zona", "Tipo", "Status", "Validade"], ["INC-Z03-042", "ZONA-03", "INTERDIÇÃO", "ATIVO", "18:40-21:30"], ["WTH-Z03-018", "ZONA-03", "CHUVA", "ATIVO", "18:55-20:10"], ["TRF-Z02-031", "ZONA-02", "CONGESTÃO", "ATIVO", "18:30-19:45"], ["INC-Z01-014", "ZONA-01", "ACIDENTE", "ENCERRADO", "17:50-18:35"]],
                [33 * mm, 27 * mm, 34 * mm, 29 * mm, 46 * mm],
            ),
            Spacer(1, 8 * mm),
            callout("Uso correto", "Boletins alteram pesos ou removem segmentos do grafo somente durante sua janela de validade e na zona especificada."),
        ],
    )
    add_page(
        story,
        "Incidente crítico",
        "Interdição do segmento B-D",
        "Boletim INC-Z03-042, versão 2.1, emitido pela central de operações.",
        [
            data_table(
                [["Campo", "Valor"], ["status", "ATIVO"], ["segment_id", "SG-BD"], ["origem -> destino", "B -> D"], ["bloqueio", "TOTAL / AMBOS OS SENTIDOS"], ["válido desde", "08/08/2026 18:40 BRT"], ["válido até", "08/08/2026 21:30 BRT"], ["modais afetados", "BICICLETA, MOTO, AUTOMÓVEL"], ["causa", "COLISÃO COM OBSTRUÇÃO DE VIA"]],
                [57 * mm, 112 * mm],
            ),
            Spacer(1, 8 * mm),
            callout("Consequência no grafo", "SG-BD deve ser removido de qualquer cálculo realizado entre 18:40 e 21:30. As rotas dependentes desse segmento precisam ser identificadas no catálogo da malha.", SOFT_RED, RED),
            Spacer(1, 7 * mm),
            p("Nota operacional", "H2Custom"),
            p("O desvio convencional indicado pela central é B-C-F-D. Corredores controlados não são avaliados por este boletim."),
        ],
    )
    add_page(
        story,
        "Condição dinâmica",
        "Chuva forte na ZONA-03",
        "Boletim WTH-Z03-018, emitido às 18:55 e válido até 20:10.",
        [
            data_table(
                [["Classe de segmento", "Penalidade", "Aplicação"], ["LOCAL", "+1 min por rota", "Todas as rotas da zona"], ["ARTERIAL", "+6 min por segmento", "Inclui SG-CF"], ["EXPRESS", "+2 min por segmento", "Se disponível"], ["CT-BIKE", "Sem ajuste adicional", "Corredor coberto"]],
                [50 * mm, 42 * mm, 77 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Impacto relevante", "SG-CF recebe penalidade de 6 minutos durante a validade deste boletim. O custo total das rotas dependentes precisa ser recalculado a partir do catálogo da malha.", SOFT_AMBER, AMBER),
            Spacer(1, 7 * mm),
            p("Limite da informação", "H2Custom"),
            p("O boletim climático não conhece pedidos, SLAs ou permissões de modal. Ele apenas publica penalidades para classes de segmento."),
        ],
    )
    add_page(
        story,
        "Distratores regionais",
        "Incidentes em outras zonas",
        "Boletins ativos no mesmo período, mas fora da ZONA-03.",
        [
            data_table(
                [["ID", "Zona", "Segmento", "Efeito", "Validade"], ["INC-Z01-019", "ZONA-01", "SG-JK", "Bloqueio total", "18:50-20:00"], ["TRF-Z02-031", "ZONA-02", "SG-BG", "+8 min", "18:30-19:45"], ["WTH-Z04-012", "ZONA-04", "Todos", "+3 min", "19:00-21:00"], ["INC-Z03-041", "ZONA-03", "SG-HJ", "Bloqueio parcial", "17:00-22:00"], ["INC-Z03-042", "ZONA-03", "SG-BD", "Bloqueio total", "18:40-21:30"]],
                [35 * mm, 28 * mm, 31 * mm, 37 * mm, 38 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Risco de recuperação", "Uma busca apenas por 'bloqueio B' pode trazer SG-BG da ZONA-02. Segmento, zona e validade precisam ser considerados juntos.", SOFT_RED, RED),
        ],
    )
    add_page(
        story,
        "Histórico",
        "Boletins encerrados e substituídos",
        "Informações semanticamente semelhantes que não podem alterar o grafo atual.",
        [
            data_table(
                [["ID", "Versão", "Status", "Conteúdo", "Encerrado"], ["INC-Z03-042", "1.0", "SUBSTITUÍDA", "Bloqueio parcial em SG-BD", "18:47"], ["INC-Z03-042", "2.0", "SUBSTITUÍDA", "Bloqueio total até 20:30", "19:02"], ["INC-Z03-042", "2.1", "ATUAL", "Bloqueio total até 21:30", "-"], ["WTH-Z03-011", "1.2", "ENCERRADA", "Chuva leve; +2 min em arterial", "17:40"]],
                [35 * mm, 25 * mm, 35 * mm, 51 * mm, 23 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Seleção temporal", "Para INC-Z03-042, a versão 2.1 substitui integralmente as versões 1.0 e 2.0. Recuperar a versão antiga produz uma janela incorreta."),
        ],
    )
    add_page(
        story,
        "Qualidade",
        "Atualizações e consistência",
        "Registro de ingestão dos boletins relevantes.",
        [
            data_table(
                [["Boletim", "occurred_at", "published_at", "ingested_at", "status"], ["INC-Z03-042 v1.0", "18:40", "18:43", "18:43:04", "OK"], ["INC-Z03-042 v2.0", "18:47", "18:48", "18:48:03", "OK"], ["INC-Z03-042 v2.1", "19:02", "19:03", "19:03:02", "OK"], ["WTH-Z03-018", "18:55", "18:56", "18:58:41", "ATRASO 2M41S"]],
                [42 * mm, 31 * mm, 32 * mm, 35 * mm, 29 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Regra", "Versões são ordenadas por effective_at e version. O atraso de ingestão não altera retroativamente a hora em que a condição começou."),
        ],
    )
    add_page(
        story,
        "Apêndice técnico",
        "Metadados de ingestão",
        "Contrato para recuperação de incidentes e condições ambientais.",
        [
            data_table(
                [["Campo", "Exemplo", "Uso"], ["bulletin_id", "INC-Z03-042", "Deduplicação"], ["region", "ZONA-03", "Filtro"], ["segment_ids", "[SG-BD]", "Atualização do grafo"], ["valid_from", "18:40", "Filtro temporal"], ["valid_until", "21:30", "Filtro temporal"], ["version", "2.1", "Resolução de conflito"], ["status", "ACTIVE", "Elegibilidade"]],
                [40 * mm, 54 * mm, 75 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Manifesto", "document_id=DOC-03; type=operational_bulletins; shift=2026-08-08-evening; version=0.1; synthetic=true"),
        ],
        final=True,
    )
    build_pdf("03-boletins-operacionais.pdf", "DOC-03", "Boletins<br/>operacionais", "TURNO 08 AGO 2026", "Incidentes, clima, congestionamentos, validade e histórico de versões.", "18:30 - 21:30 BRT", story)


def document_04():
    story = []
    add_page(
        story,
        "Escopo da fonte",
        "Políticas de acesso e modais",
        "Regras que determinam quando um pedido pode utilizar segmentos controlados.",
        [
            callout("Função no sistema", "O catálogo da malha registra a existência de um corredor. Este documento decide se o modal, o estado e o horário tornam o acesso elegível."),
            Spacer(1, 8 * mm),
            data_table(
                [["Classe", "Bicicleta", "Moto", "Automóvel", "Controle"], ["LOCAL", "PERMITIDO", "PERMITIDO", "PERMITIDO", "Aberto"], ["ARTERIAL", "PERMITIDO", "PERMITIDO", "PERMITIDO", "Aberto"], ["EXPRESS", "PERMITIDO", "PERMITIDO", "PERMITIDO", "Sujeito a incidente"], ["CT-BIKE", "CONDICIONAL", "NEGADO", "NEGADO", "Janela + estado"], ["SERVICE", "NEGADO", "CONDICIONAL", "CONDICIONAL", "Autorização" ]],
                [34 * mm, 33 * mm, 29 * mm, 33 * mm, 40 * mm],
            ),
        ],
    )
    add_page(
        story,
        "Política vigente",
        "Corredores CT-BIKE",
        "Política POL-MODAL-CT-3.0, efetiva desde 08/08/2026 às 17:00.",
        [
            data_table(
                [["Regra", "Condição"], ["modal", "BICICLETA"], ["estado do pedido", "DISPATCHED"], ["janela geral", "Conforme comunicado do corredor"], ["categoria", "DELIVERY"], ["autorização adicional", "Não exigida no ambiente SIM-2026-A"], ["evidência mínima", "modal + estado + corredor ativo"]],
                [58 * mm, 111 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Interpretação", "Bicicleta sozinha não é suficiente. Um pedido ainda em preparação não pode usar CT-BIKE, mesmo que o corredor esteja aberto.", SOFT_AMBER, AMBER),
        ],
    )
    add_page(
        story,
        "Comunicado de acesso",
        "Corredor C-E na ZONA-03",
        "Comunicado ACCESS-Z03-017, versão 3.0.",
        [
            data_table(
                [["Campo", "Valor"], ["segment_id", "SG-CE"], ["classe", "CT-BIKE"], ["origem -> destino", "C -> E"], ["válido em", "08/08/2026"], ["abre às", "18:00 BRT"], ["fecha às", "20:00 BRT"], ["modais", "Aplicar POL-MODAL-CT-3.0"], ["status às 19:15", "ATIVO"]],
                [57 * mm, 112 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Aplicação da regra", "Às 19:15, SG-CE está ativo. A elegibilidade de qualquer pedido ainda depende de consultar seu modal e estado na fonte operacional correspondente.", SOFT_TEAL, TEAL),
        ],
    )
    add_page(
        story,
        "Decisão de elegibilidade",
        "Matriz de casos",
        "Exemplos para impedir que a LLM generalize uma autorização.",
        [
            data_table(
                [["Caso", "Modal", "Estado", "Horário", "SG-CE"], ["CASE-01", "BICICLETA", "DISPATCHED", "19:15", "PERMITIDO"], ["CASE-02", "BICICLETA", "READY_TO_PICKUP", "19:15", "NEGADO"], ["CASE-03", "MOTO", "DISPATCHED", "19:15", "NEGADO"], ["CASE-04", "BICICLETA", "DISPATCHED", "20:05", "NEGADO"], ["CASE-05", "AUTOMÓVEL", "DISPATCHED", "18:45", "NEGADO"]],
                [29 * mm, 38 * mm, 45 * mm, 27 * mm, 30 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Regra formal", "eligible = modal == BICICLETA AND status == DISPATCHED AND 18:00 <= timestamp < 20:00", SOFT_AMBER, AMBER),
        ],
    )
    add_page(
        story,
        "Conflito de versões",
        "Políticas revogadas",
        "Versões antigas preservadas para auditoria, mas inválidas no horário do caso.",
        [
            data_table(
                [["Política", "Efetiva", "Status", "Regra CT-BIKE"], ["POL-MODAL-CT-1.0", "01/06/2026", "REVOGADA", "Todos os modais negados"], ["POL-MODAL-CT-2.0", "15/07/2026", "REVOGADA", "Bicicleta com autorização manual"], ["POL-MODAL-CT-2.1", "01/08/2026", "REVOGADA", "Bicicleta em qualquer estado"], ["POL-MODAL-CT-3.0", "08/08/2026 17:00", "ATUAL", "Bicicleta + DISPATCHED"]],
                [45 * mm, 42 * mm, 31 * mm, 51 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Armadilha documental", "A versão 1.0 afirma que bicicletas são proibidas. Um RAG sem filtro temporal pode recuperar essa regra e descartar incorretamente a rota C.", SOFT_RED, RED),
        ],
    )
    add_page(
        story,
        "Outras regiões",
        "Comunicados semelhantes",
        "Corredores temporários com códigos próximos, mas regras diferentes.",
        [
            data_table(
                [["Comunicado", "Zona", "Segmento", "Modal", "Janela"], ["ACCESS-Z01-017", "ZONA-01", "SG-JK", "MOTO", "17:00-19:00"], ["ACCESS-Z02-071", "ZONA-02", "SG-GH", "BICICLETA", "19:30-22:00"], ["ACCESS-Z03-017", "ZONA-03", "SG-CE", "BICICLETA", "18:00-20:00"], ["ACCESS-Z03-107", "ZONA-03", "SG-EH", "AUTOMÓVEL", "20:00-23:00"], ["ACCESS-Z04-017", "ZONA-04", "SG-MN", "MOTO", "18:00-21:00"]],
                [42 * mm, 28 * mm, 31 * mm, 34 * mm, 34 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Filtro obrigatório", "O número 017 aparece em três zonas. document_id, region e segment_id precisam permanecer associados durante chunking e recuperação."),
        ],
    )
    add_page(
        story,
        "Apêndice técnico",
        "Metadados e precedência",
        "Contrato para resolver política, comunicado e elegibilidade.",
        [
            data_table(
                [["Prioridade", "Fonte", "Função"], ["1", "Comunicado ativo", "Determina janela e segmento"], ["2", "Política vigente", "Determina modal e estado elegíveis"], ["3", "Dados do pedido", "Fornece modal, estado e timestamp"], ["4", "Política histórica", "Somente auditoria"]],
                [28 * mm, 58 * mm, 83 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Manifesto", "document_id=DOC-04; type=access_policy; policy=POL-MODAL-CT-3.0; notice=ACCESS-Z03-017; synthetic=true"),
        ],
        final=True,
    )
    build_pdf("04-politicas-de-acesso-e-modais.pdf", "DOC-04", "Políticas de acesso<br/>e modais", "POLÍTICA VIGENTE", "Permissões, janelas temporais, elegibilidade e histórico de versões.", "EFETIVA 08 AGO 2026 17:00", story)


def document_05():
    story = []
    add_page(
        story,
        "Escopo da fonte",
        "SLA e critérios de decisão",
        "Manual que transforma estado, previsão e evidências em prioridade e ação operacional.",
        [
            data_table(
                [["Classe", "Slack mínimo", "Severidade", "Ação"], ["STANDARD", "> 15 min", "NORMAL", "Monitorar"], ["ATTENTION", "8-15 min", "MÉDIA", "Recalcular e acompanhar"], ["AT_RISK", "1-7 min", "ALTA", "Selecionar alternativa válida"], ["BREACH", "<= 0 min", "CRÍTICA", "Escalar suporte"]],
                [39 * mm, 38 * mm, 37 * mm, 55 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Princípio", "A rota recomendada deve ser válida antes de ser rápida. Menor ETA não compensa bloqueio ou acesso não autorizado."),
        ],
    )
    add_page(
        story,
        "Cálculo",
        "Orçamento temporal",
        "Método utilizado para comparar alternativas no instante da decisão.",
        [
            callout("Fórmula", "slack_minutes = promised_at - decision_at - estimated_route_minutes", SOFT_AMBER, AMBER),
            Spacer(1, 8 * mm),
            data_table(
                [["Caso", "Decisão", "Promessa", "ETA candidato", "Slack"], ["CASE-SLA-101", "14:00", "14:30", "12 min", "+18 min"], ["CASE-SLA-102", "14:00", "14:18", "14 min", "+4 min"], ["CASE-SLA-103", "14:00", "14:17", "20 min", "-3 min"], ["CASE-SLA-104", "14:00", "14:08", "INVÁLIDO", "N/A"]],
                [40 * mm, 31 * mm, 34 * mm, 34 * mm, 30 * mm],
            ),
            Spacer(1, 8 * mm),
            p("Os casos acima são exemplos didáticos e não pertencem ao cenário principal do benchmark.", "Small"),
        ],
    )
    add_page(
        story,
        "Procedimento",
        "Seleção entre candidatos",
        "Algoritmo de decisão aplicado depois que validade e custo de cada alternativa foram calculados.",
        [
            data_table(
                [["Etapa", "Entrada", "Operação", "Saída"], ["1", "Candidatos", "Descartar alternativas inválidas", "Conjunto válido"], ["2", "Conjunto válido", "Ordenar por ETA ajustado", "Melhor candidato"], ["3", "Melhor candidato", "Calcular slack", "Classe de risco"], ["4", "Classe de risco", "Aplicar playbook", "Ação recomendada"]],
                [24 * mm, 45 * mm, 55 * mm, 45 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Regra de desempate", "Se dois candidatos válidos tiverem o mesmo ETA, priorizar maior slack previsto e depois menor número de segmentos controlados.", SOFT_TEAL, TEAL),
            Spacer(1, 7 * mm),
            p("A saída completa inclui validade, ETA, slack, risco e evidências. Este manual não contém o resultado do caso avaliado."),
        ],
    )
    add_page(
        story,
        "Ações",
        "Playbook de resposta",
        "Ações permitidas de acordo com a classificação final.",
        [
            data_table(
                [["Classificação", "Ação primária", "Ação secundária", "Reavaliação"], ["NORMAL", "Manter rota", "Registrar decisão", "5 min"], ["ATTENTION", "Recalcular", "Monitorar evento", "3 min"], ["AT_RISK", "Escolher melhor rota válida", "Notificar central", "2 min"], ["BREACH", "Escalar suporte", "Atualizar previsão", "Imediata"], ["INSUFFICIENT_EVIDENCE", "Não recomendar", "Solicitar fonte", "Após atualização"]],
                [43 * mm, 58 * mm, 43 * mm, 25 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Abstenção", "Se uma das restrições essenciais não puder ser comprovada, o sistema deve retornar INSUFFICIENT_EVIDENCE em vez de inventar uma rota."),
        ],
    )
    add_page(
        story,
        "Evidências",
        "Cobertura mínima para recomendação",
        "Conjunto de fatos que torna a decisão auditável.",
        [
            data_table(
                [["Dimensão", "Evidência exigida", "Fonte esperada"], ["Pedido", "modal, estado, promessa, região", "DOC-01"], ["Malha", "segmentos e custos-base", "DOC-02"], ["Dinâmica", "bloqueios e penalidades ativas", "DOC-03"], ["Acesso", "janela e elegibilidade", "DOC-04"], ["Decisão", "slack, classe e ação", "DOC-05"]],
                [37 * mm, 78 * mm, 54 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Cobertura completa", "Uma resposta só recebe pontuação máxima quando apresenta ao menos uma citação válida de cada dimensão necessária ao caso."),
        ],
    )
    add_page(
        story,
        "Distratores",
        "Regras históricas e casos semelhantes",
        "Políticas preservadas para testar versão, classe e categoria.",
        [
            data_table(
                [["Regra", "Status", "Conteúdo", "Risco"], ["SLA-2.1", "REVOGADA", "AT_RISK entre 1 e 10 min", "Classificação antiga"], ["SLA-3.0", "ATUAL", "AT_RISK entre 1 e 7 min", "Regra correta"], ["GROCERY-1.4", "ATUAL", "Tolerância extra de 5 min", "Categoria incompatível"], ["TAKEOUT-2.0", "ATUAL", "Sem cálculo de rota", "Modalidade incompatível"], ["Z01-EXCEPTION", "ATUAL", "Corredor prioritário automático", "Região incompatível"]],
                [38 * mm, 29 * mm, 59 * mm, 43 * mm],
            ),
            Spacer(1, 9 * mm),
            callout("Filtro necessário", "Categoria, modalidade e região do pedido precisam coincidir com o escopo da regra. Políticas de GROCERY, TAKEOUT ou outra zona não podem ser combinadas por similaridade textual.", SOFT_RED, RED),
        ],
    )
    add_page(
        story,
        "Apêndice técnico",
        "Saída estruturada",
        "Contrato mínimo esperado depois de recuperar e validar as fontes, sem incorporar o gabarito do benchmark.",
        [
            callout("Schema lógico", "order_id; route_id; valid; estimated_minutes; slack_minutes; risk_class; recommended_action; constraints_checked; citations; confidence"),
            Spacer(1, 8 * mm),
            data_table(
                [["Campo", "Tipo / restrição"], ["route_id", "string / candidato conhecido"], ["valid", "boolean"], ["estimated_minutes", "integer >= 0"], ["slack_minutes", "integer"], ["risk_class", "enum definido neste manual"], ["recommended_action", "enum definido no playbook"], ["citations", "array não vazio de evidências verificáveis"]],
                [60 * mm, 109 * mm],
            ),
            Spacer(1, 8 * mm),
            p("Manifesto", "H2Custom"),
            p("document_id=DOC-05; type=sla_decision_manual; policy=SLA-3.0; effective_at=2026-08-01; synthetic=true", "SmallDark"),
        ],
        final=True,
    )
    build_pdf("05-manual-de-sla-e-decisoes.pdf", "DOC-05", "Manual de SLA<br/>e decisões", "POLÍTICA SLA-3.0", "Critérios de validade, risco, priorização, abstenção e ação operacional.", "EFETIVA 01 AGO 2026", story)


def main():
    document_02()
    document_03()
    document_04()
    document_05()


if __name__ == "__main__":
    main()
