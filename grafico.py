"""Gera o gráfico comparativo a partir dos resultados do benchmark."""
import csv
import math
import os
import argparse
import tempfile
from pathlib import Path
os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'tsp-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def gerar(pasta='resultados'):
    pasta = Path(pasta)
    with (pasta / 'benchmark.csv').open() as arquivo:
        dados = list(csv.DictReader(arquivo))
    if not dados:
        raise ValueError('O CSV não contém execuções concluídas')
    ns = [int(d['n']) for d in dados]
    tempos = [float(d['segundos_mediana']) for d in dados]
    c = tempos[-1] / math.factorial(ns[-1])
    teoricos = [c * math.factorial(n) for n in ns]
    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    for eixo in eixos:
        eixo.plot(ns, tempos, 'o-', label='Tempo mediano medido')
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
    for n in range(ns[-1] + 1, ns[-1] + 4):
        print(f'PROJEÇÃO n={n}: {c * math.factorial(n):.3f} s')
    return c


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasta', default='resultados')
    gerar(parser.parse_args().pasta)
