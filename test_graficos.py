import json
from pathlib import Path
import tempfile
import unittest

from catalogo_graficos import GRAFICOS
from grafico import carregar_complementar, gerar


class Graficos(unittest.TestCase):
    def test_coleta_incompleta_nao_vira_grafico(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / 'complementares').mkdir()
            (pasta / 'complementares/origem.json').write_text(
                json.dumps({'estado':'cancelado'}), encoding='utf-8')
            with self.assertRaises(ValueError):
                carregar_complementar(pasta, 'origem')

    def test_contagem_divergente(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / 'benchmark.csv').write_text(
                'n,segundos_mediana,rotas,arestas\n3,0.01,99,6\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                gerar(pasta)

    def test_seis_graficos_com_fontes_separadas(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta = Path(tmp)
            (pasta / 'benchmark.csv').write_text(
                'n,segundos_mediana,rotas,arestas\n3,0.01,2,6\n4,0.04,6,24\n', encoding='utf-8')
            complemento = pasta / 'complementares'
            complemento.mkdir()
            def amostra(algoritmo='bruta', fixar=True, segundos=.01):
                return dict(n=3, algoritmo=algoritmo, fixar=fixar, segundos=segundos,
                            custo=6, rota=[0,1,2,0], exato=algoritmo != 'guloso',
                            rotas=(2 if fixar else 6) if algoritmo == 'bruta' else None,
                            arestas=(6 if fixar else 18) if algoritmo == 'bruta' else None)
            for nome, amostras in (
                ('origem', [amostra(), amostra(fixar=False, segundos=.03)]),
                ('metodos', [amostra(), amostra('held_karp', segundos=.005), amostra('guloso', segundos=.001)])):
                (complemento / f'{nome}.json').write_text(json.dumps(dict(
                    estado='concluido', plano_total=len(amostras), amostras=amostras)), encoding='utf-8')
            gerar(pasta)
            for nome, _, _ in GRAFICOS:
                arquivo = pasta / 'graficos' / nome
                self.assertGreater(arquivo.stat().st_size, 1000)
                self.assertEqual(arquivo.read_bytes()[:8], b'\x89PNG\r\n\x1a\n')
            (complemento / 'origem.json').unlink()
            (complemento / 'metodos.json').unlink()
            gerar(pasta)
            self.assertEqual(len(list((pasta / 'graficos').glob('*.png'))), 4)


if __name__ == '__main__':
    unittest.main()
