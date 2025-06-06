import streamlit as st
from docx import Document
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
import tempfile
import re
import language_tool_python

st.set_page_config(page_title="French Canadian QA Checker", layout="centered")
st.title("🇨🇦 French Canadian Translation QA Checker")

page_offset = st.number_input("📄 Enter starting page number for content:", min_value=1, value=1, step=1)
uploaded_file = st.file_uploader("Upload a .docx translation file", type="docx")

if uploaded_file:
    doc = Document(uploaded_file)
    filename = uploaded_file.name

    issues = []
    line_num = 0
    tool = language_tool_python.LanguageTool(
        "fr-CA",
        remote_server="https://languagetool-yourapp-small-pine-7918.fly.dev"
    )

    phone_patterns = [
        re.compile(r"\(\d{3}\)[\s-]?\d{3}[- ]\d{4}"),
        re.compile(r"\b\d{3}[- ]\d{3}[- ]\d{4}\b")
    ]

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue
        line_num += 1
        page = page_offset + (line_num // 40)

        # Apostrophes
        for m in re.finditer(r"\b\w*'\w*\b", text):
            snippet = text[max(0, m.start()-30):m.end()+30]
            context = "..." + snippet.strip() + "..."
            issues.append((page, line_num, "Apostrophe", "Straight apostrophe used instead of curved (’)", context))

        # Non-breaking space before colon
        for m in re.finditer(r"(?<!\u00A0):", text):
            idx = m.start()
            snippet = text[max(0, idx-30):idx+30]
            context = "..." + snippet.strip() + "..."
            issues.append((page, line_num, "Non-breaking space", "Missing NBSP before colon", context))

        # Guillemets check
        for idx, char in enumerate(text):
            if char == "«":
                after = text[idx + 1] if idx + 1 < len(text) else ""
                if after != ' ' and after.isalpha():
                    context = "..." + text[max(0, idx - 30):idx + 30] + "..."
                    issues.append((page, line_num, "Guillemets spacing", "Missing regular space after «", context))
            if char == "»":
                before = text[idx - 1] if idx > 0 else ""
                if before != ' ' and before.isalpha():
                    context = "..." + text[max(0, idx - 30):idx + 30] + "..."
                    issues.append((page, line_num, "Guillemets spacing", "Missing regular space before »", context))

        # Grammar checks using LanguageTool (NOW CORRECTLY INSIDE LOOP)
        matches = tool.check(text)
        for match in matches:
            error_text = text[match.offset:match.offset + match.errorLength]
            snippet = text[max(0, match.offset - 30):match.offset + match.errorLength + 30]
            context = "..." + snippet.strip() + "..."
            issues.append((
                page,
                line_num,
                "Grammar",
                match.message,
                context
            ))

    if st.button("✅ Run QA Check"):
        styles = getSampleStyleSheet()
        styleN = styles["Normal"]
        flow = []

        flow.append(Paragraph("<b>French Canadian Translation QA Summary</b>", styles["Title"]))
        flow.append(Paragraph(f"<font size=9 color='gray'>File: {filename}</font>", styles["Normal"]))
        flow.append(Paragraph("""
This summary includes QA checks for:<br/>
- Straight vs. curved apostrophes (’)<br/>
- Missing non-breaking spaces before French punctuation (:<br/>
- Determiner-noun agreement (e.g., 'tout polluants' → 'tous les polluants')<br/>
- Guillemets (« ») must be surrounded by regular breaking spaces<br/>
Note: Email capitalization inconsistencies are ignored.
""", styles["Normal"]))

        table_data = [["Page", "Line", "Issue Category", "Note", "Context"]]
        for page, line, cat, note, ctx in issues:
            table_data.append([str(page), str(line), cat, note, Paragraph(ctx, styleN)])

        table = Table(table_data, colWidths=[35, 35, 90, 200, 170])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#dce6f1")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#000000")),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 2),
            ('RIGHTPADDING', (0, 0), (-1, -1), 2),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 0.3, colors.gray),
            ('WORDWRAP', (4, 1), (4, -1), True)
        ]))
        flow.append(table)

        temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        pdf = SimpleDocTemplate(temp_pdf.name, pagesize=letter)
        pdf.build(flow)

        with open(temp_pdf.name, "rb") as f:
            st.download_button("📥 Download QA Summary PDF", f, file_name="QA_Summary_French_Canadian_Translation.pdf")
