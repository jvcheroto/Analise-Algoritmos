import math
import unittest
from tsp import custo_rota, gerar_matriz, resolver


class TestTSP(unittest.TestCase):
    def test_otimo_conhecido(self):
        matriz = [[0, 10, 15, 20], [10, 0, 35, 25],
                  [15, 35, 0, 30], [20, 25, 30, 0]]
        custo, rota, rotas, arestas = resolver(matriz)
        self.assertEqual(custo, 80)
        self.assertEqual(rota[0], rota[-1])
        self.assertEqual(set(rota[:-1]), set(range(4)))
        self.assertEqual((rotas, arestas), (6, 24))

    def test_fechamento_assimetrico(self):
        matriz = [[0, 1, 9], [9, 0, 2], [3, 9, 0]]
        self.assertEqual(custo_rota(matriz, (0, 1, 2)), (6, 3))
        self.assertEqual(resolver(matriz)[0], 6)

    def test_contagens(self):
        for n in range(3, 8):
            _, _, rotas, arestas = resolver(gerar_matriz(n))
            self.assertEqual(rotas, math.factorial(n - 1))
            self.assertEqual(arestas, math.factorial(n))

    def test_greedy_nao_garante_otimo(self):
        matriz = [[0, 1, 2, 3], [1, 0, 4, 5],
                  [2, 4, 0, 100], [3, 5, 100, 0]]
        self.assertEqual(custo_rota(matriz, (0, 1, 2, 3))[0], 108)
        self.assertEqual(resolver(matriz)[0], 14)


if __name__ == '__main__':
    unittest.main()
