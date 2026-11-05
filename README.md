# Problema do Caixeiro Viajante — força bruta

**João Victor Piumbini Cheroto**

Projeto e Análise de Algoritmos — Universidade de Vila Velha

05/11/2026

Implementação exata do TSP por enumeração de rotas, com contagem de operações, medição de tempos e comparação com Θ(n!). O [relatório](RELATORIO.md) apresenta o método, os resultados e as respostas da atividade.

## Execução no VS Code

Requisitos: Python 3.12 e a extensão Python da Microsoft. O benchmark usa somente a biblioteca padrão; a geração do gráfico exige Matplotlib.

1. Extrair o projeto e abrir a pasta que contém `tsp.py` no VS Code.
2. Abrir **Terminal → Novo Terminal**.
3. Executar os comandos abaixo, um por vez.

No Windows:

```powershell
py -m pip install -r requirements.txt
py -m unittest -v
py tsp.py --max-n 13 --repeticoes 3 --limite 90
py grafico.py
py relatorio.py
```

No Linux, substituir `py` por `python3`; também é possível usar `python` quando esse for o comando da instalação local. Não é necessário digitar comandos no console interativo `>>>`.

O benchmark imprime o início e o fim de cada repetição. Ao atingir o limite por execução, encerra o processo de cálculo e preserva os tamanhos já concluídos. A medição do algoritmo exclui o início do processo; o limite de espera inclui esse início. O limite é um critério experimental, não o máximo absoluto do computador.

Para uma demonstração rápida:

```powershell
py tsp.py --max-n 8 --repeticoes 3 --limite 90 --destino demonstracao
py grafico.py --pasta demonstracao
py relatorio.py --pasta demonstracao --destino demonstracao/RELATORIO.md
```

Essa demonstração usa uma pasta separada e preserva os resultados incluídos no projeto. Para investigar tamanhos maiores, aumentar `--max-n` (até 20) e `--limite`, conforme o tempo disponível. A busca cresce fatorialmente; solicitar 20 cidades não significa que o cálculo terminará em tempo viável. O programa para na primeira repetição que atingir o limite.

## Resultados e arquivos

- `tsp.py`: geração da matriz, cálculo exato e benchmark.
- `test_tsp.py`: testes de correção e funcionamento do experimento.
- `grafico.py`: geração das curvas medida e teórica.
- `relatorio.py`: atualização do texto, tabelas e projeções a partir dos resultados.
- `resultados/benchmark.csv`: tamanhos completos, tempos individuais, mediana, mínimo, máximo, contagens, custo ótimo e rota.
- `resultados/ambiente.json`: ambiente, parâmetros e eventual interrupção por tempo.
- `resultados/comparacao.png` e `.pdf`: gráfico; o PDF dessa pasta contém apenas o gráfico.
- `RELATORIO.md`: relatório completo, legível diretamente no GitHub.

Os resultados incluídos foram medidos em um ambiente em nuvem. Uma execução no computador pessoal produzirá outros tempos e possivelmente outro limite prático. Após um novo benchmark, executar novamente `grafico.py` e `relatorio.py`.
