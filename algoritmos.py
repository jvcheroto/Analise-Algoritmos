from functools import lru_cache
from tsp import custo_rota, resolver


def validar(matriz):
    n = len(matriz)
    if n < 3 or any(len(linha) != n for linha in matriz):
        raise ValueError('Matriz quadrada com pelo menos três cidades exigida')


def held_karp(matriz):
    """Programação dinâmica exata: O(n² 2ⁿ) em tempo, O(n 2ⁿ) em memória."""
    validar(matriz)
    n = len(matriz)

    @lru_cache(None)
    def restante(atual, mascara):
        if mascara == 0:
            return matriz[atual][0]
        return min(matriz[atual][cidade] + restante(cidade, mascara ^ (1 << cidade))
                   for cidade in range(1, n) if mascara & (1 << cidade))

    mascara = (1 << n) - 2
    valor = restante(0, mascara)
    rota = [0]
    while mascara:
        atual = rota[-1]
        proxima = min((v for v in range(1, n) if mascara & (1 << v)),
                      key=lambda v: (matriz[atual][v] + restante(v, mascara ^ (1 << v)), v))
        rota.append(proxima)
        mascara ^= 1 << proxima
    return valor, tuple(rota + [0])


def vizinho_proximo(matriz):
    """Heurística gulosa O(n²), sem garantia de custo mínimo."""
    validar(matriz)
    rota = [0]
    livres = set(range(1, len(matriz)))
    while livres:
        proxima = min(livres, key=lambda v: (matriz[rota[-1]][v], v))
        rota.append(proxima)
        livres.remove(proxima)
    custo, _ = custo_rota(matriz, rota)
    return custo, tuple(rota + [0])


def calcular(matriz, algoritmo='bruta', fixar=True, gerador='biblioteca'):
    if algoritmo == 'bruta':
        custo, rota, rotas, arestas = resolver(matriz, fixar, gerador)
    elif algoritmo in ('held_karp', 'guloso'):
        custo, rota = (held_karp if algoritmo == 'held_karp' else vizinho_proximo)(matriz)
        rotas = arestas = None
    else:
        raise ValueError('Algoritmo desconhecido')
    return dict(custo=custo, rota=list(rota), rotas=rotas, arestas=arestas,
                exato=algoritmo != 'guloso')
