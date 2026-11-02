"""Build the management deck for the StarRocks 4.1.7 audit in the SKB brand style.

Usage: python3 build_deck.py <skill_dir> <hero_dir> <out.pptx>
"""
import sys

from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

SKILL, HERO, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
LOGO = f"{SKILL}/assets/logos/skb_logo.png"

BLACK = RGBColor(0x00, 0x00, 0x00)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x7F, 0x7F, 0x7F)
BLUE = RGBColor(0x08, 0x82, 0xFF)
BLUE_DARK = RGBColor(0x10, 0x32, 0xA1)
RED = RGBColor(0xF4, 0x24, 0x46)

TITLE = "SB Sans Display Semibold"
DISPLAY = "SB Sans Display"
LIGHT = "SB Sans Display Light"
TEXT = "SB Sans Text"
DRUK = "Druk Wide"  # digits/Latin only: the Trial build has no Cyrillic

FOOTER = "Аудит StarRocks 4.1.7 · черновик"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]
page = 0


def new_slide(logo=True, numbered=True):
    global page
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = BLACK
    page += 1
    if logo:
        s.shapes.add_picture(LOGO, Inches(10.93), Inches(0.15), Inches(2.25), Inches(1.63))
    if numbered:
        text(s, FOOTER, 0.55, 7.05, 6, 0.3, TEXT, 9, GRAY)
        text(s, str(page), 12.3, 7.05, 0.5, 0.3, TEXT, 9, GRAY, align=PP_ALIGN.RIGHT)
    return s


def text(s, value, x, y, w, h, font, size, color=WHITE, bold=False,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=None):
    """Text box. `value` is a str or a list of paragraphs, each a str or a list of (text, font, color) runs."""
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    paras = value if isinstance(value, list) else value.split("\n")
    for i, para in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        if spacing:
            p.space_after = Pt(spacing)
        runs = para if isinstance(para, list) else [(para, font, color)]
        for chunk, f, c in runs:
            r = p.add_run()
            r.text = chunk
            r.font.name = f
            r.font.size = Pt(size)
            r.font.color.rgb = c
            r.font.bold = bold
    return tb


def card(s, x, y, w, h, radius=0.07):
    """Dark brand card: light grey at ~10% opacity, no outline (as in the reference deck)."""
    sh = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    sh.adjustments[0] = radius
    sh.fill.solid()
    sh.fill.fore_color.rgb = RGBColor(0xB5, 0xB5, 0xB5)
    clr = sh.fill._xPr.find(qn("a:solidFill")).find(qn("a:srgbClr"))
    etree.SubElement(clr, qn("a:alpha")).set("val", "10000")
    sh.line.fill.background()
    sh.shadow.inherit = False
    return sh


def title(s, value):
    text(s, value, 0.55, 0.5, 10.1, 1.0, TITLE, 32)


def picture(s, path, x, y, w=None, h=None):
    kw = {}
    if w:
        kw["width"] = Inches(w)
    if h:
        kw["height"] = Inches(h)
    return s.shapes.add_picture(path, Inches(x), Inches(y), **kw)


def table(s, rows, x, y, widths, row_h, accent_col):
    """Brand table: no cell fills, grey dividers, one solid blue accent column."""
    gs = s.shapes.add_table(len(rows), len(widths), Inches(x), Inches(y),
                            Inches(sum(widths)), Inches(row_h * len(rows)))
    tbl = gs.table
    tblPr = tbl._tbl.tblPr
    for attr in ("firstRow", "bandRow"):
        tblPr.set(attr, "0")
    style = tblPr.find(qn("a:tableStyleId"))
    if style is not None:
        tblPr.remove(style)
    for ci, wd in enumerate(widths):
        tbl.columns[ci].width = Inches(wd)
    for ri, row in enumerate(rows):
        tbl.rows[ri].height = Inches(row_h)
        for ci, val in enumerate(row):
            cell = tbl.cell(ri, ci)
            accent = ci == accent_col
            if accent:
                cell.fill.solid()
                cell.fill.fore_color.rgb = BLUE
            else:
                cell.fill.background()
            cell.margin_left = cell.margin_right = Inches(0.12)
            cell.margin_top = cell.margin_bottom = Inches(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            r = p.add_run()
            r.text = val
            r.font.name = TITLE if ri == 0 or accent else TEXT
            r.font.size = Pt(13 if ri == 0 else 12)
            r.font.color.rgb = WHITE
            r.font.bold = False
            tcPr = cell._tc.get_or_add_tcPr()
            for side in ("a:lnL", "a:lnR", "a:lnT", "a:lnB"):
                ln = etree.SubElement(tcPr, qn(side))
                if side == "a:lnB" or (side == "a:lnT" and ri == 0):
                    ln.set("w", str(Pt(0.75)))
                    fill = etree.SubElement(ln, qn("a:solidFill"))
                    etree.SubElement(fill, qn("a:srgbClr")).set("val", "7F7F7F")
                else:
                    etree.SubElement(ln, qn("a:noFill"))
    return tbl


# 1. Cover -------------------------------------------------------------------
s = new_slide(logo=False, numbered=False)
picture(s, f"{HERO}/s1_Рисунок_3.png", 5.6, 0.75, w=7.7)
picture(s, LOGO, 0.55, 0.4, w=2.0)
text(s, "Аудит безопасности\nСУБД StarRocks 4.1.7", 0.55, 2.55, 6.2, 1.9, TITLE, 40)
text(s, "Соответствие корпоративному стандарту КБ\nпо требованиям 2.1–5.6", 0.55, 4.55, 6.6, 0.8, TEXT, 16)
pill = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.55), Inches(5.75), Inches(2.9), Inches(0.38))
pill.adjustments[0] = 0.5
pill.fill.solid()
pill.fill.fore_color.rgb = BLUE
pill.line.fill.background()
pill.shadow.inherit = False
pt = pill.text_frame
pt.margin_top = pt.margin_bottom = 0
r = pt.paragraphs[0].add_run()
r.text = "Черновик · ноябрь 2026"
r.font.name, r.font.size, r.font.color.rgb = TITLE, Pt(13), WHITE
pt.paragraphs[0].alignment = PP_ALIGN.CENTER
text(s, "Материалы для владельца риска КБ", 0.55, 6.35, 6.6, 0.4, TEXT, 14, GRAY)

# 2. Verdict (big statement) -------------------------------------------------
s = new_slide()
text(s, [
    [("StarRocks 4.1.7 в конфигурации по умолчанию ", LIGHT, WHITE),
     ("не соответствует", TITLE, BLUE), (" стандарту.", LIGHT, WHITE)],
    [("Эксплуатация допустима ", LIGHT, WHITE), ("только как принятый риск КБ.", TITLE, WHITE)],
    [("Защиту прикладных данных от администраторов СУБД ", LIGHT, WHITE),
     ("в текущей архитектуре обеспечить нельзя", TITLE, BLUE),
     (" — риск снижается, но не устраняется.", LIGHT, WHITE)],
], 0.55, 1.9, 10.3, 4.8, LIGHT, 32, spacing=20)

# 3. Scope and method --------------------------------------------------------
s = new_slide()
title(s, "Объект и метод аудита")
cards = [
    ("объект", "4.1.7", "StarRocks, тег от 22.10.2026",
     "Commit b81ff9cc. Shared-nothing — исходный код и стенд; shared-data — исходный код, частично."),
    ("критериев", "76", "атомарных проверок по стандарту",
     "Каждое требование 2.1–5.6 разложено на проверяемые критерии и прослежено до кода и теста."),
    ("тестов на стенде", "29", "воспроизводимых проверок",
     "Изолированный Docker-стенд, синтетические данные. Проверены и недостатки, и меры защиты."),
]
for i, (label, stat, sub, body) in enumerate(cards):
    x = 0.55 + i * 4.1
    card(s, x, 1.85, 3.9, 4.85)
    text(s, label, x + 0.35, 2.15, 3.2, 0.3, TEXT, 11, GRAY)
    text(s, stat, x + 0.35, 2.6, 3.3, 1.0, DRUK, 54, BLUE, bold=True)
    text(s, sub, x + 0.35, 3.85, 3.2, 0.7, TITLE, 15)
    text(s, body, x + 0.35, 4.7, 3.2, 1.8, TEXT, 12)

# 4. RTM results (bars) ------------------------------------------------------
s = new_slide()
title(s, "Результат по 76 критериям стандарта")
bars = [("Соответствует", 12), ("При\nусловиях", 15), ("Не\nсоответствует", 17),
        ("Не\nподдерживается", 11), ("Не\nподтверждено", 5), ("Эксплуатац.\nпроверка", 16)]
base, top, maxv = 5.75, 2.3, 17
for i, (label, v) in enumerate(bars):
    x = 0.75 + i * 1.3
    h = (base - top) * v / maxv
    bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(base - h), Inches(0.95), Inches(h))
    bar.line.fill.background()
    bar.shadow.inherit = False
    bar.fill.gradient()
    bar.fill.gradient_angle = 90
    stops = bar.fill.gradient_stops
    stops[0].color.rgb, stops[0].position = BLUE, 0
    stops[1].color.rgb, stops[1].position = BLUE_DARK, 1.0
    text(s, str(v), x - 0.2, base - h - 0.62, 1.35, 0.55, DRUK, 24, WHITE, bold=True, align=PP_ALIGN.CENTER)
    text(s, label, x - 0.13, base + 0.15, 1.21, 0.7, TEXT, 10, WHITE, align=PP_ALIGN.CENTER)
card(s, 8.85, 2.3, 3.95, 4.3)
text(s, "28", 9.2, 2.6, 3.3, 0.9, DRUK, 48, BLUE, bold=True)
text(s, "критериев не соответствуют или механизм отсутствует в продукте", 9.2, 3.55, 3.3, 0.8, TITLE, 14)
text(s, "27", 9.2, 4.5, 3.3, 0.9, DRUK, 48, BLUE, bold=True)
text(s, "соответствуют, из них 15 — только при выполнении условий", 9.2, 5.45, 3.3, 0.8, TITLE, 14)
text(s, "Доля проверенных критериев — показатель охвата аудита, а не уровня защищённости.",
     0.55, 6.6, 8.0, 0.35, TEXT, 10, GRAY)

# 5. Section divider ---------------------------------------------------------
s = new_slide(numbered=False)
picture(s, f"{HERO}/s8_Рисунок_6.png", 5.8, 1.9, w=7.0)
text(s, "Ключевые\nриски", 0.55, 4.3, 6.5, 2.6, DISPLAY, 80, bold=True)

# 6. Risk categories (threat variant) ---------------------------------------
s = new_slide()
picture(s, f"{HERO}/s3_Рисунок_5.png", 6.9, 2.3, w=6.43)
title(s, "Четыре группы рисков")
risks = [
    ("ДОСТУП АДМИНИСТРАТОРОВ К ДАННЫМ",
     "Встроенные роли root, db_admin и user_admin имеют прямой или косвенный доступ к прикладным данным",
     "4.5 · F-01, F-02, F-04"),
    ("СЛУЖЕБНЫЕ ФУНКЦИИ ПО УМОЛЧАНИЮ",
     "Отладочные и служебные возможности включены и расширяют полномочия администраторов",
     "3.3, 4.1, 4.5 · F-03, F-11"),
    ("АУТЕНТИФИКАЦИЯ",
     "Нет парольной политики и блокировки учётных записей; пустой пароль root после установки",
     "4.2, 4.8 · F-04, F-05"),
    ("ЗАЩИТА КАНАЛОВ И АУДИТ",
     "Межузловые каналы без TLS; часть HTTP-интерфейсов без аутентификации; аудит неполон",
     "2.4, 4.3, 5.1 · F-06, F-07, F-09"),
]
for i, (label, body, ref) in enumerate(risks):
    y = 1.75 + i * 1.3
    card(s, 0.55, y, 6.2, 1.18)
    text(s, label, 0.8, y + 0.14, 5.8, 0.3, TITLE, 13, RED)
    text(s, body, 0.8, y + 0.45, 5.8, 0.5, TEXT, 11.5)
    text(s, ref, 0.8, y + 0.86, 5.8, 0.25, TEXT, 9.5, GRAY)

# 7. Admin roles vs data access ---------------------------------------------
s = new_slide()
title(s, "Административные роли и доступ к данным")
table(s, [
    ["Роль", "Назначение", "Доступ к прикладным данным"],
    ["root (встроенная)", "Аварийный доступ", "Да — полный, ограничить нельзя"],
    ["db_admin (встроенная)", "Администрирование объектов БД", "Да — напрямую"],
    ["user_admin (встроенная)", "Управление учётными записями", "Да — через выдачу прав себе"],
    ["security_admin (встроенная)", "Безопасность и конфигурация", "Да — до отключения служебных функций"],
    ["cluster_admin (встроенная)", "Узлы кластера", "Не подтверждено"],
    ["«DBA без данных» (своя роль)", "Администрирование схемы", "Нет — проверено 12 путей"],
], 0.55, 1.85, [3.6, 4.1, 4.4], 0.55, accent_col=2)
text(s, "Своя роль «DBA без данных» не читает данные, но видит часть метаданных и может изменять схему (F-14).",
     0.55, 6.05, 12.0, 0.4, TEXT, 11, GRAY)

# 8. Verified mitigations ----------------------------------------------------
s = new_slide()
title(s, "Меры защиты проверены на стенде")
table(s, [
    ["Мера", "Требование", "Результат проверки"],
    ["Обязательный TLS для клиентских подключений", "2.4", "Работает; localhost — исключение"],
    ["Аутентификация HTTP-интерфейсов FE и BE", "4.3, 5.5", "Работает"],
    ["Отключение служебных скриптов FE", "4.1, 4.5", "Работает"],
    ["Аудит входов и неуспешных попыток", "5.1", "Работает; выход не регистрируется"],
    ["Своя роль «DBA без данных»", "4.5", "Работает; остаются метаданные"],
], 0.55, 1.85, [6.2, 1.9, 4.0], 0.6, accent_col=2)
text(s, "Профиль настроек — в полном отчёте, §11.2. Не проверены на целевой конфигурации: шифрование межузлового трафика, "
     "отзыв прав в открытой сессии.", 0.55, 5.75, 12.0, 0.6, TEXT, 11, GRAY)

# 9. Unremovable limitations ------------------------------------------------
s = new_slide()
title(s, "Что не устраняется настройкой продукта")
limits = [
    ("01", "Встроенные роли видят данные",
     "root, db_admin и user_admin неизменяемы и сохраняют доступ к прикладным данным", "4.5"),
    ("02", "Нет парольной политики",
     "Длина, срок действия и блокировка учётных записей не поддерживаются", "4.8, 5.1"),
    ("03", "Межузловые каналы без TLS",
     "Внутренние протоколы кластера не шифруются, узлы не аутентифицируют друг друга", "2.4"),
    ("04", "Пробелы штатного аудита",
     "Нет события выхода пользователя и атрибута «приложение»", "5.1, 5.2"),
]
for i, (num, head, body, req) in enumerate(limits):
    x = 0.55 + (i % 2) * 6.15
    y = 1.85 + (i // 2) * 2.3
    card(s, x, y, 5.95, 2.1)
    text(s, num, x + 0.35, y + 0.3, 1.4, 0.8, DRUK, 36, BLUE, bold=True)
    text(s, head, x + 1.8, y + 0.32, 3.9, 0.4, TITLE, 16)
    text(s, body, x + 1.8, y + 0.8, 3.9, 0.9, TEXT, 12)
    text(s, f"Требование {req}", x + 1.8, y + 1.65, 3.9, 0.3, TEXT, 10, GRAY)
text(s, "Компенсация — только внешними мерами: PAM, DAM, сетевая сегментация, внешняя аутентификация — или исправлениями вендора.",
     0.55, 6.5, 12.0, 0.35, TEXT, 11, GRAY)

# 10. Conditions for acceptable use -----------------------------------------
s = new_slide()
picture(s, f"{HERO}/s16_Рисунок_5.png", 8.3, 2.3, w=4.9)
title(s, "Условия допустимости эксплуатации")
conditions = [
    "Применён и проверен профиль безопасной конфигурации",
    "Встроенные административные роли не выдаются людям; root — только аварийный доступ через PAM",
    "Кластер в изолированном сегменте, межузловой трафик шифруется инфраструктурой",
    "Привилегированные учётные записи — через PAM с записью сессий; установлен DAM",
    "Аутентификация пользователей через СУДИР/LDAP по защищённому каналу",
    "Аудит в реальном времени доставляется в ПКБ, настроены правила на действия администраторов",
    "Риски по F-01, F-03, F-05, F-09 заведены и приняты в установленном порядке",
]
for i, c in enumerate(conditions):
    y = 1.8 + i * 0.7
    text(s, str(i + 1), 0.55, y - 0.04, 0.55, 0.5, DRUK, 20, BLUE, bold=True)
    text(s, c, 1.2, y, 6.9, 0.6, TEXT, 13)

# 11. Decision for the risk owner -------------------------------------------
s = new_slide()
title(s, "Решение владельца риска")
decisions = [
    ("принять риск", "2.1", "Оформить риск КБ по п. 2.1",
     "Типовой риск — доступ с повышенными привилегиями; мероприятия по минимизации и принятие владельцем АС/ФП."),
    ("не размещать", "PCI DSS", "Данные карт и финансовых АС",
     "Без исправлений вендора по F-01, F-05, F-07, F-09 соответствие для этих зон не достигается."),
    ("запросить у вендора", "6", "исправлений в продукте",
     "Разделение ролей, парольная политика, полный аудит, TLS межузлового трафика и безопасные значения по умолчанию."),
]
for i, (label, stat, sub, body) in enumerate(decisions):
    x = 0.55 + i * 4.1
    card(s, x, 1.85, 3.9, 4.85)
    text(s, label, x + 0.35, 2.15, 3.2, 0.3, TEXT, 11, GRAY)
    text(s, stat, x + 0.35, 2.6, 3.3, 1.0, DRUK, 34 if len(stat) > 3 else 54, BLUE, bold=True,
         anchor=MSO_ANCHOR.BOTTOM)
    text(s, sub, x + 0.35, 3.85, 3.2, 0.7, TITLE, 15)
    text(s, body, x + 0.35, 4.7, 3.2, 1.8, TEXT, 12)

# 12. Thank you --------------------------------------------------------------
s = new_slide(numbered=False)
picture(s, f"{HERO}/s17_Рисунок_3.png", 6.3, 1.9, w=6.9)
text(s, "Спасибо!", 0.55, 3.0, 7.0, 1.6, DISPLAY, 96, bold=True)
text(s, "Полный отчёт, матрица требований и доказательства —\nв материалах аудита (каталог audit/)",
     0.55, 4.9, 6.5, 0.9, TEXT, 15)

prs.core_properties.title = "Аудит безопасности СУБД StarRocks 4.1.7"
prs.save(OUT)
print("saved", OUT, "slides:", len(prs.slides))
