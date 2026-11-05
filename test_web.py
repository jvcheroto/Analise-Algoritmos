import csv
import http.client
import io
import itertools
import json
from pathlib import Path
import tempfile
import threading
import time
import unittest
import zipfile

from algoritmos import calcular, held_karp, vizinho_proximo
from tsp import gerar_matriz, permutacoes, resolver
from web.experimentos import Gerenciador, configuracao, csv_resultados, para_api, planejar
from web.servidor import criar_servidor


def aguardar(gerenciador, identificador, prazo=10):
    fim = time.monotonic() + prazo
    while time.monotonic() < fim:
        registro = gerenciador.obter(identificador)
        if registro['estado'] != 'executando':
            return registro
        time.sleep(.02)
    raise AssertionError('A execução não terminou dentro do prazo do teste')


class Algoritmos(unittest.TestCase):
    def test_permutacoes_por_trocas(self):
        for n in range(7):
            entrada = list(range(n))
            geradas = list(permutacoes(entrada))
            self.assertEqual(set(geradas), set(itertools.permutations(entrada)))
            self.assertEqual(len(geradas), len(set(geradas)))
            self.assertEqual(entrada, list(range(n)))

    def test_origem_livre_e_manual(self):
        matriz = gerar_matriz(5)
        fixo = resolver(matriz)
        for gerador in ('biblioteca', 'manual'):
            livre = resolver(matriz, False, gerador)
            manual = resolver(matriz, True, gerador)
            self.assertEqual(livre[0], fixo[0])
            self.assertEqual(manual[0], fixo[0])
            self.assertEqual(livre[2], 5 * fixo[2])
            self.assertEqual(livre[3], 5 * fixo[3])
            self.assertEqual(livre[1][0], livre[1][-1])

    def test_held_karp_coincide_com_forca_bruta(self):
        for n in range(3, 9):
            matriz = gerar_matriz(n)
            custo, rota = held_karp(matriz)
            self.assertEqual(custo, resolver(matriz)[0])
            self.assertEqual(rota[0], rota[-1])
            self.assertEqual(sorted(rota[:-1]), list(range(n)))

    def test_held_karp_assimetrico(self):
        matriz = [[0, 1, 9], [9, 0, 2], [3, 9, 0]]
        self.assertEqual(held_karp(matriz), (6, (0, 1, 2, 0)))

    def test_guloso_nao_garante_otimo(self):
        matriz = [[0, 1, 2, 3], [1, 0, 4, 5], [2, 4, 0, 100], [3, 5, 100, 0]]
        self.assertEqual(vizinho_proximo(matriz)[0], 108)
        self.assertEqual(held_karp(matriz)[0], 14)
        resultado = calcular(matriz, 'guloso')
        self.assertFalse(resultado['exato'])
        self.assertIsNone(resultado['rotas'])
        self.assertIsNone(resultado['arestas'])

    def test_configuracoes_invalidas(self):
        for dados in (None, [], {'fim':17}, {'fim':True}, {'inicio':5,'fim':4},
                      {'limite':0}, {'repeticoes':11}, {'gerador':'x'},
                      {'comparar_origem':'sim'}, {'extra':1}, {'tipo':'outro'},
                      {'tipo':'comparacao','fim':13}):
            with self.subTest(dados=dados), self.assertRaises(ValueError):
                configuracao(dados)

    def test_planejamento_e_teto_livre(self):
        c = configuracao({'inicio':8,'fim':10,'repeticoes':2,'comparar_origem':True})
        plano = planejar(c)
        self.assertEqual(len(plano),10)
        self.assertTrue(all(d['n'] <= 9 for d in plano if not d['fixar']))
        comparacao = planejar(configuracao({'tipo':'comparacao','fim':5,'repeticoes':2}))
        self.assertEqual(len(comparacao),6)
        self.assertEqual({d['algoritmo'] for d in comparacao}, {'bruta','held_karp','guloso'})

    def test_contagens_grandes_na_api(self):
        valor = para_api({'rotas':10**20, 'arestas':None, 'n':20, 'itens':[{'arestas':10**21}]})
        self.assertEqual(valor['rotas'],str(10**20))
        self.assertIsNone(valor['arestas'])
        self.assertEqual(valor['n'],20)
        self.assertEqual(valor['itens'][0]['arestas'],str(10**21))


class Execucoes(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.g = Gerenciador(self.tmp.name, importar_inicial=False)

    def tearDown(self):
        self.g.fechar()
        self.tmp.cleanup()

    def test_execucao_persistencia_e_csv(self):
        identificador = self.g.iniciar({'inicio':3,'fim':4,'repeticoes':2,'comparar_origem':True})
        r = aguardar(self.g, identificador)
        self.assertEqual(r['estado'],'concluido',r['mensagem'])
        self.assertEqual(len(r['amostras']),8)
        self.assertEqual(len(r['resumo']),4)
        self.assertGreater(r['constante'],0)
        self.assertEqual(len(list(csv.DictReader(io.StringIO(csv_resultados(r)),delimiter=';'))),8)
        nova = Gerenciador(self.tmp.name, importar_inicial=False)
        try:
            self.assertEqual(nova.obter(identificador)['amostras'],r['amostras'])
        finally:
            nova.fechar()

    def test_comparacao_sem_contagens_inventadas(self):
        r = aguardar(self.g, self.g.iniciar({'tipo':'comparacao','fim':5,'repeticoes':1,'gerador':'manual'}))
        self.assertEqual(r['estado'],'concluido',r['mensagem'])
        bruta, hk, guloso = r['resumo']
        self.assertEqual(bruta['custo'],hk['custo'])
        self.assertGreaterEqual(guloso['custo'],bruta['custo'])
        self.assertIsNone(hk['arestas'])

    def test_cancelamento_e_concorrencia(self):
        identificador = self.g.iniciar({'inicio':13,'fim':13,'repeticoes':1})
        with self.assertRaises(RuntimeError):
            self.g.iniciar({'fim':3})
        self.g.cancelar(identificador)
        r = aguardar(self.g,identificador)
        self.assertEqual(r['estado'],'cancelado')
        self.assertEqual(r['amostras'],[])

    def test_limite_de_tempo(self):
        r = aguardar(self.g,self.g.iniciar({'inicio':13,'fim':13,'repeticoes':1,'limite':1}))
        self.assertEqual(r['estado'],'limite')
        self.assertEqual(r['amostras'],[])
        self.assertEqual(r['atual']['n'],13)

    def test_reinicio_nao_reinicia_calculo(self):
        identificador='a'*32
        registro=dict(id=identificador, estado='executando', amostras=[], titulo='Teste', inicio='2026-11-05', plano_total=1)
        Path(self.tmp.name,identificador+'.json').write_text(json.dumps(registro),encoding='utf-8')
        nova = Gerenciador(self.tmp.name, importar_inicial=False)
        try:
            self.assertEqual(nova.lista()[0]['estado'],'interrompido')
            self.assertIsNone(nova.ativo)
        finally:
            nova.fechar()

    def test_coleta_inicial_somente_leitura(self):
        g = Gerenciador(self.tmp.name)
        try:
            r=g.obter('inicial')
            self.assertEqual(len(r['amostras']),30)
            self.assertEqual(max(d['n'] for d in r['resumo']),12)
            self.assertEqual(list(Path(self.tmp.name).glob('inicial*')),[])
        finally:
            g.fechar()

    def test_fechamento_encerra_calculo(self):
        identificador=self.g.iniciar({'inicio':13,'fim':13,'repeticoes':1})
        self.g.fechar()
        self.assertEqual(self.g.obter(identificador)['estado'],'cancelado')
        self.assertFalse(self.g.thread.is_alive())


class HTTP(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.servidor=criar_servidor(0,self.tmp.name,importar_inicial=False)
        self.thread=threading.Thread(target=self.servidor.serve_forever,daemon=True)
        self.thread.start()
        self.porta=self.servidor.server_port

    def tearDown(self):
        self.servidor.gerenciador.fechar()
        self.servidor.shutdown()
        self.thread.join(timeout=5)
        self.servidor.server_close()
        self.tmp.cleanup()

    def chamar(self,caminho,metodo='GET',dados=None,headers=None):
        conexao=http.client.HTTPConnection('127.0.0.1',self.porta,timeout=5)
        cabecalhos={'Content-Type':'application/json','X-TSP-Request':'1'}
        cabecalhos.update(headers or {})
        conexao.request(metodo,caminho,json.dumps(dados) if dados is not None else None,cabecalhos)
        resposta=conexao.getresponse()
        status=resposta.status
        corpo=resposta.read()
        conexao.close()
        return status,corpo

    def test_pagina_e_arquivos_locais(self):
        for caminho in ('/','/app.js','/style.css'):
            status,corpo=self.chamar(caminho)
            self.assertEqual(status,200)
            self.assertGreater(len(corpo),100)
        self.assertEqual(self.chamar('/../../tsp.py')[0],404)

    def test_origem_e_host(self):
        self.assertEqual(self.chamar('/api/experimentos',headers={'Host':'exemplo.com'})[0],403)
        self.assertEqual(self.chamar('/api/experimentos','POST',{}, {'Origin':'https://exemplo.com'})[0],403)
        self.assertEqual(self.chamar('/api/experimentos','POST',{}, {'X-TSP-Request':''})[0],403)

    def test_dados_invalidos(self):
        self.assertEqual(self.chamar('/api/experimentos','POST',{'fim':100})[0],400)
        self.assertEqual(self.chamar('/api/experimentos/ausente')[0],404)

    def test_fluxo_http_e_exportacao(self):
        status,corpo=self.chamar('/api/experimentos','POST',{'inicio':3,'fim':3,'repeticoes':1})
        self.assertEqual(status,201)
        identificador=json.loads(corpo)['id']
        aguardar(self.servidor.gerenciador,identificador)
        base='/api/experimentos/'+identificador
        status,corpo=self.chamar(base)
        self.assertEqual(status,200)
        r=json.loads(corpo)
        self.assertEqual(r['amostras'][0]['rotas'],'2')
        self.assertEqual(self.chamar(base+'/csv')[0],200)
        status,corpo=self.chamar(base+'/zip')
        self.assertEqual(status,200)
        with zipfile.ZipFile(io.BytesIO(corpo)) as pacote:
            self.assertEqual(set(pacote.namelist()),{'experimento.json','amostras.csv','matrizes.json'})
            self.assertEqual(json.loads(pacote.read('experimento.json'))['id'],identificador)
        self.assertEqual(self.chamar(base+'/instancia?n=3')[0],200)
        self.assertEqual(self.chamar(base+'/instancia?n=20')[0],400)


if __name__ == '__main__':
    unittest.main()
