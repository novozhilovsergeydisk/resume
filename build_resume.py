# -*- coding: utf-8 -*-
"""Генератор обновлённого резюме: PDF (reportlab) и DOCX (HTML + textutil)."""
import html
import re
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory
from xml.dom import minidom
from zipfile import ZipFile
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, HRFlowable)

FONTS_DIR = "/System/Library/Fonts/Supplemental/"
pdfmetrics.registerFont(TTFont("Arial", FONTS_DIR + "Arial.ttf"))
pdfmetrics.registerFont(TTFont("Arial-Bold", FONTS_DIR + "Arial Bold.ttf"))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold")
# Arial не содержит знак рубля (U+20BD) — берём его из Helvetica Neue
pdfmetrics.registerFont(TTFont("HN", "/System/Library/Fonts/HelveticaNeue.ttc",
                               subfontIndex=0))

SALARY_PDF = ("100 000 <font face=\"HN\">" + html.escape("₽") + "</font> на руки")

from PIL import Image, ImageDraw, ImageFont

OG_TITLE = "Новожилов Сергей Юрьевич — Web-разработчик / Full-stack"
SITE_SUMMARY = (
    "Разрабатываю веб-приложения от интерфейса и API до базы данных и развёртывания. "
    "Использую ИИ-инструменты для рефакторинга кода, анализа логов и подготовки "
    "технической документации."
)
OG_DESC = ("Web-разработчик / Full-stack разработчик, 19 лет опыта: PHP, PostgreSQL, Laravel, "
           "Linux-инфраструктура. Автоматизация процессов разработки с помощью ИИ "
           "(Claude, ChatGPT, Gemini, Kimi, Qwen).")
SITE_URL = "https://novozhilovsergeydisk.github.io/resume/"
SCREENSHOTS_PATH = "postgresql16/"
SCREENSHOTS_LABEL = "Скриншоты проекта"
SCREENSHOTS_LINK = (SCREENSHOTS_LABEL, SITE_URL + SCREENSHOTS_PATH)
APPUSE_LINK = ("appuse.ru", "https://appuse.ru/")


def make_favicon(path, size=256):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.22), fill="#0f151c")
    font = ImageFont.truetype(FONTS_DIR + "Arial Bold.ttf", int(size * 0.48))
    text = "НС"
    bbox = d.textbbox((0, 0), text, font=font)
    d.text(((size - (bbox[2] - bbox[0])) / 2 - bbox[0],
            (size - (bbox[3] - bbox[1])) / 2 - bbox[1]), text, font=font, fill="white")
    img.save(path)


def make_og(path):
    img = Image.new("RGB", (1200, 630), "#0f151c")
    d = ImageDraw.Draw(img)
    f_name = ImageFont.truetype(FONTS_DIR + "Arial Bold.ttf", 72)
    f_role = ImageFont.truetype(FONTS_DIR + "Arial Bold.ttf", 44)
    f_small = ImageFont.truetype(FONTS_DIR + "Arial.ttf", 34)
    d.rectangle([0, 0, 14, 630], fill="#2f9e63")
    d.text((70, 140), "Новожилов Сергей Юрьевич", font=f_name, fill="white")
    d.text((70, 250), "PHP-разработчик / Full-stack Developer", font=f_role, fill="#9fd4b8")
    d.text((70, 360), "19 лет опыта · PHP · PostgreSQL · Laravel", font=f_small, fill="#c8cfd6")
    d.text((70, 420), "Автоматизация процессов разработки с помощью ИИ", font=f_small,
           fill="#c8cfd6")
    d.text((70, 480), "Claude · ChatGPT · Gemini · Kimi · Qwen", font=f_small, fill="#8a94a0")
    img.save(path)

LINKS = [
    ("lan-install.online", "https://lan-install.online"),
    ("lan-install.ru", "https://lan-install.ru"),
    ("telepat.online", "https://telepat.online"),
    ("github.com/novozhilovsergeydisk/resume",
     "https://github.com/novozhilovsergeydisk/resume"),
    ("github.com/novozhilovsergeydisk", "https://github.com/novozhilovsergeydisk"),
    ("wishkey.ru", "https://wishkey.ru"),
    ("slavhol.ru", "http://slavhol.ru"),
    ("servicetrend.ru", "https://servicetrend.ru"),
    ("koderstudio.ru", "https://koderstudio.ru"),
    APPUSE_LINK,
    SCREENSHOTS_LINK,
    ("medsenger.ru", "https://medsenger.ru"),
    ("pg16-cert-prep", "https://github.com/novozhilovsergeydisk/pg16-cert-prep"),
    ("vox-platform", "https://github.com/novozhilovsergeydisk/vox-platform"),
    ("resume", "https://github.com/novozhilovsergeydisk/resume"),
]


def linkify(text, links=LINKS):
    pairs = sorted(links, key=lambda x: -len(x[0]))
    pattern = re.compile("|".join(re.escape(d) for d, _ in pairs))
    urls = dict(pairs)
    return pattern.sub(lambda m: f'<a href="{urls[m.group(0)]}">{m.group(0)}</a>', text)


# ---------------------------------------------------------------- данные ---
HEADER = {
    "name": "Новожилов Сергей Юрьевич",
    "lines": [
        "Мужчина, 63 года, родился 7 января 1963",
        "+7 (916) 3465407",
        "sergionov@mail.ru — предпочитаемый способ связи",
        "GitHub: github.com/novozhilovsergeydisk",
        "Код: pg16-cert-prep (подготовка к сертификации PostgreSQL) · vox-platform · "
        "resume (исходники этого сайта)",
        "Гражданство: Россия, есть разрешение на работу: Россия",
    ],
}

POSITION = {
    "title": "Web-разработчик / Full-stack разработчик",
    "salary": "100 000 ₽ на руки",
    "lines": [
        "Специализации: — Программист, разработчик",
        "Тип занятости: полная занятость",
        "Формат работы: на месте работодателя, удалённо, гибрид",
        "Желательное время в пути до работы: не имеет значения",
    ],
}

EXPERIENCE_TITLE = "Опыт работы — 19 лет 2 месяца"

JOBS = [
    {
        "company": "ООО «Телепат», telepat.online",
        "period": "Октябрь 2018 — настоящее время",
        "duration": "8 лет 8 месяцев",
        "location": "Москва",
        "industry": ("Информационные технологии, системная интеграция, интернет — "
                     "разработка программного обеспечения"),
        "position": "Программист — Разработчик PHP / Full-stack Developer",
        "bullets": [
            ("Аутсорс-разработка для заказчика от компании ООО «Телепат» (последний год): "
             "проект «Система управления заявками» (lan-install.online) — проектирование, "
             "разработка и развитие системы."),
            ("Интеграция «Системы управления заявками» со складом и сайтом "
             "«Монтаж оборудования и слаботочных систем» (lan-install.ru)."),
            ("Автоматизация процессов разработки с помощью систем искусственного интеллекта: "
             "Claude (Claude Code, Claude CLI), ChatGPT (Codex, Codex CLI), Gemini, Kimi K3 Pro, "
             "Qwen Code — генерация и рефакторинг кода, автоматизация рутинных задач, анализ "
             "логов и ускорение документирования."),
            ("Разработка и поддержка телемедицинской платформы medsenger.ru: проектирование "
             "архитектуры, реализация прикладной логики на PHP и интеграция с внешними API. "
             "Для аудио- и видеозвонков между врачом и пациентом команда использовала Node.js "
             "и WebRTC."),
            ("Поддержка и доработка старых проектов: рефакторинг кода, оптимизация "
             "производительности, устранение ошибок."),
            ("Администрирование серверной инфраструктуры на базе Linux (Ubuntu/Debian): "
             "настройка и обслуживание веб-серверов (Nginx/Apache), управление процессами, "
             "мониторинг, обеспечение отказоустойчивости и безопасности."),
            ("Настройка, развёртывание и поддержка корпоративного почтового сервера на основе "
             "iRedMail (Postfix, Dovecot, Roundcube, PostgreSQL в качестве бэкенда), включая "
             "конфигурацию TLS, DKIM, SPF, веб-интерфейсов администрирования."),
            ("Обеспечение стабильной и безопасной работы СУБД PostgreSQL: резервное копирование, "
             "оптимизация запросов."),
            ("Тесное взаимодействие с командой: участие в планировании задач, написание "
             "технической документации."),
        ],
    },
    {
        "company": "Софткей, ЗАО, softkey.ru",
        "period": "Октябрь 2015 — Октябрь 2018",
        "duration": "3 года 1 месяц",
        "location": "Москва",
        "industry": ("Информационные технологии, системная интеграция, интернет — "
                     "интернет-компания; розничная торговля — интернет-магазин"),
        "position": "PHP-разработчик",
        "bullets": [
            "доработка и поддержка основного проекта softkey.ru и региональных сайтов;",
            "поддержка проекта wishkey.ru;",
            "оптимизация и рефакторинг кода;",
            "написание SQL запросов, триггеров и хранимых процедур в СУБД Oracle;",
            "документирование выполненного функционала;",
            "разработка отдельных витрин для вендоров: Лаборатория Касперского, ООО «Эльдорадо» "
            "и др.;",
            "создание личных кабинетов для авторов программ с широким спектром настроек и "
            "ограничений: разделы аналитики, заказов, продуктов, а также личных кабинетов для "
            "сотрудников компании;",
            "написание функционала для выгрузки данных о продажах для руководства компании + "
            "аналитические выгрузки.",
        ],
    },
    {
        "company": "ООО «Славянские каникулы», slavhol.ru",
        "period": "Январь 2011 — Октябрь 2015",
        "duration": "4 года 10 месяцев",
        "location": "Москва",
        "industry": "",
        "position": "PHP программист",
        "bullets": [
            "разработка и поддержка сайта бронирования туров slavhol.ru;",
            "создание и продвижение сайтов премиального туризма (проект «Italymania»);",
            "разработка модулей общей системы сопровождения клиентов: учёт заявок на "
            "бронирование отелей, туров, билетов; регистрация звонков клиентов для колл-центра; "
            "система почтовой рассылки;",
            "отчёты и статистика продаж: клубная карта, ваучеры для путешествий, билеты, туры;",
            "модуль для заполнения и подачи документов в консульство: ноты, заявления на визы "
            "и другие.",
        ],
    },
    {
        "company": "ООО «Сервистренд», servicetrend.ru",
        "period": "Апрель 2008 — Март 2011",
        "duration": "3 года",
        "location": "Москва",
        "industry": ("Информационные технологии, системная интеграция, интернет — разработка "
                     "программного обеспечения; системная интеграция, автоматизация "
                     "технологических и бизнес-процессов предприятия, ИТ-консалтинг"),
        "position": "Специалист по внедрению систем автоматизации",
        "bullets": [
            "доработка и обновление нетиповых конфигураций бухгалтерских и складских программ "
            "компании 1С.",
        ],
    },
]

EDUCATION = {
    "title": "Образование",
    "degree": "Высшее",
    "lines": [
        "2011 — Московский технический университет связи и информатики, Москва",
        "Факультет вычислительные машины, комплексы, системы и сети; специальность "
        "«Вычислительные машины, комплексы, системы и сети»",
    ],
}

TRAINING = {
    "title": "Повышение квалификации, курсы",
    "items": [
        {
            "year": "2026",
            "org": "АНО ВО «Московский университет «Синергия»», Москва",
            "program": "Программа «Аналитик данных нового поколения: SQL, ИИ и Power BI», "
                       "в объёме 144 часов",
            "detail": "удостоверение о повышении квалификации, рег. № 162359 от 21.09.2026",
        },
        {
            "year": "2026",
            "org": "Сертификация PostgreSQL",
            "program": "Активная подготовка к сертификации",
            "detail": "",
        },
    ],
}

SKILLS = [
    "AI CLI-инструменты", "Claude Code", "Claude CLI", "ChatGPT Codex", "Codex CLI",
    "Gemini", "Kimi K3 Pro", "Qwen Code", "Node.js", "JavaScript", "HTML5", "CSS3",
    "PostgreSQL", "MySQL", "Oracle", "Power BI", "phpMyAdmin", "Git", "Docker", "Bash",
    "Ubuntu", "Debian", "Nginx", "Visual Studio Code", "Windsurf", "JetBrains PhpStorm",
    "PHP", "Laravel",
]

DRIVE = "Права категории B"

PRO_SKILLS_TITLE = "Профессиональные навыки"
PRO_SKILLS = [
    ("Применение ИИ в разработке: использую ИИ-инструменты для генерации и рефакторинга "
     "кода, анализа логов и подготовки технической документации. Работаю с Claude "
     "(Claude Code, Claude CLI), ChatGPT (Codex, Codex CLI), Gemini, Kimi K3 Pro и Qwen Code."),
    ("Node.js: разработка приложений, чат-сервисов и Telegram-ботов, опыт работы "
     "с аудио- и видеосвязью на WebRTC в Medsenger."),
    ("JavaScript и вёрстка: ES6+ (const/let, стрелочные функции, деструктуризация, "
     "модули import/export, async/await, Promise), HTML5 и CSS3."),
    ("Базы данных: уверенная работа с PostgreSQL (включая оптимизацию запросов, индексацию, "
     "репликацию, резервное копирование), а также опыт с MySQL и Oracle."),
    ("Серверная инфраструктура: настройка, развёртывание и поддержка веб-приложений на "
     "Ubuntu и Debian (включая Nginx/Apache, PHP-FPM, PostgreSQL, системные службы systemd, "
     "supervisor, безопасность fail2ban, ufw)."),
    ("Инструменты разработки: Windsurf, Visual Studio Code, JetBrains PhpStorm, Git и Bash."),
    ("Развиваю собственный проект Koder Studio (koderstudio.ru). Разрабатываю сайты "
     "и информационные системы, настраиваю серверную инфраструктуру."),
    ("Тренажёр для подготовки к сертификации по PostgreSQL 16 (appuse.ru): "
     "тренировки по темам, пробные экзамены и отслеживание прогресса. "
     + SCREENSHOTS_LABEL + "."),
    ("PHP и Laravel: понимание развития PHP от 5.3 до 8.x, включая пространства имён, "
     "анонимные функции, типизацию и JIT-компиляцию. Практический опыт работы с Laravel, "
     "понимание MVC-архитектуры, сервис-контейнера, middleware, очередей и событийной модели."),
]

QUALITIES_TITLE = "Личные качества"
QUALITIES = ("Самодисциплина, коммуникабельность, способность быстро включаться в работу. "
             "Стремление к постоянному профессиональному росту и применению современных "
             "IT-решений на практике — в том числе с использованием возможностей "
             "искусственного интеллекта для повышения эффективности разработки.")

UPDATED = "Резюме обновлено 20 ноября 2026"

# ------------------------------------------------------------- PDF-стили ---
def st(name, **kw):
    base = dict(fontName="Arial", fontSize=9.5, leading=13.5, alignment=TA_LEFT,
                textColor=colors.HexColor("#1a1a1a"), spaceAfter=0, spaceBefore=0)
    base.update(kw)
    return ParagraphStyle(name, **base)

S = {
    "name": st("name", fontName="Arial-Bold", fontSize=20, leading=24,
               textColor=colors.HexColor("#0f151c")),
    "hdr": st("hdr", fontSize=9.5, leading=13),
    "pos": st("pos", fontName="Arial-Bold", fontSize=13, leading=17,
              textColor=colors.HexColor("#0f151c")),
    "sec": st("sec", fontName="Arial-Bold", fontSize=12.5, leading=16,
              textColor=colors.HexColor("#0f151c"), spaceBefore=10, spaceAfter=2),
    "company": st("company", fontName="Arial-Bold", fontSize=10.5, leading=14,
                  textColor=colors.HexColor("#0f151c")),
    "meta": st("meta", fontSize=9, leading=12.5, textColor=colors.HexColor("#555f6b")),
    "posname": st("posname", fontName="Arial-Bold", fontSize=9.5, leading=13,
                  textColor=colors.HexColor("#333d47")),
    "bullet": st("bullet", fontSize=9.5, leading=13.5, leftIndent=10, bulletIndent=0,
                 spaceAfter=2.5),
    "chip": st("chip", fontSize=9.5, leading=13, textColor=colors.HexColor("#0f151c")),
    "foot": st("foot", fontSize=8, leading=11, textColor=colors.HexColor("#8a94a0"),
               spaceBefore=8),
}

def hr():
    return HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#c8cfd6"),
                      spaceBefore=1, spaceAfter=5)

def P(text, style="hdr"):
    return Paragraph(linkify(html.escape(text)), S[style])

# ------------------------------------------------------------------- PDF ---
def build_pdf(path):
    doc = SimpleDocTemplate(path, pagesize=A4, leftMargin=16*mm, rightMargin=16*mm,
                            topMargin=14*mm, bottomMargin=14*mm,
                            title="Новожилов Сергей Юрьевич — резюме",
                            author="Новожилов Сергей Юрьевич")
    el = []
    el.append(P(HEADER["name"], "name"))
    for ln in HEADER["lines"]:
        el.append(P(ln))
    el.append(Spacer(1, 6))
    el.append(hr())
    el.append(P(POSITION["title"], "pos"))
    el.append(Paragraph(SALARY_PDF, S["pos"]))
    for ln in POSITION["lines"]:
        el.append(P(ln))
    el.append(Spacer(1, 4))
    el.append(P(PRO_SKILLS_TITLE, "sec"))
    el.append(hr())
    for b in PRO_SKILLS:
        el.append(Paragraph("•&nbsp;&nbsp;" + linkify(html.escape(b)), S["bullet"]))
    el.append(Spacer(1, 4))
    el.append(P(EXPERIENCE_TITLE, "sec"))
    el.append(hr())
    for job in JOBS:
        el.append(P(job["company"], "company"))
        el.append(P(f'{job["period"]} · {job["duration"]} · {job["location"]}', "meta"))
        if job["industry"]:
            el.append(P(job["industry"], "meta"))
        el.append(P(job["position"], "posname"))
        el.append(Spacer(1, 2))
        for b in job["bullets"]:
            el.append(Paragraph("•&nbsp;&nbsp;" + linkify(html.escape(b)), S["bullet"]))
        el.append(Spacer(1, 6))
    el.append(P(EDUCATION["title"], "sec"))
    el.append(hr())
    el.append(P(EDUCATION["degree"], "posname"))
    for ln in EDUCATION["lines"]:
        el.append(P(ln))
    el.append(P(TRAINING["title"], "sec"))
    el.append(hr())
    for it in TRAINING["items"]:
        el.append(P(f'{it["year"]} — {it["org"]}', "posname"))
        el.append(P(it["program"]))
        if it["detail"]:
            el.append(P(it["detail"], "meta"))
    el.append(P("Навыки", "sec"))
    el.append(hr())
    el.append(P(" · ".join(SKILLS), "chip"))
    el.append(P("Опыт вождения", "sec"))
    el.append(hr())
    el.append(P(DRIVE))
    el.append(P(QUALITIES_TITLE, "sec"))
    el.append(hr())
    el.append(P(QUALITIES))
    el.append(Spacer(1, 10))
    el.append(hr())
    el.append(P(f'Новожилов Сергей · {UPDATED}', "foot"))
    doc.build(el)

# ------------------------------------------------------------------ HTML ---
def build_html(path, site=False):
    links = [*LINKS, (SCREENSHOTS_LABEL, SCREENSHOTS_PATH)] if site else [APPUSE_LINK, SCREENSHOTS_LINK]

    def e(s):
        return linkify(html.escape(s), links)

    out = []
    head = ['<!DOCTYPE html><html lang="ru"><head><meta charset="utf-8">']
    if site:
        head.append(f"<title>{html.escape(OG_TITLE)}</title>")
        head.append('<meta name="viewport" content="width=device-width, initial-scale=1">')
        head.append(f'<meta name="description" content="{html.escape(OG_DESC)}">')
        head.append('<meta property="og:type" content="profile">')
        head.append(f'<meta property="og:title" content="{html.escape(OG_TITLE)}">')
        head.append(f'<meta property="og:description" content="{html.escape(OG_DESC)}">')
        head.append(f'<meta property="og:url" content="{SITE_URL}">')
        head.append(f'<meta property="og:image" content="{SITE_URL}og-image.png">')
        head.append('<link rel="icon" type="image/png" href="favicon.png">')
    head.append("""<style>
body { font-family: Arial, sans-serif; font-size: 10pt; color: #1a1a1a; line-height: 1.35; }
.wrap { max-width: 800px; margin: 0 auto; padding: 28px 20px; }
h1 { font-size: 18pt; margin: 0 0 4pt 0; }
h2 { font-size: 12.5pt; margin: 12pt 0 3pt 0; border-bottom: 0.7pt solid #c8cfd6;
     padding-bottom: 2pt; }
.pos { font-size: 12pt; font-weight: bold; margin: 2pt 0; }
.company { font-weight: bold; font-size: 10.5pt; }
.meta { color: #555f6b; font-size: 9pt; margin: 1pt 0; }
ul { margin: 3pt 0 8pt 14pt; padding: 0; }
li { margin-bottom: 2pt; }
p { margin: 2pt 0; }
.skills { line-height: 1.6; }
.foot { color: #8a94a0; font-size: 8pt; margin-top: 10pt;
        border-top: 0.7pt solid #c8cfd6; padding-top: 3pt; }
</style>""")
    if site:
        head.append("""<style>
h1, h2, .pos, .company { color: #0f151c; }
h2 { border-bottom: 1.4pt solid #2f9e63; }
a { color: #1f7a4d; }
</style>""")
    head.append("</head>")
    out.append("".join(head))
    out.append("<body" + (" class='wrap'" if site else "") + ">")
    out.append(f"<h1>{e(HEADER['name'])}</h1>")
    for ln in HEADER["lines"]:
        out.append(f"<p>{e(ln)}</p>")
    if site:
        from urllib.parse import quote
        pdf_href = quote("Новожилов Сергей Юрьевич.pdf")
        out.append(f'<p>📄 <a href="{pdf_href}">Скачать резюме в PDF</a></p>')
    out.append("<h2>Желаемая должность и зарплата</h2>")
    out.append(f"<p class='pos'>{e(POSITION['title'])}</p>")
    if site:
        out.append(f"<p>{e(SITE_SUMMARY)}</p>")
    out.append(f"<p class='pos'>{e(POSITION['salary'])}</p>")
    for ln in POSITION["lines"]:
        out.append(f"<p>{e(ln)}</p>")
    out.append(f"<h2>{e(PRO_SKILLS_TITLE)}</h2><ul>")
    for b in PRO_SKILLS:
        out.append(f"<li>{e(b)}</li>")
    out.append("</ul>")
    out.append(f"<h2>{e(EXPERIENCE_TITLE)}</h2>")
    for job in JOBS:
        out.append(f"<p class='company'>{e(job['company'])}</p>")
        out.append(f"<p class='meta'>{e(job['period'])} · {e(job['duration'])} · "
                   f"{e(job['location'])}</p>")
        if job["industry"]:
            out.append(f"<p class='meta'>{e(job['industry'])}</p>")
        out.append(f"<p><b>{e(job['position'])}</b></p><ul>")
        for b in job["bullets"]:
            out.append(f"<li>{e(b)}</li>")
        out.append("</ul>")
    out.append(f"<h2>{e(EDUCATION['title'])}</h2>")
    out.append(f"<p><b>{e(EDUCATION['degree'])}</b></p>")
    for ln in EDUCATION["lines"]:
        out.append(f"<p>{e(ln)}</p>")
    out.append(f"<h2>{e(TRAINING['title'])}</h2>")
    for it in TRAINING["items"]:
        block = f"<b>{e(it['year'])} — {e(it['org'])}</b><br>{e(it['program'])}"
        if it["detail"]:
            block += f"<br><span class='meta'>{e(it['detail'])}</span>"
        out.append(f"<p>{block}</p>")
    out.append("<h2>Навыки</h2>")
    out.append(f"<p class='skills'>{e(' · '.join(SKILLS))}</p>")
    out.append("<h2>Опыт вождения</h2>")
    out.append(f"<p>{e(DRIVE)}</p>")
    out.append(f"<h2>{e(QUALITIES_TITLE)}</h2>")
    out.append(f"<p>{e(QUALITIES)}</p>")
    out.append(f"<p class='foot'>Новожилов Сергей · {e(UPDATED)}</p>")
    out.append("</body></html>")
    with open(path, "w", encoding="utf-8") as f:
        f.write("".join(out))


def add_docx_links(path, links):
    # textutil сохраняет внешний вид HTML-ссылок, но теряет их адреса.
    document_name = "word/document.xml"
    relationships_name = "word/_rels/document.xml.rels"
    with TemporaryDirectory(dir=Path(path).parent) as tempdir:
        output = Path(tempdir) / "resume.docx"
        with ZipFile(path) as source, ZipFile(output, "w") as target:
            document = minidom.parseString(source.read(document_name))
            relationships = minidom.parseString(source.read(relationships_name))
            runs = document.getElementsByTagName("w:r")
            for index, (label, url) in enumerate(links, 1):
                matches = [run for run in runs if any(
                    node.firstChild and node.firstChild.data == label
                    for node in run.getElementsByTagName("w:t")
                )]
                if len(matches) != 1:
                    raise ValueError(f"Не удалось однозначно найти ссылку в DOCX: {label}")
                run, = matches
                link_id = f"ResumeLink{index}"
                link = document.createElement("w:hyperlink")
                namespace = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
                link.setAttribute("xmlns:r", namespace)
                link.setAttribute("r:id", link_id)
                run.parentNode.replaceChild(link, run)
                link.appendChild(run)

                relationship = relationships.createElement("Relationship")
                relationship.setAttribute("Id", link_id)
                relationship.setAttribute("Type", namespace + "/hyperlink")
                relationship.setAttribute("Target", url)
                relationship.setAttribute("TargetMode", "External")
                relationships.documentElement.appendChild(relationship)

            target.writestr(document_name, document.toxml(encoding="UTF-8"))
            target.writestr(relationships_name, relationships.toxml(encoding="UTF-8"))
            for member in source.infolist():
                if member.filename not in (document_name, relationships_name):
                    target.writestr(member, source.read(member))
        output.replace(path)


if __name__ == "__main__":
    import os
    outdir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(outdir, "Новожилов Сергей Юрьевич.pdf")
    html_path = os.path.join(outdir, "resume.html")
    build_pdf(pdf_path)
    build_html(html_path)
    docx_path = os.path.join(outdir, "Новожилов Сергей Юрьевич.docx")
    subprocess.run(["textutil", "-convert", "docx", html_path, "-output", docx_path],
                   check=True)
    add_docx_links(docx_path, [APPUSE_LINK, SCREENSHOTS_LINK])
    os.remove(html_path)
    build_html(os.path.join(outdir, "index.html"), site=True)
    make_favicon(os.path.join(outdir, "favicon.png"))
    make_og(os.path.join(outdir, "og-image.png"))
    print("OK:")
    print(" ", pdf_path)
    print(" ", docx_path)
