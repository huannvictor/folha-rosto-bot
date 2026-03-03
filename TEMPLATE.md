# TEMPLATE PROJECT
  
## Estrutura de Pastas Padrão (The Blueprint)

  Sempre comece criando esta estrutura. Ela separa o "cérebro" (código) dos "músculos" (dados) e da "memória" (logs).

  ```text
    1 nome-do-projeto/
    2 ├── data/                   # Gestão de arquivos
    3 │   ├── input/              # Arquivos crus recebidos (PDFs, CSVs, etc.)
    4 │   └── output/             # Resultados gerados (Excel, Relatórios, etc.)
    5 ├── src/                    # O Coração (Código-fonte)
    6 │   ├── __init__.py         # Torna a pasta um pacote Python
    7 │   ├── main.py             # Ponto de entrada (Orquestrador)
    8 │   ├── core.py             # Lógica principal (Regex, cálculos, extração)
    9 │   └── utils.py            # Ferramentas de apoio (Logs, caminhos, datas)
    10 ├── logs/                   # Histórico de execução para auditoria
    11 ├── scripts/                # Facilitadores (Arquivos .bat ou scripts de apoio)
    12 ├── tests/                  # Testes para garantir que o código não quebre
    13 ├── .gitignore              # Proteção (Não sobe lixo ou dados sensíveis para o Git)
    14 ├── README.md               # O seu "cartão de visitas" (Documentação)
    15 └── requirements.txt        # Lista de dependências (Bibliotecas)
  ```

---

## Divisão de Responsabilidades (O Padrão de Código)

Para manter o código limpo, siga esta regra de ouro:

* `utils.py`: Aqui ficam as funções que não "sabem" o que o projeto faz, mas ajudam. Ex: configurar log, criar pastas automaticamente, formatar CNPJ.
* `core.py`: Aqui fica a inteligência. Se o projeto é extrair de PDF, a função que abre o PDF e roda o Regex mora aqui.
* `main.py`: Este arquivo deve ser curto. Ele apenas chama o utils para iniciar o log e o core para processar os arquivos.

---

## O "Kit de Sobrevivência" de Arquivos Base

O `.gitignore` Universal:
Sempre inclua isso para não expor dados de clientes no GitHub:

```text
  1 __pycache__/
  2 venv/
  3 .env
  4 logs/*.log
  5 data/input/
  6 data/output/
  7 *.xlsx
  8 *.pdf
```

O Script de Execução (`.bat`):
Facilite a vida do usuário final (ou a sua própria):

```bat
  1 @echo off
  2 python -m src.main
  3 pause
```

---

## Checklist de Inicialização (Workflow)

### Toda vez que começar, siga estes 5 passos

  1. Ambiente: Crie a estrutura de pastas acima.
  2. Dependências: Crie o requirements.txt com o que vai usar (pandas, pdfplumber, openpyxl).
  3. Logs: Implemente o setup_logging no utils.py logo no primeiro dia. Se o código der erro, você saberá porquê.
  4. Prototipagem: Crie o core.py focando em resolver o problema para um único arquivo.
  5. Escalabilidade: Use o main.py para fazer um loop que processe todos os arquivos da pasta data/input.
