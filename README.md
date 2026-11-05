# TSP · Laboratório de rotas

**João Victor Piumbini Cheroto**
Projeto e Análise de Algoritmos — Universidade de Vila Velha

Aplicação local para investigar o Problema do Caixeiro Viajante. Permite encontrar rotas, medir o crescimento da força bruta e comparar estratégias na mesma matriz de custos. O [relatório acadêmico](RELATORIO.md) apresenta a análise da atividade.

## Abrir a aplicação no Windows

Requisito: **Python 3.12 ou superior**. No PowerShell, dentro da pasta do projeto:

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-web.txt
.\.venv\Scripts\python.exe iniciar_web.py
```

Depois, abrir **http://127.0.0.1:5000** no navegador. O terminal precisa permanecer aberto. Para encerrar os cálculos e o servidor, pressionar **Ctrl+C**. Nas próximas vezes, basta executar o último comando ou abrir `iniciar_web.bat`.

Se a porta estiver ocupada:

```powershell
.\.venv\Scripts\python.exe iniciar_web.py --porta 5001
```

Nesse caso, usar **http://127.0.0.1:5001**. Não é necessário ativar a `.venv` nem alterar a política do PowerShell.

No Linux ou macOS, criar o ambiente com `python3 -m venv .venv` e usar `.venv/bin/python` nos comandos seguintes. A extensão Python do VS Code é recomendada para editar e executar o código, mas não é necessária para abrir a aplicação.

## O que investigar

| Modo | Finalidade |
|---|---|
| Encontrar a melhor rota | Resolver uma instância e examinar o circuito e a matriz. |
| Medir o crescimento fatorial | Testar vários tamanhos, repetir as medições e comparar com c × n!. |
| Comparar métodos de solução | Executar força bruta, Held–Karp e vizinho mais próximo na mesma instância. |

No benchmark, a opção **medir também sem fixar a origem** acrescenta a enumeração livre até nove cidades. A quantidade de rotas é n vezes maior; a razão dos tempos pode variar.

Há duas formas de enumerar as permutações: **biblioteca Python**, que preserva o modo da coleta original, e **trocas recursivas**, implementada no projeto. Ambas examinam todas as rotas, sem poda ou eliminação dos circuitos reversos. O custo de cada rota inclui as n arestas, com retorno à origem.

Sugestão para apresentação: começar com cinco cidades e uma repetição; examinar a rota e a matriz; depois executar um benchmark de três a oito cidades, com três repetições e comparação da origem. A comparação de métodos pode ser demonstrada com oito cidades.

## Resultados e condições de medição

- A interface mostra chamadas completas, mediana, mínimo, máximo, custo e contagens. O progresso não estima o tempo restante.
- Apenas o cálculo é cronometrado no processo filho, incluindo validações, contadores e reconstrução da rota. Preparação da matriz, criação do processo, comunicação, arquivos e desenho ficam fora do tempo registrado. Não há aquecimento nas novas execuções web.
- As matrizes são simétricas, com custos inteiros entre 1 e 100, geradas com uma semente reproduzível. Os nós no desenho usam posições ilustrativas; seus custos não representam distâncias geométricas.
- A força bruta fixa avalia (n−1)! rotas e n! arestas. Sem fixação, avalia n! rotas e n·n! arestas. Os contadores são verificados após cada chamada.
- Held–Karp é exato, com tempo O(n²·2ⁿ). O vizinho mais próximo é uma heurística O(n²), sem garantia de ótimo. Não são atribuídos contadores de força bruta a esses métodos.
- A curva c × n! é calibrada no maior tamanho concluído com origem fixa, usando a mediana das chamadas disponíveis. Uma coleta com apenas um tamanho não demonstra crescimento. As projeções são estimativas.
- O limite por execução inclui a espera pelo início do processo, enquanto o tempo medido do algoritmo não inclui esse início. O limite é um critério prático, não a capacidade máxima absoluta do computador.

O limite configurável vai de 1 a 3.600 segundos. O benchmark aceita até 16 cidades; demonstrações e comparação de métodos, até 12. São aceitas de uma a dez repetições. Solicitar um tamanho grande não garante que sua execução terminará dentro do limite.

## Histórico e exportação

A **coleta inicial**, executada em ambiente em nuvem, permanece separada: 30 chamadas completas de três a 12 cidades e interrupção por tempo em 13. Ela é exibida sem repetir os cálculos nem alterar os arquivos originais.

Novos experimentos são gravados em `experimentos/`, com configuração, ambiente e amostras. Cada chamada concluída é salva antes da seguinte. Cancelar ou atingir o limite encerra o cálculo atual e mantém os resultados anteriores. Uma execução interrompida por fechamento inesperado é marcada como interrompida na próxima abertura; o cálculo não é retomado automaticamente. Arquivos inválidos são preservados no disco, mas não entram no histórico.

**CSV** baixa as amostras individuais. **Baixar experimento** exporta um ZIP com os resultados, a configuração e as matrizes utilizadas. Durante uma execução, o download representa os dados disponíveis naquele momento. Os experimentos novos ficam no computador que executa o servidor e não são enviados automaticamente ao GitHub.

A aplicação usa o servidor HTTP da biblioteca padrão e escuta apenas em `127.0.0.1`. Não requer Flask, contas ou serviços externos. A instalação de Matplotlib atende aos gráficos da linha de comando; os gráficos da interface são desenhados localmente pelo navegador.

## Testes

No PowerShell:

```powershell
.\.venv\Scripts\python.exe -m unittest -v
```

Os testes usam pastas temporárias para não modificar as coletas. Verificam os métodos exatos e a heurística, as permutações, as contagens, o cancelamento, o limite de tempo, a persistência, a API HTTP e os arquivos exportados.

## Execução pelo terminal

O fluxo original continua disponível:

```powershell
.\.venv\Scripts\python.exe tsp.py --max-n 13 --repeticoes 3 --limite 90 --destino nova_coleta
.\.venv\Scripts\python.exe grafico.py --pasta nova_coleta
.\.venv\Scripts\python.exe relatorio.py --pasta nova_coleta --destino nova_coleta/RELATORIO.md
```

Essa opção cria uma coleta separada. O relatório gerado por `relatorio.py` utiliza o formato do benchmark de terminal; os experimentos da interface possuem seu próprio formato de exportação.

## Organização

- `tsp.py`: matriz, enumeração exaustiva e benchmark de terminal.
- `algoritmos.py`: programação dinâmica e heurística gulosa.
- `web/experimentos.py`: plano, execução, cancelamento e persistência.
- `web/servidor.py`: página, API local e downloads.
- `web/static/`: interface, gráficos e desenho dos circuitos.
- `iniciar_web.py` e `iniciar_web.bat`: inicialização local.
- `test_tsp.py` e `test_web.py`: testes automatizados.
- `resultados/`: evidências da coleta inicial e gráficos.
- `grafico.py` e `relatorio.py`: geração dos materiais do benchmark de terminal.
- `RELATORIO.md`: relatório acadêmico, disponível no GitHub.
