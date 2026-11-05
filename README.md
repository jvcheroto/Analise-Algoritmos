# Problema do Caixeiro Viajante — força bruta

**João Victor Piumbini Cheroto**

Projeto e Análise de Algoritmos — Universidade de Vila Velha

05/11/2026

Estudo experimental da solução por força bruta para o Problema do Caixeiro Viajante (TSP), com comparação entre os tempos medidos e a complexidade Θ(n!). O projeto reúne a implementação em Python, os resultados de 3 a 10 cidades e a discussão das questões propostas na atividade.

O [relatório completo](RELATORIO.md) reúne o método, as tabelas, o gráfico e a discussão teórica.

## Execução

Requisitos: Python 3.12 e Matplotlib 3.10.8 para a geração do gráfico.

```bash
python3 -m pip install -r requirements.txt
python3 -m unittest -v
python3 tsp.py --max-n 10 --repeticoes 3
python3 grafico.py
```

Os dados apresentados foram obtidos em um ambiente em nuvem, com três execuções por tamanho de instância. Uma nova execução substitui os arquivos de resultados; nesse caso, a tabela e a calibração do relatório também precisam acompanhar os novos valores. O benchmark aceita até 11 cidades para limitar a duração de execuções acidentais.

## Arquivos

- `tsp.py`: implementação e benchmark.
- `test_tsp.py`: testes de correção e contagem.
- `grafico.py`: comparação entre os tempos e a curva c × n!.
- `resultados/benchmark.csv`: tempos, contagens, custos e rotas.
- `resultados/comparacao.png` e `.pdf`: gráfico comparativo.
- `RELATORIO.md`: análise e respostas investigativas.

O relatório distingue os tempos medidos das projeções para instâncias maiores.
