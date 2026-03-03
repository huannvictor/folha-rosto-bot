import re
import csv
import logging
import fitz  # PyMuPDF
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, cast
from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor

from .utils import (
    to_missing_if_blank, normalize_id, validate_doc_cpf_or_cnpj,
    validate_email_basic, normalize_phone_token
)

MISSING = "***"

FIELD_POS = {
    "ID": (85, 790), "RAZAO_SOCIAL": (185, 790), "NOME_FANTASIA": (85, 745),
    "CNPJ_CPF": (105, 695), "DIVULGADOR": (445, 695), "ENDERECO": (85, 502),
    "NUMERO": (495, 502), "CEP": (495, 453), "BAIRRO": (85, 404),
    "CIDADE": (325, 404), "UF": (495, 404), "TELEFONE": (85, 310), "EMAIL": (395, 310),
}

TEXT_COLOR = HexColor("#1f4eea")
FONT_NAME = "Helvetica-Bold"
FONT_SIZE = 10

RE_HEADER = re.compile(r"^Ficha da Escola\s+(?P<nome>.+?)\s+\((?P<id>[\d\.]+)\)", re.MULTILINE)
RE_ENDERECO = re.compile(r"^Endereço:\s*(?P<end>.+)$", re.MULTILINE)
RE_BAIRRO_CIDADE_CEP = re.compile(r"^Bairro:\s*(?P<bairro>.*?)\s+Cidade:\s*(?P<cidade>.*?)/(?P<uf>[A-Z]{2})\s+CEP:\s*(?P<cep>[\d\-]+)", re.MULTILINE)
RE_RAZAO_CNPJ = re.compile(r"^Razão Social:\s*(?P<razao>.*?)\s+CNPJ\s*/\s*CPF:\s*(?P<doc>[0-9\.\-\/]+)", re.MULTILINE)
RE_TELEFONES_LINE = re.compile(r"^Telefone\(s\):\s*(?P<rest>.+)$", re.MULTILINE | re.IGNORECASE)
RE_EMAIL_ANYWHERE = re.compile(r"E-?mail:\s*(?P<email>\S+)", re.IGNORECASE)

@dataclass
class Escola:
    id_raw: str; id_digits: str; id_normalizado: str; nome_fantasia: str; razao_social: str
    cnpj_cpf: str; endereco: str; numero: str; cep: str; bairro: str; cidade: str; uf: str
    divulgador: str; telefone: str; email: str

def split_endereco_numero(endereco_full: str) -> Tuple[str, str]:
    s = (endereco_full or "").strip()
    if not s: return MISSING, MISSING
    s = re.sub(r"[,\s]+$", "", s).strip()
    if "," not in s: return to_missing_if_blank(s), MISSING
    parts = [p.strip() for p in s.split(",") if p.strip()]
    logradouro = parts[0] if len(parts) >= 1 else ""
    cand = parts[1].strip() if len(parts) >= 2 else ""
    if re.fullmatch(r"\d+", cand): return to_missing_if_blank(logradouro), cand
    if re.fullmatch(r"^(S\s*/?\s*N|SEM\s+N[UÚ]MERO)\s*\.?$", cand, flags=re.IGNORECASE):
        return to_missing_if_blank(logradouro), "S/N"
    return to_missing_if_blank(logradouro), MISSING

def extract_telefones(text: str) -> str:
    m = RE_TELEFONES_LINE.search(text or "")
    if not m: return MISSING
    rest = RE_EMAIL_ANYWHERE.sub("", m.group("rest")).strip()
    ddd_m = re.search(r"\b(\d{2})\b", rest)
    if not ddd_m: return MISSING
    ddd = ddd_m.group(1)
    rest_wo_ddd = rest[ddd_m.end():].strip()
    phones = [token for p in rest_wo_ddd.split("/") if (token := normalize_phone_token(p))]
    return f"{ddd} " + " / ".join(phones) if phones else MISSING

def parse_ficha_page_text(text: str, divulgador: str) -> Optional[Escola]:
    mh = RE_HEADER.search(text)
    if not mh: return None
    id_info = normalize_id(mh.group("id").strip())
    me = RE_ENDERECO.search(text)
    logradouro, numero = split_endereco_numero(me.group("end").strip() if me else "")
    mb = RE_BAIRRO_CIDADE_CEP.search(text)
    mr = RE_RAZAO_CNPJ.search(text)
    return Escola(
        id_raw=to_missing_if_blank(mh.group("id")), id_digits=to_missing_if_blank(id_info["digits"]),
        id_normalizado=to_missing_if_blank(id_info["norm"]), nome_fantasia=to_missing_if_blank(mh.group("nome")),
        razao_social=to_missing_if_blank(mr.group("razao") if mr else ""), cnpj_cpf=validate_doc_cpf_or_cnpj(mr.group("doc") if mr else ""),
        endereco=to_missing_if_blank(logradouro), numero=to_missing_if_blank(numero),
        cep=to_missing_if_blank(mb.group("cep") if mb else ""), bairro=to_missing_if_blank(mb.group("bairro") if mb else ""),
        cidade=to_missing_if_blank(mb.group("cidade") if mb else ""), uf=to_missing_if_blank(mb.group("uf") if mb else ""),
        divulgador=to_missing_if_blank(divulgador), telefone=extract_telefones(text),
        email=validate_email_basic(RE_EMAIL_ANYWHERE.search(text).group("email") if RE_EMAIL_ANYWHERE.search(text) else "")
    )

def extract_escolas_from_pdf(pdf_path: Path) -> List[Escola]:
    divulgador = pdf_path.stem.split("-")[-1].strip()
    escolas = []
    doc = fitz.open(pdf_path)
    for page in doc:
        if (escola := parse_ficha_page_text(page.get_text("text") or "", divulgador)):
            escolas.append(escola)
    return escolas

def export_csv(csv_path: Path, escolas: List[Escola]):
    cols = ["DIVULGADOR", "ID_RAW", "ID_DIGITS", "ID", "NOME_FANTASIA", "RAZAO_SOCIAL", "CNPJ_CPF", "ENDERECO", "NUMERO", "CEP", "BAIRRO", "CIDADE", "UF", "TELEFONE", "EMAIL"]
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter=";")
        w.writeheader()
        for e in escolas:
            w.writerow({k: getattr(e, k.lower().replace("id", "id_normalizado") if k=="ID" else k.lower()) for k in cols})

def make_overlay_pdf(output_overlay_path: Path, page_width: float, page_height: float, data: Dict[str, str]):
    c = canvas.Canvas(str(output_overlay_path), pagesize=(page_width, page_height))
    c.setFillColor(TEXT_COLOR); c.setFont(FONT_NAME, FONT_SIZE)
    for k, (x, y) in FIELD_POS.items():
        val = to_missing_if_blank(data.get(k, "")).strip()
        if len(val) > 90 and k in ("RAZAO_SOCIAL", "ENDERECO", "NOME_FANTASIA"): val = val[:87] + "..."
        c.drawString(x, y, val)
    c.showPage(); c.save()

def merge_overlay_on_template(template_pdf: Path, overlay_pdf: Path, out_pdf: Path, only_first_page: bool = False):
    template = PdfReader(str(template_pdf)); over = PdfReader(str(overlay_pdf)); writer = PdfWriter()
    base_page0 = cast(PageObject, template.pages[0])
    base_page0.merge_page(cast(PageObject, over.pages[0]))
    writer.add_page(base_page0)
    
    if not only_first_page:
        for i in range(1, len(template.pages)): writer.add_page(cast(PageObject, template.pages[i]))
    
    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pdf, "wb") as f: writer.write(f)
