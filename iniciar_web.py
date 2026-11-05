"""Inicia a aplicação local do laboratório de TSP."""
import argparse
import multiprocessing
from pathlib import Path
from web.servidor import criar_servidor


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--porta', type=int, default=5000)
    parser.add_argument('--dados', type=Path, default=Path(__file__).resolve().parent / 'experimentos')
    args = parser.parse_args()
    if not 1 <= args.porta <= 65535:
        parser.error('A porta deve estar entre 1 e 65535')
    try:
        servidor = criar_servidor(args.porta, args.dados)
    except OSError as erro:
        parser.exit(1, f'Não foi possível abrir a porta {args.porta}: {erro}\n')
    print(f'Aplicação disponível em http://127.0.0.1:{servidor.server_port}', flush=True)
    print('Para encerrar, pressione Ctrl+C neste terminal.', flush=True)
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print('\nEncerrando os cálculos e salvando os resultados...', flush=True)
    finally:
        servidor.gerenciador.fechar()
        servidor.server_close()


if __name__ == '__main__':
    multiprocessing.freeze_support()
    main()
