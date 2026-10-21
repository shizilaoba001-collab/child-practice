"""Deterministic A4 renderer. No remote resources, no machine font paths."""
import math
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader

FONT = 'LearningSerifSC'
PAGE_W, PAGE_H = A4
LEFT, RIGHT, BOTTOM = 38, PAGE_W - 38, 42


def setup():
    if FONT not in pdfmetrics.getRegisteredFontNames():
        path = Path(__file__).resolve().parents[1] / 'assets/fonts/LearningSerifSC.ttf'
        pdfmetrics.registerFont(TTFont(FONT, str(path)))


def check_text(text):
    cmap = pdfmetrics.getFont(FONT).face.charToGlyph
    missing = sorted({ch for ch in text if not ch.isspace() and ord(ch) not in cmap})
    if missing:
        raise ValueError('字体缺字：' + ''.join(missing))


def text(c, x, y, s, size=13):
    check_text(str(s))
    c.setFillColorRGB(0, 0, 0)
    c.setFont(FONT, size)
    c.drawString(x, y, str(s))


def wrapped(s, width, size):
    lines = []
    line = ''
    for ch in str(s):
        if ch == '\n':
            lines.append(line)
            line = ''
        elif pdfmetrics.stringWidth(line + ch, FONT, size) > width and line and ch not in '，。？！、；：）”：':
            lines.append(line)
            line = ch
        else:
            line += ch
    if line:
        lines.append(line)
    return lines


def paragraph(c, y, s, size=13, leading=21):
    for line in wrapped(s, RIGHT - LEFT, size):
        if y < BOTTOM:
            raise ValueError('孩子页文字溢出，请减少本页内容或合理分配页面')
        text(c, LEFT, y, line, size)
        y -= leading
    return y


def header(c, label, title, issued, page, count):
    text(c, LEFT, 804, label + '｜' + title, 20)
    text(c, LEFT, 774, issued + '     姓名：____________', 11)
    text(c, RIGHT - 30, 25, (str(page) if count == '?' else str(page) + '/' + str(count)), 10)
    return 732


def block(c, y, data):
    kind = data['type']
    if kind == 'text':
        return paragraph(c, y, data['text'], data.get('size', 14), data.get('leading', 23)) - 5
    if kind == 'blank':
        lines = data.get('lines', 1)
        if not 1 <= lines <= 6:
            raise ValueError('blank.lines须1—6')
        for _ in range(lines):
            c.setLineWidth(.5)
            c.line(LEFT, y - 15, RIGHT, y - 15)
            y -= 34
        return y
    if kind == 'ruby':
        # Units may be one character or a short token; readings are authored, never guessed here.
        x = LEFT
        y -= 14
        for unit in data['units']:
            s, py = unit['text'], unit.get('pinyin', '')
            check_text(s + py)
            width = max(22, pdfmetrics.stringWidth(s, FONT, 14) + 8,
                        pdfmetrics.stringWidth(py, FONT, 8.5) + 5)
            if width > RIGHT - LEFT:
                raise ValueError('单个注音单元太宽，请拆成字或短词')
            if x + width > RIGHT:
                x = LEFT
                y -= 42
            c.setFont(FONT, 14)
            c.drawCentredString(x + width / 2, y, s)
            if py:
                c.setFont(FONT, 8.5)
                c.drawCentredString(x + width / 2, y + 18, py)
            x += width
        return y - 30
    if kind == 'copy_grid':
        chars, copies = data['characters'], data['copies_each']
        size = 31
        if not 1 <= copies <= 5:
            raise ValueError('临写遍数须1—5')
        cols = 2 if (copies + 1) * size * 2 + 24 < RIGHT - LEFT else 1
        for i, ch in enumerate(chars):
            check_text(ch)
            x = LEFT + (i % cols) * (RIGHT - LEFT) / cols
            yy = y - (i // cols) * 49 - size
            for j in range(copies + 1):
                xx = x + j * size
                c.setStrokeColorRGB(.55, .55, .55)
                c.setLineWidth(.5)
                c.setDash()
                c.rect(xx, yy, size, size)
                c.setDash(2, 2)
                c.line(xx + size / 2, yy, xx + size / 2, yy + size)
                c.line(xx, yy + size / 2, xx + size, yy + size / 2)
            c.setDash()
            text(c, x + 3, yy + 5, ch, 25)
        return y - math.ceil(len(chars) / cols) * 49 - 8
    if kind == 'table':
        rows = data['rows']
        if not rows or not rows[0] or any(len(r) != len(rows[0]) for r in rows):
            raise ValueError('表格须为规则矩形')
        width = (RIGHT - LEFT) / len(rows[0])
        for i, row in enumerate(rows):
            for j, value in enumerate(row):
                if pdfmetrics.stringWidth(str(value), FONT, 12) > width - 12:
                    raise ValueError('表格文字太长，请拆分')
                yy = y - 31 * (i + 1)
                c.setDash()
                c.rect(LEFT + j * width, yy, width, 31)
                text(c, LEFT + j * width + 6, yy + 9, value, 12)
        return y - 31 * len(rows) - 15
    if kind == 'diagram':
        height = data.get('height', 90)
        if not 20 <= height <= 250:
            raise ValueError('图示高度须20—250')
        for obj in data['objects']:
            typ = obj['type']
            x, yy = obj.get('x', 0), obj.get('y', 0)
            if not 0 <= x <= RIGHT - LEFT or not 0 <= yy <= height:
                raise ValueError('图示坐标超界')
            X, Y = LEFT + x, y - height + yy
            c.setDash()
            c.setLineWidth(1)
            if typ == 'rect':
                if x + obj['width'] > RIGHT - LEFT or yy + obj['height'] > height:
                    raise ValueError('矩形超界')
                c.rect(X, Y, obj['width'], obj['height'])
            elif typ == 'circle':
                radius = obj['radius']
                if x-radius < 0 or x+radius > RIGHT-LEFT or yy-radius < 0 or yy+radius > height:
                    raise ValueError('圆超界')
                c.circle(X, Y, radius)
            elif typ == 'line':
                x2, y2 = obj['x2'], obj['y2']
                if not 0 <= x2 <= RIGHT - LEFT or not 0 <= y2 <= height:
                    raise ValueError('线段超界')
                c.line(X, Y, LEFT + x2, y - height + y2)
            elif typ == 'text':
                size = obj.get('size', 12)
                if x + pdfmetrics.stringWidth(obj['text'], FONT, size) > RIGHT - LEFT:
                    raise ValueError('图中文字超界')
                text(c, X, Y, obj['text'], size)
            else:
                raise ValueError('不支持的图形类型')
        return y - height - 12
    raise ValueError('不支持的题面block：' + kind)


def render(packet, out, label):
    setup()
    qpath, apath = out / 'questions.pdf', out / 'answers.pdf'
    c = canvas.Canvas(str(qpath), pagesize=A4)
    c.setTitle(label + ' 练习题')
    for i, page in enumerate(packet['pages'], 1):
        y = header(c, label, page['subject'] + '练习', packet['date'], i, len(packet['pages']))
        for q in page['questions']:
            y = paragraph(c, y, q['id'] + '．' + q['title'], 15, 24)
            for data in q['blocks']:
                y = block(c, y, data)
                if y < BOTTOM:
                    raise ValueError('题目超出版面：' + q['id'])
            y -= 15
        c.showPage()
    c.save()
    c = canvas.Canvas(str(apath), pagesize=A4)
    c.setTitle(label + ' 家长答案')
    page_no = 1
    y = header(c, label, '家长答案', packet['date'], page_no, '?')
    for page in packet['pages']:
        for q in page['questions']:
            pieces = [q['id'] + '．' + q['answer']]
            if q.get('parent_note'):
                pieces.append('观察：' + q['parent_note'])
            for piece in pieces:
                for line in wrapped(piece, RIGHT - LEFT, 11.5):
                    if y < 65:
                        c.showPage()
                        page_no += 1
                        y = header(c, label, '家长答案', packet['date'], page_no, '?')
                    text(c, LEFT, y, line, 11.5)
                    y -= 19
            y -= 9
    c.showPage()
    c.save()
    if len(PdfReader(qpath).pages) != len(packet['pages']):
        raise ValueError('PDF页数异常')
    return {'answer_pages': len(PdfReader(apath).pages)}
