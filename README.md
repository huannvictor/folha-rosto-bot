# Folha de Rosto Bot 🤖

Bot para extração de dados de fichas de escolas e geração automática de Folhas de Rosto em PDF.

## ⚠️ Problemática

Como Assistente Comercial, uma das minhas atribuições críticas é a atualização cadastral das escolas para alimentar o sistema da empresa com dados de contato, alunado e adoção de sistemas de ensino.
O fluxo convencional depende de formulários impressos preenchidos por divulgadores em campo. No entanto, a versão atualizada desses formulários muitas vezes leva semanas ou meses para ficar disponível, enquanto a demanda por esses dados é urgente.

Nesse cenário, a solução paliativa era o preenchimento de formulários em branco **totalmente à mão**. Para uma amostra como a da Paraíba (**671 escolas**), o impacto operacional é massivo:

* **Complexidade do Formulário:** O documento exige o preenchimento de mais de 13 campos cadastrais densos (Razão Social, CNPJ, Endereços longos, E-mails, Telefones, etc.), além de dados variáveis (Alunado, Mensalidades).
* **Estimativa de Tempo Manual:** Considerando uma média conservadora de **4 minutos** para localizar os dados e transcrevê-los de forma legível em cada folha, seriam necessárias aproximadamente **44 horas e 44 minutos** de trabalho ininterrupto.
* **Retrabalho:** Dados ilegíveis ou incompletos vindos do campo geravam um ciclo constante de correções manuais.

## ✅ Solução

O **Folha de Rosto Bot** automatiza a parte mais braçal e suscetível a erros desse processo. Ele extrai dados brutos de relatórios do sistema e os "injeta" cirurgicamente no template oficial em PDF.

* **Otimização:** O bot popula automaticamente todos os dados fixos (ID, CNPJ, Razão Social, Localização, Contato).
* **Foco no que importa:** O divulgador em campo agora recebe uma folha pré-preenchida, precisando atualizar apenas o que é estritamente novo ou variável (alunado, mensalidade).
* **Economia de Tempo Real:** O processamento das **671 escolas da Paraíba**, que levaria mais de uma semana de trabalho manual (45h), é concluído pelo bot em **menos de 1 minuto**.
* **Precisão:** Erros de digitação e problemas com caligrafia foram eliminados, garantindo que o sistema receba sempre a informação correta.

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
