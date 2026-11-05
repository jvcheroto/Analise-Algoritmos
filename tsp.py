"""TSP exato: todas as permutações, sem poda nem eliminação de reversos."""
import argparse
import csv
import itertools
import math
import random
import statistics
import time
from pathlib import Path


def gerar_matriz(n, seed=42):
    if n < 3:
        raise ValueError('Use pelo menos três cidades')
    rng = random.Random(seed)
    matriz = [[0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            matriz[i][j] = matriz[j][i] = rng.randint(1, 100)
    return matriz


def custo_rota(matriz, rota):
    """Soma exatamente n arestas, incluindo a volta à cidade inicial."""
    total = 0
    avaliacoes = 0
    for i in range(len(rota)):
        total += matriz[rota[i]][rota[(i + 1) % len(rota)]]
        avaliacoes += 1
    return total, avaliacoes


def resolver(matriz):
    n = len(matriz)
    if n < 3 or any(len(linha) != n for linha in matriz):
        raise ValueError('A matriz deve ser quadrada com n >= 3')
    melhor_custo = math.inf
    melhor_rota = None
    rotas = arestas = 0
    for permutacao in itertools.permutations(range(1, n)):
        rota = (0,) + permutacao
        custo, operacoes = custo_rota(matriz, rota)
        rotas += 1
        arestas += operacoes
        if custo < melhor_custo:
            melhor_custo, melhor_rota = custo, rota
    return melhor_custo, melhor_rota + (0,), rotas, arestas


def benchmark(max_n=10, repeticoes=3, destino='resultados'):
    if not 3 <= max_n <= 11:
        raise ValueError('Por segurança, use 3 <= max-n <= 11')
    if repeticoes < 1:
        raise ValueError('Use pelo menos uma repetição')
    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = []
    for n in range(3, max_n + 1):
        matriz = gerar_matriz(n)
        tempos = []
        for _ in range(repeticoes):
            inicio = time.perf_counter()
            custo, rota, rotas, arestas = resolver(matriz)
            tempos.append(time.perf_counter() - inicio)
        assert rotas == math.factorial(n - 1)
        assert arestas == math.factorial(n)
        linha = dict(n=n, rotas=rotas, arestas=arestas,
                     segundos_mediana=statistics.median(tempos),
                     segundos_min=min(tempos), segundos_max=max(tempos),
                     custo_otimo=custo, rota='-'.join(str(v + 1) for v in rota))
        linhas.append(linha)
        print(linha, flush=True)
    with (pasta / 'benchmark.csv').open('w', newline='') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=linhas[0].keys())
        escritor.writeheader()
        escritor.writerows(linhas)
    return linhas


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-n', type=int, default=10)
    parser.add_argument('--repeticoes', type=int, default=3)
    parser.add_argument('--destino', default='resultados')
    args = parser.parse_args()
    benchmark(args.max_n, args.repeticoes, args.destino)
