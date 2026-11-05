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


class TestValidacao(unittest.TestCase):
    def test_matriz_pequena(self):
        for matriz in ([], [[0]], [[0, 1], [1, 0]]):
            with self.subTest(matriz=matriz), self.assertRaises(ValueError):
                resolver(matriz)

    def test_matriz_nao_quadrada(self):
        with self.assertRaises(ValueError):
            resolver([[0, 1, 2], [1, 0], [2, 1, 0]])

    def test_custos_invalidos(self):
        for valor in (float('nan'), float('inf'), -float('inf'), 1.7e308, '2', None, True):
            matriz = gerar_matriz(3)
            matriz[0][1] = valor
            with self.subTest(valor=valor), self.assertRaises(ValueError):
                resolver(matriz)

    def test_tamanho_gerador_invalido(self):
        for n in (-1, 0, 2, 3.5, True):
            with self.subTest(n=n), self.assertRaises(ValueError):
                gerar_matriz(n)

    def test_semente_reproduzivel(self):
        self.assertEqual(gerar_matriz(8), gerar_matriz(8))
        self.assertNotEqual(gerar_matriz(8, 1), gerar_matriz(8, 2))

    def test_propriedades_matriz(self):
        matriz = gerar_matriz(9)
        for i in range(9):
            self.assertEqual(matriz[i][i], 0)
            for j in range(i + 1, 9):
                self.assertEqual(matriz[i][j], matriz[j][i])
                self.assertTrue(1 <= matriz[i][j] <= 100)

    def test_custos_zero(self):
        self.assertEqual(resolver([[0] * 4 for _ in range(4)])[0], 0)

    def test_custos_negativos(self):
        self.assertEqual(resolver([[0, -1, -1], [-1, 0, -1], [-1, -1, 0]])[0], -3)

        grande = 10 ** 400
        self.assertEqual(resolver([[0, grande, grande], [grande, 0, grande],
                                   [grande, grande, 0]])[0], 3 * grande)

    def test_custos_fracionarios(self):
        self.assertAlmostEqual(resolver([[0, .5, .5], [.5, 0, .5], [.5, .5, 0]])[0], 1.5)

    def test_entrada_nao_modificada(self):
        import copy
        matriz = gerar_matriz(5)
        original = copy.deepcopy(matriz)
        resolver(matriz)
        self.assertEqual(matriz, original)

    def test_empate_deterministico(self):
        matriz = [[0 if i == j else 1 for j in range(4)] for i in range(4)]
        self.assertEqual(resolver(matriz)[1], (0, 1, 2, 3, 0))

    def test_sem_fixacao(self):
        from itertools import permutations
        matriz = gerar_matriz(5)
        resultados = [custo_rota(matriz, rota)[0] for rota in permutations(range(5))]
        custo, _, rotas, _ = resolver(matriz)
        self.assertEqual(len(resultados), 5 * rotas)
        self.assertEqual(min(resultados), custo)

    def test_oraculo_programacao_dinamica(self):
        # Referência independente: Held–Karp por subconjuntos (sem permutações).
        import random
        rng = random.Random(123)
        for n in range(3, 8):
            for caso in range(4):
                matriz = [[0 if i == j else rng.randint(0, 30)
                           for j in range(n)] for i in range(n)]
                dp = {(1 << j, j): matriz[0][j] for j in range(1, n)}
                for mascara in range(1, 1 << n):
                    if mascara & 1:
                        continue
                    for fim in range(1, n):
                        if (mascara, fim) not in dp:
                            continue
                        for proximo in range(1, n):
                            if mascara & (1 << proximo):
                                continue
                            chave = (mascara | (1 << proximo), proximo)
                            valor = dp[mascara, fim] + matriz[fim][proximo]
                            dp[chave] = min(dp.get(chave, math.inf), valor)
                esperado = min(dp[(1 << n) - 2, j] + matriz[j][0] for j in range(1, n))
                custo, rota, _, _ = resolver(matriz)
                with self.subTest(n=n, caso=caso):
                    self.assertEqual(custo, esperado)
                    self.assertEqual(len(rota), n + 1)
                    self.assertEqual(rota[0], 0)
                    self.assertEqual(rota[-1], 0)
                    self.assertEqual(set(rota[:-1]), set(range(n)))
                    self.assertEqual(custo_rota(matriz, rota[:-1])[0], custo)


class TestBenchmark(unittest.TestCase):
    def test_argumentos_invalidos(self):
        from tsp import benchmark
        for kwargs in ({'max_n': 2}, {'max_n': 21}, {'repeticoes': 0},
                       {'limite': 0}, {'limite': float('nan')}, {'repeticoes': 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                benchmark(**kwargs)

    def test_gravacao_resultados(self):
        import csv
        import json
        import tempfile
        from pathlib import Path
        from tsp import benchmark
        with tempfile.TemporaryDirectory() as pasta:
            linhas = benchmark(3, 2, pasta, 10)
            self.assertEqual(len(linhas), 1)
            with (Path(pasta) / 'benchmark.csv').open(encoding='utf-8') as arquivo:
                salvo = list(csv.DictReader(arquivo))
            self.assertEqual(int(salvo[0]['rotas']), 2)
            self.assertEqual(len(json.loads(salvo[0]['tempos_s'])), 2)
            meta = json.loads((Path(pasta) / 'ambiente.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['estado'], 'concluído')

    def test_limite_preserva_resultados(self):
        import json
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tsp import benchmark
        with tempfile.TemporaryDirectory() as pasta:
            with patch('tsp.executar_com_limite', side_effect=[((6, (0, 1, 2, 0), 2, 6), .01), None]):
                linhas = benchmark(4, 1, pasta, 1)
            self.assertEqual(len(linhas), 1)
            meta = json.loads((Path(pasta) / 'ambiente.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['n_interrompido'], 4)
            self.assertEqual(meta['estado'], 'limite de tempo')

    def test_encerramento_real_por_limite(self):
        from tsp import executar_com_limite
        self.assertIsNone(executar_com_limite(gerar_matriz(12), .01))


class TestRelatorio(unittest.TestCase):
    def test_relatorio_e_grafico_com_dados_atuais(self):
        import tempfile
        from pathlib import Path
        from tsp import benchmark
        from grafico import gerar as grafico
        from relatorio import gerar as relatorio
        with tempfile.TemporaryDirectory() as pasta:
            benchmark(3, 1, pasta, 10)
            self.assertGreater(grafico(pasta), 0)
            texto = relatorio(pasta, Path(pasta) / 'relatorio.md')
            self.assertIn('n = 3', texto)
            self.assertIn('repetições igual a 1', texto)
            self.assertTrue((Path(pasta) / 'comparacao.png').is_file())
            self.assertTrue((Path(pasta) / 'comparacao.pdf').is_file())

    def test_relatorio_csv_vazio(self):
        import tempfile
        from pathlib import Path
        from relatorio import gerar
        with tempfile.TemporaryDirectory() as pasta:
            (Path(pasta) / 'benchmark.csv').write_text('n,segundos_mediana\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                gerar(pasta)

    def test_relatorio_interrompido(self):
        import tempfile
        from pathlib import Path
        from unittest.mock import patch
        from tsp import benchmark
        from relatorio import gerar
        with tempfile.TemporaryDirectory() as pasta:
            with patch('tsp.executar_com_limite', side_effect=[((6, (0, 1, 2, 0), 2, 6), .01), None]):
                benchmark(4, 1, pasta, 1)
            texto = gerar(pasta, Path(pasta) / 'relatorio.md')
            self.assertIn('tentativa com n = 4', texto)
            self.assertIn('sem determinar o ótimo', texto)


if __name__ == '__main__':
    unittest.main()
