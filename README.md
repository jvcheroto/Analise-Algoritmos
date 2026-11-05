# TSP · Laboratório de rotas

**João Victor Piumbini Cheroto**

Projeto e Análise de Algoritmos — Universidade de Vila Velha

Aplicação para estudar a força bruta no Problema do Caixeiro Viajante, medir tempos e comparar métodos. A análise da atividade está no [relatório](RELATORIO.md).

## Executar no Windows

Requisito: Python 3.12 ou superior. Abrir o PowerShell na pasta do projeto e executar:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe iniciar_web.py
```

Acessar **http://127.0.0.1:5000** no navegador. Manter o terminal aberto e usar **Ctrl+C** para encerrar. Nas próximas vezes, executar apenas o último comando ou abrir `iniciar_web.bat`.

Se a porta estiver ocupada, usar `iniciar_web.py --porta 5001` e acessar **http://127.0.0.1:5001**. Os comandos utilizam o ambiente virtual diretamente; não é preciso ativá-lo no PowerShell. O terminal integrado do VS Code também pode ser usado.

## Modos disponíveis

| Modo | Uso |
|---|---|
| Encontrar a melhor rota | Resolver uma instância e consultar o circuito e a matriz. |
| Medir o crescimento fatorial | Executar vários tamanhos e comparar os tempos com c × n!. |
| Comparar métodos de solução | Comparar força bruta, Held–Karp e vizinho mais próximo na mesma matriz. |

No benchmark, a comparação **sem fixar a origem** está disponível até nove cidades. A origem livre gera n vezes mais rotas, embora a razão entre os tempos possa variar.

A enumeração pode usar `itertools.permutations` ou o gerador por **trocas recursivas**. Os dois modos avaliam todas as permutações e mantêm os circuitos reversos. A coleta inicial usou `itertools`.

Para uma demonstração curta, usar cinco cidades e uma repetição. Para observar a curva, usar de três a oito cidades com três repetições.

## Medições

O tempo é medido dentro da função de cálculo, incluindo validações, contadores e reconstrução da rota. A geração da matriz, o início do processo, a comunicação e a exportação ficam fora desse intervalo. As execuções são sequenciais e não têm aquecimento.

Cada tamanho usa a mesma matriz em todas as repetições e métodos. Os custos são inteiros de 1 a 100, com diagonal zero e simetria. As posições dos nós no desenho são ilustrativas.

A tabela apresenta mediana, mínimo, máximo e contagens por chamada. O progresso indica chamadas concluídas. As projeções usam c × n!, calibrado pela mediana do maior tamanho concluído com origem fixa. Um único tamanho permite comparar tempos, mas não verificar uma tendência de crescimento.

O benchmark aceita até 16 cidades; os outros modos, até 12. São permitidas de uma a dez repetições e limite de 1 a 3.600 segundos por chamada. Esse limite inclui a espera pelo início do processo. Ao atingi-lo, o programa encerra a chamada atual e preserva as anteriores.

## Histórico e downloads

A coleta inicial contém 30 chamadas completas, de três a 12 cidades, e uma tentativa interrompida em 13. Ela foi realizada em ambiente em nuvem e permanece separada das novas coletas.

Os experimentos da interface ficam em `experimentos/`, no computador que executa o servidor. Cada chamada concluída é salva antes da seguinte. Cancelamentos preservam esses resultados. Após um fechamento inesperado, o histórico marca a execução como interrompida, sem retomar o cálculo.

- **CSV:** amostras individuais.
- **Baixar experimento:** ZIP com resultados, configuração e matrizes.
- **Salvar gráfico:** imagem vetorial em SVG.

Downloads feitos durante uma execução contêm os dados disponíveis naquele momento. Os novos experimentos não são enviados automaticamente ao GitHub.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

A suíte verifica algoritmos, contagens, entradas inválidas, cancelamento, limite de tempo, persistência, API e exportação. Os testes usam pastas temporárias.

## Benchmark pelo terminal

```powershell
.\.venv\Scripts\python.exe tsp.py --max-n 13 --repeticoes 3 --limite 90 --destino nova_coleta
.\.venv\Scripts\python.exe grafico.py --pasta nova_coleta
.\.venv\Scripts\python.exe relatorio.py --pasta nova_coleta --destino nova_coleta/RELATORIO.md
```

Os comandos criam uma coleta separada e geram seu gráfico e relatório. `relatorio.py` lê o formato do benchmark de terminal; as exportações da interface têm formato próprio.

## Arquivos principais

- `tsp.py`: força bruta, gerador de permutações e benchmark.
- `algoritmos.py`: Held–Karp e vizinho mais próximo.
- `web/`: execução dos experimentos, servidor local e interface.
- `iniciar_web.py` e `iniciar_web.bat`: inicialização.
- `test_tsp.py` e `test_web.py`: testes automatizados.
- `resultados/`: dados e gráficos da coleta inicial.
- `grafico.py` e `relatorio.py`: geração dos materiais de terminal.
- `RELATORIO.md`: relatório da atividade.
