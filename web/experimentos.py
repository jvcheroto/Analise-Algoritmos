"""Execução sequencial, cancelamento e armazenamento dos experimentos locais."""
import copy
import csv
from datetime import datetime, timezone
import io
import json
import math
import multiprocessing
from pathlib import Path
import platform
import statistics
import threading
import time
import uuid

from algoritmos import calcular
from tsp import gerar_matriz

RAIZ = Path(__file__).resolve().parents[1]
TERMINAIS = {'concluido', 'cancelado', 'limite', 'erro', 'interrompido'}


def agora():
    return datetime.now(timezone.utc).isoformat()


def configuracao(dados):
    if not isinstance(dados, dict):
        raise ValueError('Informe a configuração do experimento')
    campos = {'tipo', 'inicio', 'fim', 'repeticoes', 'limite', 'semente', 'comparar_origem', 'gerador'}
    if set(dados) - campos:
        raise ValueError('A configuração contém campos desconhecidos')
    tipo = dados.get('tipo', 'benchmark')
    if tipo not in ('demo', 'benchmark', 'comparacao'):
        raise ValueError('Escolha um tipo de experimento válido')

    def inteiro(chave, padrao, minimo, maximo):
        valor = dados.get(chave, padrao)
        if type(valor) is not int or not minimo <= valor <= maximo:
            raise ValueError(f'{chave}: use um inteiro entre {minimo} e {maximo}')
        return valor

    c = dict(tipo=tipo, inicio=inteiro('inicio', 3, 3, 16),
             fim=inteiro('fim', 8, 3, 16),
             repeticoes=inteiro('repeticoes', 3, 1, 10),
             semente=inteiro('semente', 42, -1000000000, 1000000000),
             limite=inteiro('limite', 90, 1, 3600),
             comparar_origem=dados.get('comparar_origem', False),
             gerador=dados.get('gerador', 'biblioteca'))
    if type(c['comparar_origem']) is not bool:
        raise ValueError('A comparação da origem deve ser verdadeira ou falsa')
    if c['gerador'] not in ('biblioteca', 'manual'):
        raise ValueError('Escolha um gerador de permutações válido')
    if c['inicio'] > c['fim']:
        raise ValueError('O tamanho inicial deve ser menor ou igual ao final')
    if tipo != 'benchmark':
        if c['fim'] > 12:
            raise ValueError('Demonstrações e comparação de métodos aceitam até 12 cidades')
        c['inicio'] = c['fim']
        c['comparar_origem'] = False
    return c


def planejar(c):
    plano = []
    for n in range(c['inicio'], c['fim'] + 1):
        metodos = [('bruta', True)]
        if c['tipo'] == 'comparacao':
            metodos += [('held_karp', True), ('guloso', True)]
        elif c['comparar_origem'] and n <= 9:
            metodos += [('bruta', False)]
        for algoritmo, fixar in metodos:
            plano.extend(dict(n=n, algoritmo=algoritmo, fixar=fixar, repeticao=rep)
                         for rep in range(1, c['repeticoes'] + 1))
    return plano


def _worker(matriz, item, gerador, conexao):
    try:
        inicio = time.perf_counter()
        resultado = calcular(matriz, item['algoritmo'], item['fixar'], gerador)
        resultado['segundos'] = time.perf_counter() - inicio
        conexao.send({'resultado': resultado})
    except Exception as erro:
        conexao.send({'erro': f'{type(erro).__name__}: {erro}'})
    finally:
        conexao.close()


def resumo(amostras):
    grupos = {}
    for a in amostras:
        grupos.setdefault((a['n'], a['algoritmo'], a['fixar']), []).append(a)
    linhas = []
    for (n, algoritmo, fixar), grupo in grupos.items():
        tempos = [a['segundos'] for a in grupo]
        ultima = grupo[-1]
        linhas.append(dict(n=n, algoritmo=algoritmo, fixar=fixar, repeticoes=len(grupo),
                           mediana=statistics.median(tempos), minimo=min(tempos), maximo=max(tempos),
                           custo=ultima['custo'], rota=ultima['rota'], exato=ultima['exato'],
                           rotas=ultima['rotas'], arestas=ultima['arestas']))
    return linhas


def verificar(resultado, matriz, item):
    n = len(matriz)
    rota = resultado['rota']
    if (len(rota) != n + 1 or rota[0] != rota[-1]
            or sorted(rota[:-1]) != list(range(n))
            or (item['fixar'] and rota[0] != 0)):
        raise ValueError('A execução retornou um circuito inválido')
    custo = sum(matriz[rota[i]][rota[i + 1]] for i in range(n))
    if custo != resultado['custo'] or not math.isfinite(resultado['segundos']) or resultado['segundos'] < 0:
        raise ValueError('Custo ou tempo inconsistente')
    if item['algoritmo'] == 'bruta':
        rotas = math.factorial(n - 1 if item['fixar'] else n)
        if resultado['rotas'] != rotas or resultado['arestas'] != n * rotas:
            raise ValueError('A busca não corresponde às contagens esperadas')


class Gerenciador:
    def __init__(self, pasta, importar_inicial=True):
        self.pasta = Path(pasta)
        self.pasta.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.cancelar_evento = threading.Event()
        self.thread = None
        self.ativo = None
        self.encerrando = False
        self.registros = {}
        for arquivo in sorted(self.pasta.glob('*.json')):
            try:
                registro = json.loads(arquivo.read_text(encoding='utf-8'))
                identificador = registro['id']
                uuid.UUID(identificador)
                if registro['estado'] not in TERMINAIS:
                    registro.update(estado='interrompido', mensagem='Execução interrompida antes do reinício.', fim=agora())
                self.registros[identificador] = registro
                self._salvar(registro)
            except (ValueError, KeyError, TypeError):
                # Arquivos danificados permanecem no disco para inspeção.
                continue
        if importar_inicial:
            self._importar()

    def _importar(self):
        arquivo = RAIZ / 'resultados' / 'benchmark.csv'
        if not arquivo.exists():
            return
        with arquivo.open(encoding='utf-8') as f:
            linhas = list(csv.DictReader(f))
        meta = json.loads((RAIZ / 'resultados' / 'ambiente.json').read_text(encoding='utf-8'))
        amostras = []
        for d in linhas:
            rota = [int(v) - 1 for v in d['rota'].split('-')]
            for rep, segundos in enumerate(json.loads(d['tempos_s']), 1):
                amostras.append(dict(n=int(d['n']), algoritmo='bruta', fixar=True,
                    repeticao=rep, segundos=segundos, custo=int(d['custo_otimo']), rota=rota,
                    exato=True, rotas=int(d['rotas']), arestas=int(d['arestas'])))
        self.registros['inicial'] = dict(id='inicial', estado={'limite de tempo':'limite', 'concluído':'concluido'}.get(meta['estado'], 'interrompido'),
            titulo='Coleta inicial · ambiente em nuvem', inicio=meta['inicio_utc'], fim=meta.get('fim_utc'),
            config=dict(tipo='benchmark', inicio=3, fim=meta['max_n_solicitado'], repeticoes=meta['repeticoes'],
                        semente=meta['semente'], limite=meta['limite_por_execucao_s'], comparar_origem=False, gerador='biblioteca'),
            ambiente=meta, amostras=amostras, plano_total=(meta['max_n_solicitado'] - 2) * meta['repeticoes'],
            mensagem='Resultados preservados do experimento original; não foram recalculados pela interface.', atual=None)

    def _salvar(self, registro):
        caminho = self.pasta / (registro['id'] + '.json')
        temporario = caminho.with_suffix('.tmp')
        temporario.write_text(json.dumps(registro, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        temporario.replace(caminho)

    def lista(self):
        with self.lock:
            return [dict(id=r['id'], titulo=r['titulo'], estado=r['estado'], inicio=r['inicio'],
                         concluidas=len(r['amostras']), total=r['plano_total'])
                    for r in sorted(self.registros.values(), key=lambda x: x['inicio'], reverse=True)]

    def obter(self, identificador):
        with self.lock:
            if identificador not in self.registros:
                raise KeyError('Experimento não encontrado')
            r = copy.deepcopy(self.registros[identificador])
        r['resumo'] = resumo(r['amostras'])
        fixos = [d for d in r['resumo'] if d['algoritmo'] == 'bruta' and d['fixar']]
        maior = max(fixos, key=lambda d: d['n']) if fixos else None
        r['constante'] = maior['mediana'] / math.factorial(maior['n']) if maior else None
        r['calibracao_n'] = maior['n'] if maior else None
        r['projecoes'] = [dict(n=n, segundos=r['constante'] * math.factorial(n))
                          for n in range(maior['n'] + 1, maior['n'] + 4)] if maior else []
        return r

    def iniciar(self, dados):
        c = configuracao(dados)
        plano = planejar(c)
        with self.lock:
            if self.encerrando or self.ativo is not None:
                raise RuntimeError('Há um experimento em andamento. Aguarde ou cancele antes de iniciar outro.')
            identificador = uuid.uuid4().hex
            registro = dict(id=identificador, titulo={'demo': 'Demonstração de rota', 'benchmark': 'Crescimento fatorial',
                'comparacao': 'Comparação de métodos'}[c['tipo']], estado='executando', inicio=agora(), fim=None,
                config=c, ambiente=dict(python=platform.python_version(), sistema=platform.platform(),
                cronometro='perf_counter somente no cálculo, incluindo validações e contadores; sem aquecimento'),
                amostras=[], plano_total=len(plano), atual=None, mensagem='Preparando o experimento.')
            self.registros[identificador] = registro
            self._salvar(registro)
            self.ativo = identificador
            self.cancelar_evento.clear()
            self.thread = threading.Thread(target=self._rodar, args=(identificador, plano), daemon=True)
            self.thread.start()
            return identificador

    def cancelar(self, identificador):
        with self.lock:
            if self.ativo != identificador:
                raise RuntimeError('Esse experimento não está em execução')
            self.cancelar_evento.set()
            self.registros[identificador]['mensagem'] = 'Encerrando a execução atual...'

    def _chamada(self, matriz, item, c):
        contexto = multiprocessing.get_context('spawn')
        leitura, escrita = contexto.Pipe(duplex=False)
        processo = contexto.Process(target=_worker, args=(matriz, item, c['gerador'], escrita))
        processo.start()
        escrita.close()
        prazo = time.monotonic() + c['limite']
        try:
            while True:
                if self.cancelar_evento.is_set():
                    return None, 'cancelado'
                if leitura.poll(0.05):
                    resposta = leitura.recv()
                    if self.cancelar_evento.is_set():
                        return None, 'cancelado'
                    if 'erro' in resposta:
                        raise RuntimeError(resposta['erro'])
                    return resposta['resultado'], None
                if time.monotonic() >= prazo:
                    return None, 'limite'
                if not processo.is_alive():
                    raise RuntimeError('O processo terminou sem resultado')
        finally:
            if processo.is_alive():
                processo.terminate()
            processo.join()
            leitura.close()

    def _rodar(self, identificador, plano):
        r = self.registros[identificador]
        c = r['config']
        estado = 'concluido'
        mensagem = 'Todas as chamadas planejadas foram concluídas.'
        try:
            for item in plano:
                with self.lock:
                    r['atual'] = item
                    r['mensagem'] = f"Calculando n={item['n']}, repetição {item['repeticao']}..."
                matriz = gerar_matriz(item['n'], c['semente'])
                resultado, motivo = self._chamada(matriz, item, c)
                if motivo:
                    estado = motivo
                    mensagem = ('Cancelado. As chamadas concluídas foram preservadas.' if motivo == 'cancelado'
                                else f"Limite de {c['limite']} s atingido em n={item['n']}; a chamada atual não foi concluída.")
                    break
                verificar(resultado, matriz, item)
                with self.lock:
                    r['amostras'].append(dict(**item, **resultado))
                    self._salvar(r)
        except Exception as erro:
            estado, mensagem = 'erro', f'{type(erro).__name__}: {erro}'
        finally:
            with self.lock:
                r.update(estado=estado, fim=agora(), mensagem=mensagem)
                try:
                    self._salvar(r)
                except OSError as erro:
                    r.update(estado='erro', mensagem=f'Falha ao salvar: {erro}')
                self.ativo = None

    def fechar(self):
        with self.lock:
            self.encerrando = True
            self.cancelar_evento.set()
            thread = self.thread
        if thread:
            thread.join(timeout=10)


def csv_resultados(registro):
    campos = ['n', 'algoritmo', 'fixar', 'repeticao', 'segundos', 'custo', 'exato', 'rotas', 'arestas', 'rota']
    saida = io.StringIO(newline='')
    escritor = csv.DictWriter(saida, fieldnames=campos, delimiter=';', lineterminator='\n')
    escritor.writeheader()
    for a in registro['amostras']:
        linha = {k: a[k] for k in campos}
        linha['rota'] = ' → '.join(str(v + 1) for v in a['rota'])
        escritor.writerow(linha)
    return saida.getvalue()


def para_api(valor, chave=''):
    if isinstance(valor, dict):
        return {k: para_api(v, k) for k, v in valor.items()}
    if isinstance(valor, list):
        return [para_api(v, chave) for v in valor]
    if chave in ('rotas', 'arestas') and valor is not None:
        return str(valor)
    return valor
