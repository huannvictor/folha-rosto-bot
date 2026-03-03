# Folha de Rosto Bot 🤖

Bot para extração de dados de fichas de escolas e geração automática de Folhas de Rosto em PDF.

## Estrutura de Pastas

```text
folha-rosto-bot/
├── data/
│   ├── input/              # PDFs originais (fichas)
│   │   ├── processados-RN/ # Arquivos do RN
│   │   └── processados-PB/ # Arquivos da PB
│   ├── output/             # Resultados gerados
│   │   ├── impressao/      # PDFs de 1 página (impressão em massa)
│   │   ├── backup_digital/ # PDFs completos (backup divulgador)
│   │   └── escolas.csv     # Relatório de auditoria
│   └── templates/          # Template base (PDF)
├── logs/                   # Registros de execução
├── scripts/                # Facilitadores (run.bat)
├── src/                    # Código-fonte
│   ├── core.py             # Lógica de extração e PDF
│   ├── main.py             # Orquestrador
│   └── utils.py            # Validações e suporte
├── tests/                  # Testes unitários
├── .gitignore              # Proteção de arquivos
├── README.md               # Documentação
└── requirements.txt        # Dependências
```

## Como Executar

1. Coloque os arquivos PDF na pasta `data/input`.
2. Garanta que o template está em `data/templates`.
3. Execute o script `scripts/run.bat` ou use o comando padrão:

  ```bash
  python -m src.main
  ```

### Modos de Operação

O script permite escolher qual tipo de arquivo gerar através do argumento `--modo`:

* **Ambos (Padrão):** Gera as pastas de impressão e backup simultaneamente.

  executa: `run.bat`
  
  ou

  ```bash
  python -m src.main --modo ambos
  ```

* **Apenas Impressão:** Gera apenas os arquivos de 1 página.

  ```bash
  python -m src.main --modo impressao
  ```

* **Apenas Backup:** Gera apenas os arquivos completos (com todas as páginas do template).

  ```bash
  python -m src.main --modo backup
  ```

## Requisitos

As bibliotecas necessárias estão em `requirements.txt`. Instale com:

```bash
pip install -r requirements.txt
```
