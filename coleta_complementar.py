"""Coletas para comparar a fixação da origem e os métodos de solução."""
import argparse
import json
import multiprocessing
from pathlib import Path
import time

from web.experimentos import Gerenciador, csv_resultados


def coletar(destino='resultados/complementares', limite=90):
    pasta = Path(destino)
    pasta.mkdir(parents=True, exist_ok=True)
    gerenciador = Gerenciador(pasta / 'execucoes', importar_inicial=False)
    configuracoes = (
        ('origem', dict(tipo='benchmark', inicio=3, fim=9, repeticoes=3,
                       limite=limite, comparar_origem=True, semente=42)),
        ('metodos', dict(tipo='comparacao', fim=10, repeticoes=3,
                        limite=limite, semente=42)),
    )
    try:
        for nome, config in configuracoes:
            identificador = gerenciador.iniciar(config)
            chamadas = -1
            while True:
                registro = gerenciador.obter(identificador)
                concluidas = len(registro['amostras'])
                if chamadas != concluidas:
                    print(f'{nome}: {concluidas}/{registro["plano_total"]} chamadas', flush=True)
                    chamadas = concluidas
                if registro['estado'] != 'executando':
                    break
                time.sleep(.1)
            if registro['estado'] != 'concluido':
                raise RuntimeError(f'{nome}: {registro["mensagem"]}')
            (pasta / f'{nome}.json').write_text(
                json.dumps(registro, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
            (pasta / f'{nome}.csv').write_text(csv_resultados(registro), encoding='utf-8')
    finally:
        gerenciador.fechar()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destino', default='resultados/complementares')
    parser.add_argument('--limite', type=int, default=90)
    args = parser.parse_args()
    coletar(args.destino, args.limite)
