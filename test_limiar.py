import json
import math
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from web.experimentos import Gerenciador

from relatorio import gerar


class RelatorioLimiar(unittest.TestCase):
    def preparar(self, pasta):
        pasta.joinpath('benchmark.csv').write_text(
            'n,segundos_mediana,rotas,arestas,custo_otimo,rota,tempos_s\n3,0.01,2,6,101,1-2-3-1,[0.01]\n', encoding='utf-8')
        pasta.joinpath('ambiente.json').write_text(json.dumps(dict(
            estado='concluído', max_n_solicitado=3, repeticoes=1,
            limite_por_execucao_s=90, python='3.12', sistema='ambiente de teste',
            inicio_utc='2026-11-05T12:00:00+00:00', semente=42)), encoding='utf-8')
        amostras = [dict(n=n, algoritmo='bruta', fixar=True, repeticao=1,
            segundos=tempo, custo=100, rota=list(range(n))+[0], exato=True,
            rotas=math.factorial(n-1), arestas=math.factorial(n)) for n,tempo in ((12,45),(13,600))]
        registro=dict(id='b'*32, titulo='Coleta complementar', inicio='2026-11-05T12:01:00+00:00',
                      estado='concluido', plano_total=2, config={'semente':42}, amostras=amostras,
                      ambiente={'python':'3.12','sistema':'ambiente de teste'})
        pasta.joinpath('complementares').mkdir()
        return registro

    def test_limiar_medido_separado_da_coleta_inicial(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta=Path(tmp)
            registro=self.preparar(pasta)
            pasta.joinpath('complementares/limiar.json').write_text(json.dumps(registro),encoding='utf-8')
            texto=gerar(pasta,pasta/'RELATORIO.md')
            self.assertIn('10,00 minutos',texto)
            self.assertIn('6.227.020.800',texto)
            self.assertIn('não foram incorporados às medianas',texto)
            self.assertIn('12 cidades ficaram abaixo de um minuto',texto)

    def test_contagem_invalida_impede_afirmar_busca_completa(self):
        with tempfile.TemporaryDirectory() as tmp:
            pasta=Path(tmp)
            registro=self.preparar(pasta)
            registro['amostras'][1]['arestas']=1
            pasta.joinpath('complementares/limiar.json').write_text(json.dumps(registro),encoding='utf-8')
            with self.assertRaises(ValueError):
                gerar(pasta,pasta/'RELATORIO.md')

    def test_historico_importa_limiar_sem_substituir_coleta_inicial(self):
        with tempfile.TemporaryDirectory() as tmp:
            raiz=Path(tmp)
            pasta=raiz/'resultados'
            pasta.mkdir()
            registro=self.preparar(pasta)
            pasta.joinpath('complementares/limiar.json').write_text(json.dumps(registro),encoding='utf-8')
            with patch('web.experimentos.RAIZ',raiz):
                gerenciador=Gerenciador(raiz/'execucoes')
                try:
                    self.assertEqual(gerenciador.obter('inicial')['resumo'][0]['n'],3)
                    novo=gerenciador.obter('b'*32)
                    self.assertEqual(novo['titulo'],'Limiar de minutos · coleta complementar')
                    self.assertEqual(max(d['n'] for d in novo['resumo']),13)
                    self.assertIsNone(gerenciador.ativo)
                finally:
                    gerenciador.fechar()


if __name__ == '__main__':
    unittest.main()
