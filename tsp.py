"""TSP exato: todas as permutações, sem poda nem eliminação de reversos."""
import argparse
import csv
import itertools
import math
import json
import multiprocessing
import platform
from datetime import datetime, timezone
import random
import statistics
import sys
import time
from pathlib import Path


def gerar_matriz(n, seed=42):
    if isinstance(n, bool) or not isinstance(n, int) or n < 3:
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


def permutacoes(elementos):
    """Enumera permutações por trocas, sem armazenar o espaço de busca."""
    itens = list(elementos)

    def visitar(posicao):
        if posicao == len(itens):
            yield tuple(itens)
            return
        for indice in range(posicao, len(itens)):
            itens[posicao], itens[indice] = itens[indice], itens[posicao]
            yield from visitar(posicao + 1)
            itens[posicao], itens[indice] = itens[indice], itens[posicao]

    yield from visitar(0)


def resolver(matriz, fixar_inicio=True, gerador='biblioteca'):
    if not isinstance(matriz, (list, tuple)):
        raise ValueError('A matriz deve ser uma sequência de linhas')
    n = len(matriz)
    if n < 3 or any(not isinstance(linha, (list, tuple)) or len(linha) != n for linha in matriz):
        raise ValueError('A matriz deve ser quadrada com n >= 3')
    if any(isinstance(valor, bool) or not isinstance(valor, (int, float))
           or (isinstance(valor, float) and not math.isfinite(valor))
           for linha in matriz for valor in linha):
        raise ValueError('Os custos devem ser números reais finitos')
    if any(isinstance(v, float) for linha in matriz for v in linha):
        # Margem para evitar overflow na soma de n custos de ponto flutuante.
        seguro = sys.float_info.max / (n + 1)
        if any(abs(v) > seguro for linha in matriz for v in linha):
            raise ValueError('Custos grandes demais para somar em ponto flutuante')
    if type(fixar_inicio) is not bool or gerador not in ('biblioteca', 'manual'):
        raise ValueError('Modo de enumeração inválido')
    enumerar = itertools.permutations if gerador == 'biblioteca' else permutacoes
    melhor_custo = math.inf
    melhor_rota = None
    rotas = arestas = 0
    for permutacao in enumerar(range(1 if fixar_inicio else 0, n)):
        rota = (0,) + permutacao if fixar_inicio else permutacao
        custo, operacoes = custo_rota(matriz, rota)
        rotas += 1
        arestas += operacoes
        if custo < melhor_custo:
            melhor_custo, melhor_rota = custo, rota
    return melhor_custo, melhor_rota + (melhor_rota[0],), rotas, arestas


def _executar(matriz, conexao):
    try:
        inicio = time.perf_counter()
        resultado = resolver(matriz)
        segundos = time.perf_counter() - inicio
        conexao.send((resultado, segundos))
    finally:
        conexao.close()


def executar_com_limite(matriz, limite):
    contexto = multiprocessing.get_context('spawn')
    leitura, escrita = contexto.Pipe(duplex=False)
    processo = contexto.Process(target=_executar, args=(matriz, escrita))
    processo.start()
    escrita.close()
    try:
        if not leitura.poll(limite):
            return None
        try:
            return leitura.recv()
        except EOFError as erro:
            raise RuntimeError('O processo de cálculo terminou sem resultado') from erro
    finally:
        if processo.is_alive():
            processo.terminate()
        processo.join()
        leitura.close()


def benchmark(max_n=10, repeticoes=3, destino='resultados', limite=90.0):
    if isinstance(max_n, bool) or not isinstance(max_n, int) or not 3 <= max_n <= 20:
        raise ValueError('Use 3 <= max-n <= 20')
    if isinstance(repeticoes, bool) or not isinstance(repeticoes, int) or repeticoes < 1:
        raise ValueError('Use pelo menos uma repetição inteira')
    if not math.isfinite(limite) or limite <= 0:
        raise ValueError('O limite deve ser positivo e finito')
    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    linhas = []
    metadados = dict(inicio_utc=datetime.now(timezone.utc).isoformat(),
                     python=platform.python_version(), sistema=platform.platform(),
                     processador=platform.processor(), semente=42,
                     repeticoes=repeticoes, limite_por_execucao_s=limite,
                     max_n_solicitado=max_n, estado='em andamento')
    arquivo_meta = pasta / 'ambiente.json'
    arquivo_meta.write_text(json.dumps(metadados, indent=2, ensure_ascii=False), encoding='utf-8')
    campos = ['n', 'rotas', 'arestas', 'segundos_mediana', 'segundos_min',
              'segundos_max', 'custo_otimo', 'rota', 'tempos_s']
    with (pasta / 'benchmark.csv').open('w', newline='', encoding='utf-8') as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=campos, lineterminator='\n')
        escritor.writeheader()
        arquivo.flush()
        for n in range(3, max_n + 1):
            matriz = gerar_matriz(n)
            tempos = []
            for repeticao in range(1, repeticoes + 1):
                print(f'n={n}, repetição {repeticao}/{repeticoes}: iniciando', flush=True)
                medicao = executar_com_limite(matriz, limite)
                if medicao is None:
                    metadados.update(estado='limite de tempo', n_interrompido=n,
                                     repeticao_interrompida=repeticao,
                                     repeticoes_concluidas_no_n=tempos,
                                     fim_utc=datetime.now(timezone.utc).isoformat())
                    arquivo_meta.write_text(json.dumps(metadados, indent=2, ensure_ascii=False), encoding='utf-8')
                    print(f'n={n}: processo encerrado após limite de {limite:g} s; '
                          'nenhum ótimo é declarado para a execução interrompida.', flush=True)
                    return linhas
                (custo, rota, rotas, arestas), segundos = medicao
                if rotas != math.factorial(n - 1) or arestas != math.factorial(n):
                    raise RuntimeError('Contagens incompatíveis com a busca completa')
                tempos.append(segundos)
                print(f'Concluído: {segundos:.6f} s', flush=True)
            linha = dict(n=n, rotas=rotas, arestas=arestas,
                         segundos_mediana=statistics.median(tempos),
                         segundos_min=min(tempos), segundos_max=max(tempos),
                         custo_otimo=custo, rota='-'.join(str(v + 1) for v in rota),
                         tempos_s=json.dumps(tempos))
            linhas.append(linha)
            escritor.writerow(linha)
            arquivo.flush()
    metadados.update(estado='concluído', fim_utc=datetime.now(timezone.utc).isoformat())
    arquivo_meta.write_text(json.dumps(metadados, indent=2, ensure_ascii=False), encoding='utf-8')
    return linhas


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-n', type=int, default=10)
    parser.add_argument('--repeticoes', type=int, default=3)
    parser.add_argument('--limite', type=float, default=90,
                        help='Limite em segundos por execução, incluindo início do processo')
    parser.add_argument('--destino', default='resultados')
    args = parser.parse_args()
    try:
        benchmark(args.max_n, args.repeticoes, args.destino, args.limite)
    except ValueError as erro:
        parser.error(str(erro))
