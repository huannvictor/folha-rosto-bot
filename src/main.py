import logging
import argparse
from pathlib import Path
from pypdf import PdfReader
from pypdf._page import PageObject
from typing import cast

from .utils import setup_logging
from .core import (
    extract_escolas_from_pdf, make_overlay_pdf, 
    merge_overlay_on_template, export_csv
)

def main():
    parser = argparse.ArgumentParser(description="Gerador de Folhas de Rosto")
    parser.add_argument("--modo", choices=["impressao", "backup", "ambos"], default="ambos", 
                        help="Modo de geração: impressao (1 pág), backup (todas págs) ou ambos.")
    args = parser.parse_args()

    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    input_dir = data_dir / "input"
    output_base = data_dir / "output"
    template_pdf = data_dir / "templates" / "FOLHA DE ROSTO 2026 - com margem.pdf"
    log_dir = base_dir / "logs"

    setup_logging(log_dir)
    logging.info(f"Iniciando processamento (Modo: {args.modo})...")

    if not template_pdf.exists():
        logging.error(f"Template não encontrado: {template_pdf}")
        return

    template = PdfReader(str(template_pdf))
    page0 = cast(PageObject, template.pages[0])
    pw, ph = float(page0.mediabox.width), float(page0.mediabox.height)

    pdfs = sorted(input_dir.glob("pdfFichaEscola - *.pdf"))
    if not pdfs:
        logging.warning(f"Nenhum PDF encontrado em {input_dir}")
        return

    all_escolas = []
    for pdf_path in pdfs:
        logging.info(f"Lendo: {pdf_path.name}")
        escolas = extract_escolas_from_pdf(pdf_path)
        all_escolas.extend(escolas)

        for e in escolas:
            overlay_tmp = output_base / "_tmp_overlay.pdf"
            data = {
                "ID": e.id_normalizado, "RAZAO_SOCIAL": e.razao_social,
                "NOME_FANTASIA": e.nome_fantasia, "CNPJ_CPF": e.cnpj_cpf,
                "DIVULGADOR": e.divulgador, "ENDERECO": e.endereco,
                "NUMERO": e.numero, "CEP": e.cep, "BAIRRO": e.bairro,
                "CIDADE": e.cidade, "UF": e.uf, "TELEFONE": e.telefone, "EMAIL": e.email,
            }
            make_overlay_pdf(overlay_tmp, pw, ph, data)

            # Geração conforme o modo escolhido
            filename = f"{e.id_normalizado} - {e.divulgador}.pdf"
            
            if args.modo in ["impressao", "ambos"]:
                out_impressao = output_base / "impressao" / e.divulgador / filename
                merge_overlay_on_template(template_pdf, overlay_tmp, out_impressao, only_first_page=True)

            if args.modo in ["backup", "ambos"]:
                out_backup = output_base / "backup_digital" / e.divulgador / filename
                merge_overlay_on_template(template_pdf, overlay_tmp, out_backup, only_first_page=False)
            
            if overlay_tmp.exists(): overlay_tmp.unlink()

    csv_path = output_base / "escolas.csv"
    export_csv(csv_path, all_escolas)
    logging.info(f"Concluído! {len(all_escolas)} escolas processadas.")
    logging.info(f"Arquivos salvos em {output_base}")

if __name__ == "__main__":
    main()
