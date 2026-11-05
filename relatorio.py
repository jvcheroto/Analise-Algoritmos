"""Atualiza o relatório com os resultados da pasta informada."""
import argparse
import csv
import json
import math
import os
from pathlib import Path
from catalogo_graficos import GRAFICOS
from web.experimentos import resumo


def inteiro(valor):
    return f'{int(valor):,}'.replace(',', '.')


def decimal(valor, casas=6):
    return f'{float(valor):,.{casas}f}'.replace(',', '_').replace('.', ',').replace('_', '.')


def gerar(pasta='resultados', destino='RELATORIO.md'):
    pasta = Path(pasta)
    with (pasta / 'benchmark.csv').open(encoding='utf-8') as arquivo:
        dados = list(csv.DictReader(arquivo))
    if not dados:
        raise ValueError('Não há tamanhos concluídos para gerar o relatório')
    meta = json.loads((pasta / 'ambiente.json').read_text(encoding='utf-8'))
    ultimo = dados[-1]
    maior = int(ultimo['n'])
    tempo = float(ultimo['segundos_mediana'])
    constante = tempo / math.factorial(maior)
    tabela = '\n'.join(
        f"| {d['n']} | {inteiro(d['rotas'])} | {inteiro(d['arestas'])} | "
        f"{decimal(d['segundos_mediana'], 9)} | {d['custo_otimo']} |" for d in dados)
    projecoes = '\n'.join(f'| {n} | {inteiro(math.factorial(n - 1))} | '
                           f'{inteiro(math.factorial(n))} | '
                           f'{decimal(constante * math.factorial(n), 2)} |'
                           for n in range(maior + 1, maior + 4))
    if meta['estado'] == 'limite de tempo':
        limite = (f"A tentativa com n = {meta['n_interrompido']} foi encerrada pelo limite de "
                  f"{decimal(meta['limite_por_execucao_s'], 0)} segundos na repetição "
                  f"{meta['repeticao_interrompida']}. Esse limite considera também o início do processo. "
                  'A execução foi interrompida sem determinar o ótimo. Não há mediana nem '
                  'contagem completa para essa tentativa.')
    elif meta['estado'] == 'concluído':
        limite = f'Todos os tamanhos solicitados, até n = {maior}, foram concluídos.'
    else:
        raise ValueError('O experimento ainda está em andamento')
    imagem = Path(os.path.relpath(pasta / 'comparacao.png', Path(destino).parent)).as_posix()
    figuras = []
    for i, (nome, titulo, descricao) in enumerate(GRAFICOS, 1):
        arquivo = pasta / 'graficos' / nome
        if arquivo.is_file():
            caminho = Path(os.path.relpath(arquivo, Path(destino).parent)).as_posix()
            figuras.append(f'### Gráfico {i} — {titulo}\n\n![{titulo}]({caminho})\n\n{descricao}')
    if figuras:
        figuras = '\n\n'.join(figuras)
    else:
        figuras = f'![Tempos medidos e curva fatorial.]({imagem})'
    complemento = ''
    for nome, titulo in (('origem', 'Fixação da origem'), ('metodos', 'Métodos de solução')):
        arquivo = pasta / 'complementares' / (nome + '.json')
        if arquivo.is_file():
            registro = json.loads(arquivo.read_text(encoding='utf-8'))
            if registro['estado'] != 'concluido':
                raise ValueError('Coleta complementar não concluída')
            c = registro['config']
            ambiente = registro['ambiente']
            faixa = f"{c['fim']} cidades" if c['inicio'] == c['fim'] else f"{c['inicio']} a {c['fim']} cidades"
            fonte = Path(os.path.relpath(arquivo, Path(destino).parent)).as_posix()
            complemento += (f"\n\n**{titulo}:** coleta de {faixa}, "
                            f"{c['repeticoes']} repetições, semente {c['semente']}, "
                            f"{len(registro['amostras'])} chamadas completas. "
                            f"Ambiente: Python {ambiente['python']}, `{ambiente['sistema']}`. "
                            f"Registros em [{nome}.json]({fonte}).")
            linhas = resumo(registro['amostras'])
            if nome == 'origem':
                n = max(d['n'] for d in linhas)
                fixo = next(d for d in linhas if d['n'] == n and d['fixar'])
                livre = next(d for d in linhas if d['n'] == n and not d['fixar'])
                complemento += (f" Em n = {n}, as medianas foram {decimal(fixo['mediana'])} s "
                                f"com origem fixa e {decimal(livre['mediana'])} s com origem livre. "
                                f"A razão dos tempos foi {decimal(livre['mediana']/fixo['mediana'], 2)}, "
                                f"enquanto a razão das contagens de rotas foi exatamente {n}.")
            else:
                custos = {d['algoritmo']: d['custo'] for d in linhas}
                if custos['bruta'] != custos['held_karp']:
                    raise ValueError('Os métodos exatos divergiram na coleta complementar')
                complemento += (f" Força bruta e Held–Karp encontraram custo {custos['bruta']}; "
                                f"o vizinho mais próximo encontrou {custos['guloso']}. "
                                'O menor tempo do guloso não implica garantia de ótimo.')
    if complemento:
        complemento = ('\n\nAs coletas complementares dos gráficos 5 e 6 são independentes da tabela inicial '
                       'e não entram na calibração de c.' + complemento)
    texto = f'''# Explorando a intratabilidade e a força bruta no Problema do Caixeiro Viajante

**Autor:** João Victor Piumbini Cheroto

**Disciplina:** Projeto e Análise de Algoritmos — Universidade de Vila Velha

**Data:** 05/11/2026

## 1. Introdução e objetivo

O Problema do Caixeiro Viajante (TSP) busca o circuito de menor custo que visite cada cidade uma vez e retorne à origem. Este trabalho implementa a força bruta e compara suas contagens e tempos de execução com a análise das seções 4.1 e 4.2 da Unidade 04.

## 2. Implementação e método experimental

O grafo completo é representado por uma matriz simétrica, com diagonal zero e custos inteiros de 1 a 100. A geração utiliza `random.Random(42)`, permitindo reproduzir as instâncias. Os custos não seguem necessariamente a desigualdade triangular. Para cada tamanho, a mesma matriz é usada em todas as repetições.

A cidade de índice 0, correspondente a v₁, permanece fixa. A função `resolver` percorre as permutações dos outros índices, calcula o custo de cada circuito e guarda o menor valor. A função `custo_rota` soma as n arestas, incluindo o retorno à origem. As permutações são geradas sob demanda, sem armazenar todas simultaneamente. Como o enunciado adota (n−1)! rotas, os dois sentidos de um circuito são avaliados mesmo no grafo simétrico.

Foram solicitadas instâncias de 3 a {meta['max_n_solicitado']} cidades, com número de repetições igual a {meta['repeticoes']} por tamanho e limite de {decimal(meta['limite_por_execucao_s'], 0)} segundos por execução. Os tamanhos de 3 a {maior} foram concluídos integralmente. A medição usa `time.perf_counter()` dentro do processo de cálculo, incluindo validação da matriz, geração de permutações, avaliação, contagem e escolha do ótimo. A criação da matriz, o início do processo, a comunicação entre processos, a gravação dos arquivos e a geração dos gráficos ficam fora do tempo registrado no CSV.

Ambiente registrado na coleta: Python {meta['python']}, sistema `{meta['sistema']}`. As chamadas são sequenciais, cada uma em um processo separado para permitir o encerramento por tempo. Hardware e carga do sistema influenciam as medições.

O CSV reúne os tempos individuais, a mediana, o mínimo e o máximo de cada tamanho concluído. As contagens são verificadas após cada chamada. Interrupções ficam registradas em `ambiente.json`.

## 3. Resultados experimentais

| n | Rotas = (n−1)! | Avaliações de arestas = n! | Mediana (s) | Custo ótimo |
|---|---:|---:|---:|---:|
{tabela}

As contagens coincidiram com as expressões teóricas em todas as repetições concluídas. O exemplo de n = 6 corresponde a 120 rotas e 720 arestas, conforme a seção 4.1.7 do material. Na maior instância concluída, n = {maior}, a rota ótima foi {ultimo['rota']}, com custo {ultimo['custo_otimo']}. Os custos ótimos entre tamanhos não precisam crescer, pois as matrizes são distintas.

{figuras}{complemento}

Fonte: resultados do experimento registrados em `benchmark.csv`.

A curva f(n) = c × n! usa c = {constante:.8e} s, calculado pela mediana do maior tamanho concluído dividida por seu fatorial. A coincidência nesse ponto é consequência da calibração. Os demais pontos permitem comparar a tendência, com maior influência dos custos fixos nos tamanhos pequenos. As medições são compatíveis com o crescimento fatorial; a demonstração de Θ(n!) vem da contagem de operações.

## 4. Análise e discussão

### 4.1. Redução do espaço de busca

Sem fixar a origem, seriam geradas n! permutações. Cada circuito orientado apareceria n vezes, uma por possível cidade de partida. Ao fixar v₁, restam (n−1)! rotas. A razão é n!/(n−1)! = n, ou seja, uma redução por um fator n. Para n = 10, a busca passa de 3.628.800 para 362.880 rotas, economia de 90%.

O teste `test_sem_fixacao` compara as duas estratégias em uma instância de cinco cidades: a enumeração sem fixação produz cinco vezes mais rotas e o mesmo custo ótimo. Na implementação principal, apenas os índices de 1 a n−1 são permutados. Para grafos simétricos, eliminar também os circuitos reversos permitiria uma redução adicional por dois; essa otimização não foi aplicada para manter a contagem solicitada.

### 4.2. Custo de avaliação e complexidade total

O laço de `custo_rota` executa n iterações, consultando e somando uma aresta em cada uma. A ligação da última cidade à primeira também é incluída. Assim, cada avaliação custa Θ(n), sob o modelo de operações de custo constante para os inteiros utilizados.

Com R = (n−1)! rotas, a quantidade de avaliações de arestas é A(n) = n × (n−1)! = n!. O quociente A(n)/R foi igual a n nos resultados. Portanto, o tempo da implementação é Θ(n!). A contagem n! não corresponde a todas as instruções da CPU: criação de tuplas, comparações e atualização de contadores também contribuem para o tempo.

A matriz ocupa Θ(n²) de memória. A geração e a avaliação usam espaço adicional linear em n, pois as rotas não são armazenadas simultaneamente.

### 4.3. Limiar prático da intratabilidade

A maior instância concluída foi n = {maior}, com mediana de {decimal(tempo)} segundos. {limite}

O limite de tempo é o critério de parada adotado. Ele não determina o maior tamanho que a máquina conseguiria resolver com mais tempo.

As projeções abaixo usam a mesma constante c. Esses tempos não foram medidos:

| n | Rotas previstas | Avaliações de arestas previstas | Tempo projetado (s) |
|---|---:|---:|---:|
{projecoes}

Ao acrescentar uma cidade, a contagem de avaliações cresce por um fator n+1. Esse comportamento explica por que poucos acréscimos podem levar a minutos ou horas. O Merge Sort, com Θ(n log n), apresenta crescimento muito menor. A recorrência T(n) = 2T(n−1) + c, discutida na seção 4.2.2, exemplifica Θ(2ⁿ); não descreve esta implementação do TSP, cujo crescimento é fatorial.

### 4.4. P, NP e limites das heurísticas

P e NP são classes de problemas de decisão, com P contida em NP. NP reúne problemas cujas respostas positivas admitem certificados verificáveis em tempo polinomial. Isso não significa que todo problema em NP seja intratável. A versão de decisão do TSP pergunta se existe uma rota de custo no máximo B e é NP-completa. A versão de otimização, abordada neste trabalho, é NP-difícil.

Uma rota candidata permite calcular seu custo e verificar se ele respeita B em tempo polinomial. Esse procedimento não prova que a rota seja ótima. Não se conhece um algoritmo exato polinomial para o TSP geral, e P versus NP permanece em aberto. A análise desta força bruta não demonstra que todo algoritmo exato precise de tempo fatorial. A programação dinâmica, por exemplo, reduz o tempo para O(n² × 2ⁿ), ainda exponencial.

A heurística do vizinho mais próximo pode executar em O(n²) com uma matriz, mas escolhas locais não garantem o ótimo global. O exemplo abaixo, partindo de A, demonstra essa limitação:

| Cidade | A | B | C | D |
|---|---:|---:|---:|---:|
| A | 0 | 1 | 2 | 3 |
| B | 1 | 0 | 4 | 5 |
| C | 2 | 4 | 0 | 100 |
| D | 3 | 5 | 100 | 0 |

O vizinho mais próximo escolhe A→B→C→D→A, com custo 1+4+100+3 = 108. A rota A→C→B→D→A custa 2+4+5+3 = 14. A força bruta confirma que 14 é o ótimo. O exemplo utiliza custos sem a desigualdade triangular, conforme o modelo adotado.

Heurísticas e metaheurísticas podem obter boas soluções em menos tempo, mas geralmente não certificam a otimalidade. Garantias de aproximação dependem do algoritmo e de hipóteses específicas sobre os custos.

## 5. Validação e reprodução

Os testes automatizados abrangem ótimo conhecido, fechamento do circuito, contagem fatorial, economia pela fixação da origem, empates, custos nulos, negativos e fracionários, entradas inválidas e preservação da matriz. Também comparam os resultados com uma referência independente por programação dinâmica em 20 matrizes assimétricas, de 3 a 7 cidades.

Os testes do benchmark verificam os argumentos, a gravação dos resultados e a preservação das chamadas concluídas após uma interrupção. O limite de tempo também é exercitado com um processo real. Os tempos da suíte de testes não compõem o benchmark.

Comandos de reprodução no PowerShell, executados na pasta do projeto:

```powershell
py -m venv .venv
.\\.venv\\Scripts\\python.exe -m pip install -r requirements.txt
.\\.venv\\Scripts\\python.exe -m unittest -v
.\\.venv\\Scripts\\python.exe tsp.py --max-n 13 --repeticoes 3 --limite 90
.\\.venv\\Scripts\\python.exe grafico.py
.\\.venv\\Scripts\\python.exe relatorio.py
```

Após uma nova coleta, executar `grafico.py` e `relatorio.py` para atualizar os materiais com os tempos obtidos.

### 5.1. Aplicação local

A aplicação oferece demonstração de rotas, benchmark com e sem origem fixa e comparação com Held–Karp e vizinho mais próximo. A enumeração pode usar `itertools.permutations` ou trocas recursivas.

As coletas da interface ficam em `experimentos/` e não foram agregadas aos resultados da seção 3. No desenho da rota, as posições dos nós são ilustrativas; os custos vêm da matriz. As instruções de execução e exportação estão no README.

## 6. Conclusão

As contagens observadas confirmaram (n−1)! rotas e n! avaliações de arestas. Fixar a origem reduz o trabalho redundante, mas mantém a complexidade Θ(n!). A busca foi concluída até n = {maior}; as instâncias seguintes foram discutidas por projeção. O crescimento fatorial limita a aplicação da força bruta, apesar da garantia de ótimo nas execuções completas. Heurísticas reduzem o custo da busca, mas não oferecem a mesma garantia em geral.

## Referência

UNIVERSIDADE VILA VELHA. **Unidade 04: Projeto e Análise de Algoritmos**. Material disponibilizado na disciplina, seções 4.1 e 4.2.
'''
    Path(destino).write_text(texto, encoding='utf-8')
    return texto


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pasta', default='resultados')
    parser.add_argument('--destino', default='RELATORIO.md')
    args = parser.parse_args()
    gerar(args.pasta, args.destino)
