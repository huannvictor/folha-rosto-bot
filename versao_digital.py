import re
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple, cast

import fitz  # PyMuPDF
from pypdf import PdfReader, PdfWriter
from pypdf._page import PageObject
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor


# =========================
# 1) CONFIGURAÇÃO (AJUSTE 1 VEZ)
# =========================
FIELD_POS = {
    "ID": (85, 790),
    "RAZAO_SOCIAL": (185, 790),
    "NOME_FANTASIA": (85, 745),
    "CNPJ_CPF": (105, 695),
    "DIVULGADOR": (445, 695),
    "ENDERECO": (85, 502),
    "NUMERO": (495, 502),
    "CEP": (495, 453),
    "BAIRRO": (85, 404),
    "CIDADE": (325, 404),
    "UF": (495, 404),
    "TELEFONE": (85, 310),
    "EMAIL": (395, 310),
}

TEXT_COLOR = HexColor("#1f4eea")
FONT_NAME = "Helvetica-Bold"
FONT_SIZE = 10

MISSING = "***"


# =========================
# 2) EXTRAÇÃO DA FICHA (PDF do sistema)
# =========================
@dataclass
class Escola:
    id_raw: str
    id_digits: str
    id_normalizado: str
    nome_fantasia: str
    razao_social: str
    cnpj_cpf: str
    endereco: str
    numero: str
    cep: str
    bairro: str
    cidade: str
    uf: str
    divulgador: str
    telefone: str
    email: str


RE_HEADER = re.compile(
    r"^Ficha da Escola\s+(?P<nome>.+?)\s+\((?P<id>[\d\.]+)\)",
    re.MULTILINE
)
RE_ENDERECO = re.compile(r"^Endereço:\s*(?P<end>.+)$", re.MULTILINE)
RE_BAIRRO_CIDADE_CEP = re.compile(
    r"^Bairro:\s*(?P<bairro>.*?)\s+Cidade:\s*(?P<cidade>.*?)/(?P<uf>[A-Z]{2})\s+CEP:\s*(?P<cep>[\d\-]+)",
    re.MULTILINE
)
RE_RAZAO_CNPJ = re.compile(
    r"^Razão Social:\s*(?P<razao>.*?)\s+CNPJ\s*/\s*CPF:\s*(?P<doc>[0-9\.\-\/]+)",
    re.MULTILINE
)
RE_TELEFONES_LINE = re.compile(
    r"^Telefone\(s\):\s*(?P<rest>.+)$", re.MULTILINE | re.IGNORECASE
)
RE_EMAIL_ANYWHERE = re.compile(
    r"E-?mail:\s*(?P<email>\S+)", re.IGNORECASE
)


def to_missing_if_blank(s: str) -> str:
    s = (s or "").strip()
    return s if s else MISSING


def normalize_id(id_raw: str) -> Dict[str, str]:
    digits = re.sub(r"\D", "", id_raw)  # "020.743" -> "020743"
    if not digits:
        return {"digits": "", "norm": ""}
    norm = str(int(digits))  # remove zeros à esquerda ("020743" -> "20743")
    return {"digits": digits, "norm": norm}


# =========================
# VALIDAÇÕES (CPF/CNPJ/EMAIL/TELEFONE)
# =========================
def validate_cpf_digits(cpf_digits: str) -> bool:
    cpf = re.sub(r"\D", "", cpf_digits or "")
    if len(cpf) != 11:
        return False
    if cpf == cpf[0] * 11:
        return False

    def calc_digit(base: str, weights: List[int]) -> str:
        total = sum(int(d) * w for d, w in zip(base, weights))
        r = total % 11
        return "0" if r < 2 else str(11 - r)

    d1 = calc_digit(cpf[:9], list(range(10, 1, -1)))
    d2 = calc_digit(cpf[:9] + d1, list(range(11, 1, -1)))
    return cpf[-2:] == d1 + d2


def validate_cnpj_digits(cnpj_digits: str) -> bool:
    cnpj = re.sub(r"\D", "", cnpj_digits or "")
    if len(cnpj) != 14:
        return False
    if cnpj == cnpj[0] * 14:
        return False

    def calc_digit(base: str, weights: List[int]) -> str:
        total = sum(int(d) * w for d, w in zip(base, weights))
        r = total % 11
        return "0" if r < 2 else str(11 - r)

    w1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    w2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]

    d1 = calc_digit(cnpj[:12], w1)
    d2 = calc_digit(cnpj[:12] + d1, w2)
    return cnpj[-2:] == d1 + d2


def validate_doc_cpf_or_cnpj(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and validate_cpf_digits(digits):
        return value.strip()
    if len(digits) == 14 and validate_cnpj_digits(digits):
        return value.strip()
    return MISSING


def validate_email_basic(value: str) -> str:
    s = (value or "").strip()
    if not s:
        return MISSING
    # validação simples e suficiente p/ saneamento
    if re.fullmatch(r"(?i)[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", s):
        return s
    return MISSING


def normalize_phone_token(token: str) -> Optional[str]:
    """
    Aceita:
    - fixo: 3042-5116 (8 dígitos)
    - celular: 9xxx-xxxx (8 dígitos) ou 9xxxx-xxxx (9 dígitos)
    Retorna o token "bonito" (com hífen) se válido; senão None.
    """
    t = (token or "").strip()
    if not t:
        return None

    # mantém só dígitos e hífen, porque no PDF costuma vir assim
    t = re.sub(r"[^\d\-]", "", t)

    if re.fullmatch(r"\d{4}-\d{4}", t):              # fixo
        return t
    if re.fullmatch(r"9\d{3}-\d{4}", t):             # 9XXX-XXXX
        return t
    if re.fullmatch(r"9\d{4}-\d{4}", t):             # 9XXXX-XXXX
        return t

    # fallback: se vier só dígitos, tenta formatar
    digits = re.sub(r"\D", "", t)
    if re.fullmatch(r"\d{8}", digits):
        return f"{digits[:4]}-{digits[4:]}"
    if re.fullmatch(r"9\d{7}", digits):
        return f"{digits[:4]}-{digits[4:]}"
    if re.fullmatch(r"9\d{8}", digits):
        return f"{digits[:5]}-{digits[5:]}"

    return None


def extract_email(text: str) -> str:
    m = RE_EMAIL_ANYWHERE.search(text or "")
    if not m:
        return MISSING
    return validate_email_basic(m.group("email"))


def extract_telefones(text: str) -> str:
    """
    Lê a linha "Telefone(s): ...", tolerante com variações e com E-Mail na mesma linha.
    Retorna:
    - "83 3042-5116 / 98796-3926"
    - "***" se não houver nenhum telefone válido
    """
    m = RE_TELEFONES_LINE.search(text or "")
    if not m:
        return MISSING

    rest = m.group("rest").strip()

    # Remove o trecho do email da linha de telefone (se existir)
    rest = RE_EMAIL_ANYWHERE.sub("", rest).strip()

    # pega o DDD (primeiros 2 dígitos que aparecerem)
    ddd_m = re.search(r"\b(\d{2})\b", rest)
    if not ddd_m:
        return MISSING
    ddd = ddd_m.group(1)

    # remove o DDD do começo (primeira ocorrência) e quebra por "/"
    rest_wo_ddd = rest[ddd_m.end():].strip()
    parts = [p.strip() for p in rest_wo_ddd.split("/")]

    phones = []
    for p in parts:
        token = normalize_phone_token(p)
        if token:
            phones.append(token)

    if not phones:
        return MISSING

    return f"{ddd} " + " / ".join(phones)


def split_endereco_numero(endereco_full: str) -> Tuple[str, str]:
    """
    Regras:
    - logradouro = antes da primeira vírgula
    - numero = após a primeira vírgula (aceita dígitos ou variações de "sem número")
    - ignora complemento (após segunda vírgula)
    - se não houver vírgula -> numero = "***" (regra nova)
    - se não houver endereço -> "***" em ambos
    """
    s = (endereco_full or "").strip()
    if not s:
        return MISSING, MISSING

    s = re.sub(r"[,\s]+$", "", s).strip()

    if "," not in s:
        return to_missing_if_blank(s), MISSING

    parts = [p.strip() for p in s.split(",") if p.strip()]
    logradouro = parts[0] if len(parts) >= 1 else ""
    candidato_num = parts[1] if len(parts) >= 2 else ""
    cand = candidato_num.strip()

    if re.fullmatch(r"\d+", cand):
        return to_missing_if_blank(logradouro), cand

    sem_numero_patterns = [
        r"^S\s*/?\s*N\s*[º°]?\s*\.?$",
        r"^SEM\s+N[UÚ]MERO\s*\.?$",
    ]
    for pat in sem_numero_patterns:
        if re.fullmatch(pat, cand, flags=re.IGNORECASE):
            return to_missing_if_blank(logradouro), "S/N"

    return to_missing_if_blank(logradouro), MISSING


def parse_ficha_page_text(text: str, divulgador: str) -> Optional[Escola]:
    mh = RE_HEADER.search(text)
    if not mh:
        return None

    nome_fantasia = mh.group("nome").strip()
    id_raw = mh.group("id").strip()
    id_info = normalize_id(id_raw)

    me = RE_ENDERECO.search(text)
    endereco_full = me.group("end").strip() if me else ""
    logradouro, numero = split_endereco_numero(endereco_full)

    mb = RE_BAIRRO_CIDADE_CEP.search(text)
    bairro = mb.group("bairro").strip() if mb else ""
    cidade = mb.group("cidade").strip() if mb else ""
    uf = mb.group("uf").strip() if mb else ""
    cep = mb.group("cep").strip() if mb else ""

    mr = RE_RAZAO_CNPJ.search(text)
    razao_social = mr.group("razao").strip() if mr else ""
    cnpj_cpf_raw = mr.group("doc").strip() if mr else ""
    cnpj_cpf = validate_doc_cpf_or_cnpj(cnpj_cpf_raw)

    email = extract_email(text)

    telefone = extract_telefones(text)

    return Escola(
        id_raw=to_missing_if_blank(id_raw),
        id_digits=to_missing_if_blank(id_info["digits"]),
        id_normalizado=to_missing_if_blank(id_info["norm"]),
        nome_fantasia=to_missing_if_blank(nome_fantasia),
        razao_social=to_missing_if_blank(razao_social),
        cnpj_cpf=to_missing_if_blank(cnpj_cpf),
        endereco=to_missing_if_blank(logradouro),
        numero=to_missing_if_blank(numero),
        cep=to_missing_if_blank(cep),
        bairro=to_missing_if_blank(bairro),
        cidade=to_missing_if_blank(cidade),
        uf=to_missing_if_blank(uf),
        divulgador=to_missing_if_blank(divulgador),
        telefone=to_missing_if_blank(telefone),
        email=to_missing_if_blank(email),
    )


def extract_escolas_from_pdf(pdf_path: Path) -> List[Escola]:
    divulgador = pdf_path.stem.split("-")[-1].strip()

    escolas: List[Escola] = []
    doc = fitz.open(pdf_path)
    for i in range(doc.page_count):
        page = doc.load_page(i)
        text = page.get_text("text") or ""
        escola = parse_ficha_page_text(text, divulgador)
        if escola:
            escolas.append(escola)

    return escolas


# =========================
# 3) CSV + LOGS DE FALTAS
# =========================
CSV_COLUMNS = [
    "DIVULGADOR",
    "ID_RAW",
    "ID_DIGITS",
    "ID",
    "NOME_FANTASIA",
    "RAZAO_SOCIAL",
    "CNPJ_CPF",
    "ENDERECO",
    "NUMERO",
    "CEP",
    "BAIRRO",
    "CIDADE",
    "UF",
    # 🔹 NOVOS
    "TELEFONE",
    "EMAIL",
]

REQUIRED_FIELDS = [
    "id_normalizado",
    "nome_fantasia",
    "razao_social",
    "cnpj_cpf",
    "endereco",
    "numero",
    "cep",
    "bairro",
    "cidade",
    "uf",
    "divulgador",
    "telefone",
    "email",
]


def missing_fields(escola: Escola) -> List[str]:
    faltas = []
    for f in REQUIRED_FIELDS:
        v = getattr(escola, f, "")
        if not v or str(v).strip() == MISSING:
            faltas.append(f)
    return faltas


def export_csv(csv_path: Path, escolas: List[Escola]):
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, delimiter=";")
        w.writeheader()
        for e in escolas:
            w.writerow({
                "DIVULGADOR": e.divulgador,
                "ID_RAW": e.id_raw,
                "ID_DIGITS": e.id_digits,
                "ID": e.id_normalizado,
                "NOME_FANTASIA": e.nome_fantasia,
                "RAZAO_SOCIAL": e.razao_social,
                "CNPJ_CPF": e.cnpj_cpf,
                "ENDERECO": e.endereco,
                "NUMERO": e.numero,
                "CEP": e.cep,
                "BAIRRO": e.bairro,
                "CIDADE": e.cidade,
                "UF": e.uf,
                "TELEFONE": e.telefone,
                "EMAIL": e.email,
            })


# =========================
# 4) GERAR FOLHA DE ROSTO (overlay + merge)
# =========================
def make_overlay_pdf(output_overlay_path: Path, page_width: float, page_height: float, data: Dict[str, str]):
    c = canvas.Canvas(str(output_overlay_path), pagesize=(page_width, page_height))
    c.setFillColor(TEXT_COLOR)
    c.setFont(FONT_NAME, FONT_SIZE)

    def draw(field: str, value: str):
        value = to_missing_if_blank(value)
        x, y = FIELD_POS[field]
        value = value.strip()

        if len(value) > 90 and field in ("RAZAO_SOCIAL", "ENDERECO", "NOME_FANTASIA"):
            value = value[:87] + "..."
        c.drawString(x, y, value)

    for k in (
        "ID", "RAZAO_SOCIAL", "NOME_FANTASIA", "CNPJ_CPF", "DIVULGADOR",
        "ENDERECO", "NUMERO", "CEP", "BAIRRO", "CIDADE", "UF", "TELEFONE", "EMAIL",
    ):
        draw(k, data.get(k, ""))

    c.showPage()
    c.save()


def merge_overlay_on_template(template_pdf: Path, overlay_pdf: Path, out_pdf: Path):
    template = PdfReader(str(template_pdf))
    over = PdfReader(str(overlay_pdf))
    writer = PdfWriter()

    # Página 1 (index 0) = template + overlay
    base_page0 = cast(PageObject, template.pages[0])
    overlay_page0 = cast(PageObject, over.pages[0])
    base_page0.merge_page(overlay_page0)  # pylint: disable=no-member
    writer.add_page(base_page0)

    # Páginas seguintes = template “puro” (backup)
    for i in range(1, len(template.pages)):
        writer.add_page(cast(PageObject, template.pages[i]))

    out_pdf.parent.mkdir(parents=True, exist_ok=True)
    with open(out_pdf, "wb") as f:
        writer.write(f)


# =========================
# 5) PIPELINE PRINCIPAL
# =========================
def gerar_folhas_rosto(input_dir: Path, template_pdf: Path, output_dir: Path):
    if not template_pdf.exists():
        raise FileNotFoundError(f"Template não encontrado: {template_pdf}")

    template = PdfReader(str(template_pdf))
    template_page0 = cast(PageObject, template.pages[0])
    mediabox = template_page0.mediabox  # pylint: disable=no-member
    page_width = float(mediabox.width)
    page_height = float(mediabox.height)

    pdfs = sorted(input_dir.glob("pdfFichaEscola - *.pdf"))
    if not pdfs:
        raise FileNotFoundError(f"Nenhum PDF encontrado em {input_dir} com padrão 'pdfFichaEscola - *.pdf'")

    all_escolas: List[Escola] = []
    total_pdfs = 0

    for pdf_path in pdfs:
        total_pdfs += 1
        escolas = extract_escolas_from_pdf(pdf_path)

        if not escolas:
            print(f"[WARN] Nenhuma escola detectada em: {pdf_path.name}")
            continue

        all_escolas.extend(escolas)

        for e in escolas:
            faltas = missing_fields(e)
            if faltas:
                print(f"[WARN] {e.id_normalizado} ({e.divulgador}) faltou campo: {', '.join(faltas)}")

        for e in escolas:
            divulgador_dir = output_dir / e.divulgador
            out_name = f"{e.id_normalizado} - {e.divulgador}.pdf"
            out_pdf = divulgador_dir / out_name

            overlay_pdf = output_dir / "_tmp_overlay.pdf"

            data = {
                "ID": e.id_normalizado,
                "RAZAO_SOCIAL": e.razao_social,
                "NOME_FANTASIA": e.nome_fantasia,
                "CNPJ_CPF": e.cnpj_cpf,
                "DIVULGADOR": e.divulgador,
                "ENDERECO": e.endereco,
                "NUMERO": e.numero,
                "CEP": e.cep,
                "BAIRRO": e.bairro,
                "CIDADE": e.cidade,
                "UF": e.uf,
                "TELEFONE": e.telefone,
                "EMAIL": e.email,
            }

            make_overlay_pdf(overlay_pdf, page_width, page_height, data)
            merge_overlay_on_template(template_pdf, overlay_pdf, out_pdf)

        print(f"[OK] {pdf_path.name}: {len(escolas)} escolas -> {output_dir / escolas[0].divulgador}")

    csv_path = output_dir / "escolas.csv"
    export_csv(csv_path, all_escolas)
    print(f"\n[OK] CSV gerado para auditoria: {csv_path}")

    tmp = output_dir / "_tmp_overlay.pdf"
    if tmp.exists():
        tmp.unlink()

    print(f"\n✅ Concluído: {len(all_escolas)} folhas geradas (de {total_pdfs} PDFs lidos).")


if __name__ == "__main__":
    base_dir = Path(__file__).parent
    input_dir = base_dir / "input"
    template_pdf = base_dir / "templates" / "FOLHA DE ROSTO 2026 - com margem.pdf"
    output_dir = base_dir / "output_digital"

    gerar_folhas_rosto(input_dir, template_pdf, output_dir)