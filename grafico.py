"""Gráficos dos tempos e contagens dos experimentos de TSP."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import tempfile

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'tsp-matplotlib'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from catalogo_graficos import GRAFICOS
from web.experimentos import resumo

AZUL = '#247aa5'
VERDE = '#176d64'
LARANJA = '#d47b37'


def finalizar(fig, eixo, pasta, indice):
    eixo.grid(True, alpha=.2)
    eixo.set_axisbelow(True)
    fig.tight_layout()
    fig.savefig(pasta / GRAFICOS[indice][0], dpi=160)
    plt.close(fig)


def carregar_complementar(pasta, nome):
    arquivo = pasta / 'complementares' / f'{nome}.json'
    if not arquivo.exists():
        return None
    registro = json.loads(arquivo.read_text(encoding='utf-8'))
    if registro['estado'] != 'concluido' or len(registro['amostras']) != registro['plano_total']:
        raise ValueError(f'A coleta complementar {nome} não foi concluída')
    return registro


def gerar(pasta='resultados'):
    pasta = Path(pasta)
    with (pasta / 'benchmark.csv').open(encoding='utf-8') as arquivo:
        dados = list(csv.DictReader(arquivo))
    if not dados:
        raise ValueError('O CSV não contém execuções concluídas')
    ns = [int(d['n']) for d in dados]
    tempos = [float(d['segundos_mediana']) for d in dados]
    c = tempos[-1] / math.factorial(ns[-1])
    teoricos = [c * math.factorial(n) for n in ns]
    pasta_graficos = pasta / 'graficos'
    pasta_graficos.mkdir(exist_ok=True)

    def tempo(eixo, log=False):
        eixo.plot(ns, tempos, 'o-', color=AZUL, label='Mediana medida')
        eixo.plot(ns, teoricos, '--', color=LARANJA, label='c × n!')
        eixo.set(xlabel='Número de cidades (n)', ylabel='Tempo (s)', xticks=ns)
        eixo.set_title('Escala logarítmica' if log else 'Escala linear')
        if log:
            eixo.set_yscale('log')
        eixo.grid(True, alpha=.2)
        eixo.legend()

    fig, eixos = plt.subplots(1, 2, figsize=(12, 4.5))
    tempo(eixos[0])
    tempo(eixos[1], True)
    fig.tight_layout()
    fig.savefig(pasta / 'comparacao.png', dpi=180)
    fig.savefig(pasta / 'comparacao.pdf')
    plt.close(fig)
    for indice in (0, 1):
        fig, eixo = plt.subplots(figsize=(8.5, 4.5))
        tempo(eixo, indice == 1)
        finalizar(fig, eixo, pasta_graficos, indice)

    for indice, campo, previsto, formula in (
            (2, 'rotas', lambda n: math.factorial(n - 1), '(n−1)!'),
            (3, 'arestas', math.factorial, 'n!')):
        valores = [int(d[campo]) for d in dados]
        if valores != [previsto(n) for n in ns]:
            raise ValueError(f'Contagens de {campo} divergentes da teoria')
        fig, eixo = plt.subplots(figsize=(8.5, 4.5))
        eixo.plot(ns, [previsto(n) for n in ns], '--', color=LARANJA, label=f'Esperado: {formula}')
        eixo.scatter(ns, valores, s=35, color=AZUL, zorder=3, label='Contagem observada')
        eixo.set(xlabel='Número de cidades (n)', ylabel='Quantidade por chamada', xticks=ns,
                 title=GRAFICOS[indice][1], yscale='log')
        eixo.legend()
        finalizar(fig, eixo, pasta_graficos, indice)

    origem = carregar_complementar(pasta, 'origem')
    if origem:
        linhas = resumo(origem['amostras'])
        fig, eixo = plt.subplots(figsize=(8.5, 4.5))
        for fixar, cor, nome in ((True, AZUL, 'Origem fixa'), (False, LARANJA, 'Origem livre')):
            grupo = sorted((d for d in linhas if d['fixar'] == fixar), key=lambda d: d['n'])
            eixo.plot([d['n'] for d in grupo], [d['mediana'] for d in grupo], 'o-', color=cor, label=nome)
        eixo.set(xlabel='Número de cidades (n)', ylabel='Tempo mediano (s)', yscale='log',
                 title='Efeito da fixação da cidade inicial', xticks=sorted({d['n'] for d in linhas}))
        eixo.legend()
        finalizar(fig, eixo, pasta_graficos, 4)
    else:
        (pasta_graficos / GRAFICOS[4][0]).unlink(missing_ok=True)

    metodos = carregar_complementar(pasta, 'metodos')
    if metodos:
        linhas = resumo(metodos['amostras'])
        tamanhos = {d['n'] for d in linhas}
        if len(tamanhos) != 1:
            raise ValueError('A comparação de métodos deve usar uma única instância')
        nomes = {'bruta': 'Força bruta', 'held_karp': 'Held–Karp', 'guloso': 'Vizinho mais próximo'}
        fig, eixo = plt.subplots(figsize=(8.5, 4.5))
        tempos_metodos = [d['mediana'] for d in linhas]
        eixo.bar(range(len(linhas)), tempos_metodos, color=[AZUL, VERDE, LARANJA], width=.5)
        for i, d in enumerate(linhas):
            eixo.annotate(f"{d['mediana']:.6f} s\ncusto {d['custo']}", (i, d['mediana']),
                          xytext=(0, 8), textcoords='offset points', ha='center', fontsize=9)
        eixo.set(xticks=range(len(linhas)), xticklabels=[nomes[d['algoritmo']] for d in linhas],
                 xlabel='Método', ylabel='Tempo mediano (s)', yscale='log',
                 title=f'Comparação de métodos — {next(iter(tamanhos))} cidades')
        eixo.set_ylim(min(tempos_metodos) / 4, max(tempos_metodos) * 8)
        finalizar(fig, eixo, pasta_graficos, 5)
    else:
        (pasta_graficos / GRAFICOS[5][0]).unlink(missing_ok=True)

    print(f'Constante calibrada c = {c:.12g} s/operação contada')
    print(f'Gráficos disponíveis em {pasta_graficos}')
    return c


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasta', default='resultados')
    gerar(parser.parse_args().pasta)
