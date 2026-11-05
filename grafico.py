"""Gera o gráfico comparativo a partir dos resultados do benchmark."""
import csv
import math
import os
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', '/tmp/tsp-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def gerar(pasta='resultados'):
    pasta = Path(pasta)
    with (pasta / 'benchmark.csv').open() as arquivo:
        dados = list(csv.DictReader(arquivo))
    ns = [int(d['n']) for d in dados]
    tempos = [float(d['segundos_mediana']) for d in dados]
    # Calibração pela maior instância medida, onde o overhead pesa menos.
    c = tempos[-1] / math.factorial(ns[-1])
    teoricos = [c * math.factorial(n) for n in ns]
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    for eixo in eixos:
        eixo.plot(ns, tempos, 'o-', label='Mediana de 3 execuções')
        eixo.plot(ns, teoricos, '--', label='c × n! (calibrada no maior n)')
        eixo.set(xlabel='Número de cidades (n)', ylabel='Tempo (segundos)', xticks=ns)
        eixo.grid(True, alpha=.3)
        eixo.legend()
    eixos[0].set_title('Crescimento do tempo')
    eixos[1].set_yscale('log')
    eixos[1].set_title('Mesmos dados em escala logarítmica')
    fig.tight_layout()
    fig.savefig(pasta / 'comparacao.png', dpi=180)
    fig.savefig(pasta / 'comparacao.pdf')
    plt.close(fig)
    print(f'Constante calibrada c = {c:.12g} s/operação contada')
    for n in (11, 12, 13, 14, 15):
        print(f'PROJEÇÃO n={n}: {c * math.factorial(n):.3f} s')
    return c


if __name__ == '__main__':
    gerar()
