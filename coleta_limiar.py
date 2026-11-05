"""Mede instâncias de 12 e 13 cidades para observar o limiar de minutos."""
import argparse
import json
import multiprocessing
from pathlib import Path
import time

from web.experimentos import Gerenciador, csv_resultados


def coletar(destino='resultados/complementares', limite=3600):
    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    gerenciador = Gerenciador(pasta / 'execucoes', importar_inicial=False)
    inicio = time.monotonic()
    try:
        identificador = gerenciador.iniciar(dict(tipo='benchmark', inicio=12, fim=13,
            repeticoes=1, limite=limite, semente=42, gerador='biblioteca'))
        proximo_aviso = 0
        concluidas = -1
        while True:
            registro = gerenciador.obter(identificador)
            decorrido = time.monotonic() - inicio
            if len(registro['amostras']) != concluidas or decorrido >= proximo_aviso:
                concluidas = len(registro['amostras'])
                print(f"{decorrido:.0f} s decorridos; {concluidas}/2 chamadas concluídas; "
                      f"{registro['mensagem']}", flush=True)
                for a in registro['amostras']:
                    print(f"n={a['n']}: {a['segundos']:.6f} s; custo {a['custo']}; "
                          f"{a['rotas']} rotas; {a['arestas']} arestas", flush=True)
                proximo_aviso = decorrido + 30
            if registro['estado'] != 'executando':
                break
            time.sleep(.5)
        if registro['estado'] != 'concluido':
            raise RuntimeError(registro['mensagem'])
        (pasta / 'limiar.json').write_text(json.dumps(registro, ensure_ascii=False, indent=2), encoding='utf-8')
        (pasta / 'limiar.csv').write_text(csv_resultados(registro), encoding='utf-8')
    finally:
        gerenciador.fechar()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', default='resultados/complementares')
    parser.add_argument('--limite', type=int, default=3600)
    args = parser.parse_args()
    coletar(args.destino, args.limite)
