import re
import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple

def setup_logging(log_dir: Path):
    """Configura o sistema de logs para salvar em arquivos na pasta logs."""
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "execucao.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

def to_missing_if_blank(s: str, missing_marker: str = "***") -> str:
    s = (s or "").strip()
    return s if s else missing_marker

def normalize_id(id_raw: str) -> Dict[str, str]:
    digits = re.sub(r"\D", "", id_raw)
    if not digits:
        return {"digits": "", "norm": ""}
    norm = str(int(digits))
    return {"digits": digits, "norm": norm}

def validate_cpf_digits(cpf_digits: str) -> bool:
    cpf = re.sub(r"\D", "", cpf_digits or "")
    if len(cpf) != 11 or cpf == cpf[0] * 11:
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
    if len(cnpj) != 14 or cnpj == cnpj[0] * 14:
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

def validate_doc_cpf_or_cnpj(value: str, missing_marker: str = "***") -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and validate_cpf_digits(digits):
        return value.strip()
    if len(digits) == 14 and validate_cnpj_digits(digits):
        return value.strip()
    return missing_marker

def validate_email_basic(value: str, missing_marker: str = "***") -> str:
    s = (value or "").strip()
    if not s or not re.fullmatch(r"(?i)[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", s):
        return missing_marker
    return s

def normalize_phone_token(token: str) -> Optional[str]:
    t = (token or "").strip()
    if not t: return None
    t = re.sub(r"[^\d\-]", "", t)

    if re.fullmatch(r"\d{4}-\d{4}", t) or re.fullmatch(r"9\d{3,4}-\d{4}", t):
        return t

    digits = re.sub(r"\D", "", t)
    if re.fullmatch(r"\d{8}", digits):
        return f"{digits[:4]}-{digits[4:]}"
    if re.fullmatch(r"9\d{7}", digits):
        return f"{digits[:4]}-{digits[4:]}"
    if re.fullmatch(r"9\d{8}", digits):
        return f"{digits[:5]}-{digits[5:]}"
    return None
