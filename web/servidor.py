import io
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
import zipfile

from tsp import gerar_matriz
from web.experimentos import Gerenciador, csv_resultados, para_api

ESTATICOS = Path(__file__).resolve().parent / 'static'


class Servidor(ThreadingHTTPServer):
    daemon_threads = True


class Handler(BaseHTTPRequestHandler):
    def log_message(self, formato, *args):
        pass

    def _enviar(self, conteudo, tipo='application/json; charset=utf-8', status=200, nome=None):
        if not isinstance(conteudo, bytes):
            conteudo = conteudo.encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(conteudo)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'")
        if nome:
            self.send_header('Content-Disposition', f'attachment; filename="{nome}"')
        self.end_headers()
        try:
            self.wfile.write(conteudo)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _json(self, valor, status=200):
        self._enviar(json.dumps(para_api(valor), ensure_ascii=False, allow_nan=False), status=status)

    def _local(self):
        permitidos = {f'127.0.0.1:{self.server.server_port}', f'localhost:{self.server.server_port}'}
        host = self.headers.get('Host', '')
        origem = self.headers.get('Origin')
        return host in permitidos and (origem is None or origem == 'http://' + host)

    def do_GET(self):
        if not self._local():
            self._json({'erro': 'Acesso permitido apenas pela origem local.'}, 403)
            return
        partes = urlsplit(self.path).path.strip('/').split('/')
        caminho = urlsplit(self.path).path
        estaticos = {'/': ('index.html', 'text/html; charset=utf-8'),
                     '/app.js': ('app.js', 'text/javascript; charset=utf-8'),
                     '/style.css': ('style.css', 'text/css; charset=utf-8')}
        try:
            if caminho in estaticos:
                nome, tipo = estaticos[caminho]
                self._enviar((ESTATICOS / nome).read_bytes(), tipo)
            elif caminho == '/api/experimentos':
                self._json(self.server.gerenciador.lista())
            elif len(partes) in (3, 4) and partes[:2] == ['api', 'experimentos']:
                r = self.server.gerenciador.obter(partes[2])
                if len(partes) == 3:
                    self._json(r)
                elif partes[3] == 'instancia':
                    from urllib.parse import parse_qs
                    query = parse_qs(urlsplit(self.path).query)
                    n = int(query.get('n', [r['config']['fim']])[0])
                    if not r['config']['inicio'] <= n <= r['config']['fim']:
                        raise ValueError('Tamanho fora do experimento')
                    self._json({'n': n, 'matriz': gerar_matriz(n, r['config']['semente'])})
                elif partes[3] == 'csv':
                    self._enviar(csv_resultados(r), 'text/csv; charset=utf-8', nome='tsp-amostras.csv')
                elif partes[3] == 'zip':
                    buffer = io.BytesIO()
                    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as pacote:
                        pacote.writestr('experimento.json', json.dumps(r, ensure_ascii=False, indent=2))
                        pacote.writestr('amostras.csv', csv_resultados(r))
                        matrizes = {str(n): gerar_matriz(n, r['config']['semente'])
                                    for n in sorted({a['n'] for a in r['amostras']})}
                        pacote.writestr('matrizes.json', json.dumps(matrizes))
                    self._enviar(buffer.getvalue(), 'application/zip', nome='tsp-experimento.zip')
                else:
                    self._json({'erro': 'Recurso não encontrado'}, 404)
            else:
                self._json({'erro': 'Recurso não encontrado'}, 404)
        except KeyError:
            self._json({'erro': 'Experimento não encontrado'}, 404)
        except (ValueError, TypeError):
            self._json({'erro': 'Parâmetro inválido'}, 400)

    def do_POST(self):
        if not self._local() or self.headers.get('X-TSP-Request') != '1':
            self._json({'erro': 'Solicitação local inválida'}, 403)
            return
        if self.headers.get('Content-Type', '').split(';')[0] != 'application/json':
            self._json({'erro': 'Use conteúdo JSON'}, 415)
            return
        try:
            tamanho = int(self.headers.get('Content-Length', '0'))
            if not 0 < tamanho <= 4096:
                raise ValueError('Solicitação vazia ou grande demais')
            dados = json.loads(self.rfile.read(tamanho))
            caminho = urlsplit(self.path).path
            partes = caminho.strip('/').split('/')
            if caminho == '/api/experimentos':
                self._json({'id': self.server.gerenciador.iniciar(dados)}, 201)
            elif len(partes) == 4 and partes[:2] == ['api', 'experimentos'] and partes[3] == 'cancelar':
                self.server.gerenciador.cancelar(partes[2])
                self._json({'mensagem': 'Cancelamento solicitado'})
            else:
                self._json({'erro': 'Recurso não encontrado'}, 404)
        except (ValueError, TypeError, UnicodeDecodeError) as erro:
            self._json({'erro': str(erro)}, 400)
        except RuntimeError as erro:
            self._json({'erro': str(erro)}, 409)


def criar_servidor(porta=5000, pasta=None, importar_inicial=True):
    servidor = Servidor(('127.0.0.1', porta), Handler)
    try:
        servidor.gerenciador = Gerenciador(pasta or ESTATICOS.parents[1] / 'experimentos', importar_inicial)
    except Exception:
        servidor.server_close()
        raise
    return servidor
