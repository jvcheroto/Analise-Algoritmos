'use strict';
const $ = id => document.getElementById(id);
const nomes = {bruta: 'Força bruta', held_karp: 'Held–Karp', guloso: 'Vizinho mais próximo'};
const estados = {executando: 'EM EXECUÇÃO', concluido: 'CONCLUÍDO', cancelado: 'CANCELADO', limite: 'LIMITE ATINGIDO', erro: 'ERRO', interrompido: 'INTERROMPIDO'};
const numero = (v, casas = 6) => Number(v).toLocaleString('pt-BR', {maximumFractionDigits: casas});
const contagem = v => v == null ? '—' : BigInt(v).toLocaleString('pt-BR');
const seguro = v => String(v).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let selecionado = null, registro = null, chaveRota = '', tokenRota = 0;

async function api(url, dados) {
  const opcoes = dados === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json', 'X-TSP-Request':'1'}, body:JSON.stringify(dados)};
  const resposta = await fetch(url, opcoes);
  const corpo = await resposta.json();
  if (!resposta.ok) throw new Error(corpo.erro || 'Não foi possível concluir a solicitação.');
  return corpo;
}
function aviso(texto = '') { $('aviso').textContent = texto; $('aviso').hidden = !texto; }
function config() {
  const c = {tipo:$('tipo').value, inicio:Number($('inicio').value), fim:Number($('fim').value),
    repeticoes:Number($('repeticoes').value), limite:Number($('limite').value), semente:Number($('semente').value),
    comparar_origem:$('comparar').checked, gerador:$('gerador').value};
  if (c.tipo !== 'benchmark') { c.inicio = c.fim; c.comparar_origem = false; }
  return c;
}
function plano() {
  const benchmarkAtual = $('tipo').value === 'benchmark';
  if (!benchmarkAtual && Number($('fim').value) > 12) $('fim').value = 12;
  const c = config(), benchmark = c.tipo === 'benchmark';
  $('inicio-label').hidden = !benchmark; $('inicio').disabled = !benchmark;
  $('origem-label').hidden = !benchmark;
  $('fim').max = benchmark ? 16 : 12;
  if (!benchmark && c.fim > 12) $('fim').value = 12;
  let chamadas = 0;
  for (let n = c.inicio; n <= c.fim && n <= 16; n++) {
    chamadas += c.repeticoes * (c.tipo === 'comparacao' ? 3 : 1 + (c.comparar_origem && n <= 9 ? 1 : 0));
  }
  $('plano').textContent = c.inicio > c.fim ? 'O início deve ser menor ou igual ao fim.' :
    `${chamadas} chamadas planejadas · ${c.inicio === c.fim ? c.fim : `${c.inicio} a ${c.fim}`} cidades · mesma matriz em cada comparação. ` +
    (c.fim >= 11 ? 'Instâncias maiores podem levar minutos ou atingir o limite configurado.' : 'O tempo aumenta rapidamente a cada nova cidade.');
}
function abrirView(nome) {
  document.querySelectorAll('.view').forEach(el => el.hidden = el.id !== 'view-' + nome);
  document.querySelectorAll('.tab').forEach(el => el.classList.toggle('active', el.dataset.view === nome));
}
async function historico() {
  const lista = await api('/api/experimentos');
  $('historico').replaceChildren();
  for (const item of lista) {
    const botao = document.createElement('button');
    botao.classList.toggle('selected', item.id === selecionado);
    botao.innerHTML = `<strong>${seguro(item.titulo)}</strong>${new Date(item.inicio).toLocaleString('pt-BR')}<br><small>${estados[item.estado] || seguro(item.estado)} · ${item.concluidas}/${item.total} chamadas</small>`;
    botao.onclick = () => selecionar(item.id);
    $('historico').append(botao);
  }
  const ativo = lista.find(item => item.estado === 'executando');
  $('iniciar').disabled = Boolean(ativo);
  if (!selecionado && lista.length) await selecionar(ativo ? ativo.id : lista[0].id);
}
async function selecionar(id) {
  selecionado = id; chaveRota = ''; aviso();
  try {
    const r = await api('/api/experimentos/' + id);
    if (selecionado !== id) return;
    registro = r; renderizar();
  } catch (erro) { aviso(erro.message); }
}
function metodo(d) { return nomes[d.algoritmo] + (d.algoritmo === 'bruta' ? (d.fixar ? ' · origem fixa' : ' · origem livre') : ''); }
function renderizar() {
  const r = registro, c = r.config, linhas = r.resumo;
  $('experimento').hidden = false;
  $('titulo').textContent = r.titulo;
  $('data').textContent = new Date(r.inicio).toLocaleString('pt-BR');
  $('estado').textContent = estados[r.estado] || r.estado;
  $('mensagem').textContent = r.mensagem;
  $('cancelar').hidden = r.estado !== 'executando';
  $('cancelar').disabled = false;
  $('progresso').max = r.plano_total || 1; $('progresso').value = r.amostras.length;
  $('progresso-texto').textContent = `${r.amostras.length} de ${r.plano_total} chamadas concluídas. Progresso por chamada concluída.`;
  $('met-chamadas').textContent = r.amostras.length;
  const maior = linhas.length ? Math.max(...linhas.map(d => d.n)) : null;
  const linhaMaior = linhas.find(d => d.n === maior && d.algoritmo === 'bruta' && d.fixar);
  $('met-n').textContent = maior || '—';
  $('met-tempo').textContent = linhaMaior ? numero(linhaMaior.mediana, 3) + ' s' : '—';
  $('baixar-csv').href = `/api/experimentos/${r.id}/csv`;
  $('baixar-zip').href = `/api/experimentos/${r.id}/zip`;
  $('tabela').innerHTML = linhas.length ? linhas.map(d => `<tr><td>${d.n}</td><td>${metodo(d)}</td><td>${d.repeticoes}/${c.repeticoes}</td><td>${numero(d.mediana, 9)}</td><td>${numero(d.minimo, 6)}–${numero(d.maximo, 6)}</td><td>${numero(d.custo, 3)}${d.exato ? ' · ótimo' : ' · heurístico'}</td><td>${contagem(d.rotas)}</td><td>${contagem(d.arestas)}</td></tr>`).join('') : '<tr><td colspan="8">Aguardando a primeira chamada completa.</td></tr>';
  $('projecoes').innerHTML = r.projecoes.length ? r.projecoes.map(d => `<div><span>${d.n} cidades · projeção</span><strong>${numero(d.segundos, 2)} s</strong><span>${numero(d.segundos / 60, 2)} minutos</span></div>`).join('') : '<p>As projeções ficam disponíveis após uma execução de força bruta com origem fixa.</p>';
  $('condicoes').innerHTML = `<div class="conditions"><strong>Configuração registrada</strong><br>${c.inicio} a ${c.fim} cidades · ${c.repeticoes} repetições · semente ${c.semente} · limite ${c.limite} s<br>Permutações: ${c.gerador === 'manual' ? 'trocas recursivas' : 'biblioteca Python'}<br>Python ${seguro(r.ambiente.python)} · ${seguro(r.ambiente.sistema)}<br>Início: ${new Date(r.inicio).toLocaleString('pt-BR')}${r.fim ? '<br>Fim: ' + new Date(r.fim).toLocaleString('pt-BR') : ''}</div>`;
  desenharGrafico();
  const chave = r.id + ':' + linhas.length;
  if (chaveRota !== chave) {
    const antiga = $('selecionar-rota').value;
    $('selecionar-rota').innerHTML = linhas.map((d, i) => `<option value="${i}">${d.n} cidades · ${metodo(d)}</option>`).join('');
    if (chaveRota && Number(antiga) < linhas.length) $('selecionar-rota').value = antiga;
    else if (linhas.length) $('selecionar-rota').value = linhas.length - 1;
    chaveRota = chave;
    desenharRota().catch(erro => aviso(erro.message));
  }
}
function desenharGrafico() {
  const linhas = registro.resumo;
  if (!linhas.length) { $('grafico').innerHTML = '<p>A curva será construída com os tempos efetivamente medidos.</p>'; $('curva-info').textContent = ''; return; }
  const fixos = linhas.filter(d => d.algoritmo === 'bruta' && d.fixar);
  const livres = linhas.filter(d => d.algoritmo === 'bruta' && !d.fixar);
  const W = 850, H = 310, L = 70, R = 25, T = 20, B = 45;
  const log = $('log').checked;
  const transformar = v => log ? Math.log10(Math.max(v, 1e-10)) : v;
  const unicos = [...new Set(linhas.map(d => d.n))];
  $('legenda').hidden = unicos.length === 1;
  let conteudo = '';
  const fatoriais = n => { let f = 1; for (let i = 2; i <= n; i++) f *= i; return f; };
  const teoricos = fixos.map(d => ({n:d.n, mediana:registro.constante * fatoriais(d.n)}));
  const valores = [...linhas, ...teoricos].map(d => transformar(d.mediana));
  let yMin = log ? Math.floor(Math.min(...valores)) : 0;
  let yMax = log ? Math.ceil(Math.max(...valores)) : Math.max(...valores) * 1.12;
  if (yMax === yMin) yMax = yMin + 1;
  const y = v => H - B - (transformar(v) - yMin) / (yMax - yMin) * (H - B - T);
  for (let i = 0; i <= 4; i++) {
    const v = yMin + (yMax - yMin) * i / 4, pos = H - B - i * (H - B - T) / 4;
    const label = log ? (10 ** v).toExponential(1) : numero(v, 4);
    conteudo += `<line x1="${L}" x2="${W-R}" y1="${pos}" y2="${pos}" stroke="#e0e7df"/><text x="${L-10}" y="${pos+4}" text-anchor="end" font-size="11" fill="#657470">${label}</text>`;
  }
  if (unicos.length === 1) {
    $('curva-info').textContent = 'Comparação de tempos para uma instância. O crescimento exige medições de vários tamanhos.';
    linhas.forEach((d, i) => {
      const x = L + (i + .5) * (W - L - R) / linhas.length;
      conteudo += `<line x1="${x}" x2="${x}" y1="${y(d.mediana)}" y2="${H-B}" stroke="${d.algoritmo === 'guloso' ? '#d47b37' : '#247aa5'}" stroke-width="22"/><text x="${x}" y="${H-B+20}" text-anchor="middle" font-size="11">${seguro(nomes[d.algoritmo])}</text><circle cx="${x}" cy="${y(d.mediana)}" r="4" fill="#176d64"><title>${numero(d.mediana,9)} s</title></circle>`;
    });
  } else {
    $('curva-info').textContent = `Tempos medidos e c × n!, com c = ${registro.constante.toExponential(4)} s. Calibração em n=${registro.calibracao_n}.`;
    const menor = Math.min(...unicos), maior = Math.max(...unicos);
    const x = n => L + (n-menor)/(maior-menor)*(W-L-R);
    for (const n of unicos) conteudo += `<text x="${x(n)}" y="${H-B+22}" text-anchor="middle" font-size="11">${n}</text>`;
    const linha = (dados, cor, tracejado) => {
      if (!dados.length) return '';
      return `<polyline points="${dados.map(d => `${x(d.n)},${y(d.mediana)}`).join(' ')}" fill="none" stroke="${cor}" stroke-width="2" ${tracejado ? 'stroke-dasharray="6 5"' : ''}/>`;
    };
    conteudo += linha(teoricos,'#939f95',true) + linha(fixos,'#247aa5') + linha(livres,'#d47b37');
    for (const d of [...fixos, ...livres]) conteudo += `<circle cx="${x(d.n)}" cy="${y(d.mediana)}" r="4.5" fill="${d.fixar ? '#247aa5' : '#d47b37'}"><title>n=${d.n}: ${numero(d.mediana,9)} s</title></circle>`;
  }
  conteudo += `<text x="${W/2}" y="${H-4}" text-anchor="middle" font-size="11" fill="#657470">${unicos.length === 1 ? 'Método de solução' : 'Número de cidades (n)'}</text><text x="8" y="13" font-size="11" fill="#657470">Tempo (s)</text>`;
  $('grafico').innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${W} ${H}" role="img" aria-label="Gráfico dos tempos medidos">${conteudo}</svg>`;
}
async function desenharRota() {
  const token = ++tokenRota, r = registro, d = r.resumo[Number($('selecionar-rota').value)];
  if (!d) { $('mapa').innerHTML = '<p>A rota será exibida após uma chamada completa.</p>'; $('matriz').replaceChildren(); $('caminho').textContent = ''; $('rota-custo').textContent = ''; return; }
  const instancia = await api(`/api/experimentos/${r.id}/instancia?n=${d.n}`);
  if (token !== tokenRota || r.id !== selecionado) return;
  const matriz = instancia.matriz, n = d.n, centroX = 300, centroY = 225, raio = 165;
  const pontos = Array.from({length:n}, (_, i) => ({x:centroX + raio * Math.cos(2*Math.PI*i/n - Math.PI/2), y:centroY + raio * Math.sin(2*Math.PI*i/n - Math.PI/2)}));
  let svg = '';
  for (let i = 0; i < n; i++) {
    const a = pontos[d.rota[i]], b = pontos[d.rota[i+1]];
    svg += `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="#72a99a" stroke-width="2.5"><title>Custo ${matriz[d.rota[i]][d.rota[i+1]]}</title></line>`;
    if (n <= 8) svg += `<text x="${(a.x+b.x)/2}" y="${(a.y+b.y)/2-7}" fill="#43685c" font-size="12" text-anchor="middle">${matriz[d.rota[i]][d.rota[i+1]]}</text>`;
  }
  pontos.forEach((p, i) => { svg += `<circle cx="${p.x}" cy="${p.y}" r="19" fill="${i === 0 ? '#176d64' : '#e8f0e7'}" stroke="#176d64"/><text x="${p.x}" y="${p.y+5}" text-anchor="middle" font-size="14" fill="${i===0 ? 'white' : '#176d64'}">${i+1}</text>`; });
  $('mapa').innerHTML = `<svg viewBox="0 0 600 450" role="img" aria-label="Circuito visitando todas as cidades">${svg}</svg>`;
  $('caminho').textContent = d.rota.map(v => 'v' + (v + 1)).join(' → ');
  const exatos = r.resumo.filter(a => a.n === n && a.exato);
  const custoOtimo = exatos.length ? exatos[0].custo : null;
  $('rota-custo').textContent = `${metodo(d)} · custo ${numero(d.custo)} · ${d.exato ? 'ótimo confirmado por método exato' : 'solução heurística, sem garantia de ótimo'}` + (!d.exato && custoOtimo > 0 ? ` · diferença para o ótimo: ${numero(100*(d.custo-custoOtimo)/custoOtimo,2)}%` : '');
  $('matriz').innerHTML = `<table><thead><tr><th>De / para</th>${matriz.map((_,i) => `<th>v${i+1}</th>`).join('')}</tr></thead><tbody>${matriz.map((linha,i) => `<tr><th>v${i+1}</th>${linha.map(v => `<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table>`;
}
$('formulario').addEventListener('input', plano);
$('formulario').addEventListener('submit', async evento => {
  evento.preventDefault(); aviso(); $('iniciar').disabled = true;
  try { const r = await api('/api/experimentos', config()); await selecionar(r.id); await historico(); $('experimento').scrollIntoView({behavior:'smooth', block:'start'}); }
  catch (erro) { aviso(erro.message); $('iniciar').disabled = false; }
});
$('cancelar').onclick = async () => {
  $('cancelar').disabled = true;
  try { await api(`/api/experimentos/${selecionado}/cancelar`, {}); }
  catch (erro) { aviso(erro.message); }
};
$('novo').onclick = () => $('configuracao').scrollIntoView({behavior:'smooth'});
$('salvar-grafico').onclick = evento => {
  evento.preventDefault();
  const svg = $('grafico').querySelector('svg');
  if (!svg) { aviso('Aguarde uma chamada completa para salvar o gráfico.'); return; }
  const imagem = svg.cloneNode(true);
  imagem.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
  const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(imagem)], {type:'image/svg+xml'}));
  const link = document.createElement('a'); link.href = url; link.download = 'tsp-grafico.svg';
  link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
};
$('log').onchange = () => { if (registro) desenharGrafico(); };
$('selecionar-rota').onchange = () => desenharRota().catch(erro => aviso(erro.message));
document.querySelectorAll('.tab').forEach(botao => botao.onclick = () => abrirView(botao.dataset.view));
async function atualizar() {
  try {
    await historico();
    if (selecionado) {
      const id = selecionado, r = await api('/api/experimentos/' + id);
      if (id === selecionado) { registro = r; renderizar(); }
    }
  } catch (erro) { aviso('Conexão interrompida. Confira se o servidor continua aberto no terminal. ' + erro.message); }
  finally { setTimeout(atualizar, 1200); }
}
async function carregarGaleria() {
  try {
    const graficos = await api('/api/graficos');
    $('galeria').innerHTML = graficos.map((g, i) => `<article><h3>${i+1}. ${seguro(g.titulo)}</h3><p>${seguro(g.descricao)}</p>${g.disponivel ? `<a href="${g.url}" download="${seguro(g.arquivo)}"><img src="${g.url}" alt="${seguro(g.titulo)}" loading="lazy"><span>Baixar PNG ↓</span></a>` : '<p>Gráfico indisponível. Gere os arquivos com grafico.py após a coleta correspondente.</p>'}</article>`).join('');
  } catch (erro) { $('galeria').textContent = erro.message; }
}
plano(); atualizar(); carregarGaleria();
