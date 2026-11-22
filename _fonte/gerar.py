"""Gera o site estático da Impacto Bike em site/publico/ a partir de _fonte/dados/catalogo.json.

Rodar antes: python -I catalogo.py.  Depois:  python -I gerar.py  (dentro de site/_fonte)
Fotos: converte nuvemshop/imagens/<produto>/NN.jpg em WebP 1000 px e 420 px (só as que faltam).
Sem estilo nem script inline (a política de segurança CSP bloqueia os dois).
"""
import json, re, shutil, hashlib, html, unicodedata, collections, datetime
from pathlib import Path
from multiprocessing import Pool

AQUI = Path(__file__).resolve().parent
PROJ = AQUI.parent.parent
OUT = AQUI.parent / 'publico'
NUV = PROJ / 'nuvemshop'
E = html.escape
ZAP = '5537998421369'
HOJE = datetime.date.today().strftime('%d/%m/%Y')

LOJA = dict(
    nome='Impacto Bike', razao='Impacto Cicle Ecommerce Ltda', cnpj='15.473.468/0001-70',
    endereco='Av. Governador Valadares, Centro · Arcos/MG',       # número diverge (619 / 595 sala SS1 / 680): confirmar
    fone='(37) 3351-2702', zap='(37) 99842-1369', insta='https://www.instagram.com/impactobikearcos/',
    horario='Segunda a sexta, 9h às 19h · Sábado, 8h às 12h',
    mapa='https://www.google.com/maps/search/?api=1&query=Impacto+Bike+Arcos+MG',
)

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

def brl(v):
    s = f'{v:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')
    return 'R$ ' + s

def zap(txt):
    from urllib.parse import quote
    return f'https://wa.me/{ZAP}?text={quote(txt)}'

# ---------------------------------------------------------------- fotos
def _converte(args):
    src, dst_g, dst_m = args
    from PIL import Image
    im = Image.open(src).convert('RGB')
    g = im.copy(); g.thumbnail((1000, 1000), Image.LANCZOS); g.save(dst_g, 'WEBP', quality=80, method=5)
    m = im.copy(); m.thumbnail((420, 420), Image.LANCZOS); m.save(dst_m, 'WEBP', quality=78, method=5)

def foto_url(arq, tam=''):
    # imagens/<id>/01.jpg -> img/p/<id>/01.webp  (ou 01-m.webp)
    p = Path(arq)
    return f'img/p/{p.parent.name}/{p.stem}{"-m" if tam == "m" else ""}.webp'

def converte_fotos(produtos):
    tarefas = []
    for p in produtos:
        arqs = set(p['imgs']) | {v['img'] for v in p['vars'] if v['img']}
        for a in arqs:
            g, m = OUT / foto_url(a), OUT / foto_url(a, 'm')
            if g.exists() and m.exists(): continue
            g.parent.mkdir(parents=True, exist_ok=True)
            tarefas.append((str(NUV / a), str(g), str(m)))
    if tarefas:
        with Pool() as pool: pool.map(_converte, tarefas, chunksize=16)
    print(f'fotos convertidas agora: {len(tarefas)}')

# ---------------------------------------------------------------- ícones (sprite)
ICONES = {
    'busca': '<circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/>',
    'sacola': '<path d="M5.5 8h13l1 12.5h-15L5.5 8Z"/><path d="M9 8V6.5a3 3 0 0 1 6 0V8"/>',
    'zap': '<path d="M20.5 11.6a8.6 8.6 0 0 1-12.7 7.6L3.5 20.5l1.4-4.1a8.6 8.6 0 1 1 15.6-4.8Z"/><path d="M9 9.2c.3 2.4 2.4 4.6 5 5.2l1.2-1.3-1.8-1-.8.8c-1-.5-1.9-1.4-2.4-2.4l.8-.8-1-1.8L9 9.2Z"/>',
    'menu': '<path d="M4 6.5h16M4 12h16M4 17.5h16"/>',
    'filtro': '<path d="M4 6h9M17 6h3M4 12h3M11 12h9M4 18h11M19 18h1"/><circle cx="15" cy="6" r="2"/><circle cx="9" cy="12" r="2"/><circle cx="17" cy="18" r="2"/>',
    'x': '<path d="M6 6l12 12M18 6 6 18"/>',
    'baixo': '<path d="m6 9 6 6 6-6"/>',
    'dir': '<path d="m9 6 6 6-6 6"/>',
    'cadeado': '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7.5a4 4 0 0 1 8 0V11"/>',
    'caminhao': '<path d="M3 6.5h11v9.5H3zM14 10h4l3 3.2V16h-7"/><circle cx="7" cy="18" r="2"/><circle cx="17.5" cy="18" r="2"/>',
    'loja': '<path d="M4 10v10h16V10M3 10l2-6h14l2 6M3 10h18M9 20v-6h6v6"/>',
    'cartao': '<rect x="3" y="5.5" width="18" height="13" rx="2"/><path d="M3 10h18M7 15h3"/>',
    'pix': '<path d="M12 2.8 21.2 12 12 21.2 2.8 12Z"/><path d="m8.5 12 3.5-3.5 3.5 3.5-3.5 3.5Z"/>',
    'escudo': '<path d="M12 3 4.5 6v6c0 4.6 3.2 7.7 7.5 9 4.3-1.3 7.5-4.4 7.5-9V6L12 3Z"/><path d="m9 12 2.2 2.2L15.5 10"/>',
    'check': '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
    'chave': '<path d="M14.7 6.3a4 4 0 0 0-5.4 5.4L3 18l3 3 6.3-6.3a4 4 0 0 0 5.4-5.4l-2.5 2.5-2.4-.6-.6-2.4 2.5-2.5Z"/>',
    'robo': '<rect x="4.5" y="8" width="15" height="11" rx="3"/><path d="M12 4.5V8M9 13h.01M15 13h.01M2.5 12.5v3M21.5 12.5v3"/>',
    'pessoa': '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    'banco': '<ellipse cx="12" cy="5.5" rx="8" ry="2.8"/><path d="M4 5.5v13c0 1.6 3.6 2.8 8 2.8s8-1.2 8-2.8v-13M4 12c0 1.6 3.6 2.8 8 2.8s8-1.2 8-2.8"/>',
    'estrela': '<path d="m12 3 2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9L12 3Z"/>',
    'relogio': '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
    'pino': '<path d="M12 21s-7-6.2-7-11a7 7 0 0 1 14 0c0 4.8-7 11-7 11Z"/><circle cx="12" cy="10" r="2.5"/>',
    'bike': '<circle cx="6" cy="16" r="4"/><circle cx="18" cy="16" r="4"/><path d="m6 16 4-8h5l3 8M10 8 8.5 5H6.5M15 8l-3 8"/>',
    'troca': '<path d="M4 9h13l-3-3M20 15H7l3 3"/>',
    'olho': '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12Z"/><circle cx="12" cy="12" r="3"/>',
}
SPRITE = '<svg xmlns="http://www.w3.org/2000/svg" class="sprite" aria-hidden="true" focusable="false">' + ''.join(
    f'<symbol id="i-{k}" viewBox="0 0 24 24">{v}</symbol>' for k, v in ICONES.items()) + '</svg>'
def ico(n, cls='ico'): return f'<svg class="{cls}" aria-hidden="true"><use href="#i-{n}"/></svg>'

# ---------------------------------------------------------------- layout
CSS = JS = ''
def assets():
    global CSS, JS
    (OUT / 'assets' / 'fontes').mkdir(parents=True, exist_ok=True)
    for f in (AQUI / 'assets' / 'fontes').glob('*.woff2'): shutil.copy(f, OUT / 'assets' / 'fontes' / f.name)
    for f in ('logo.webp', 'favicon.png', 'apple-touch-icon.png'): shutil.copy(AQUI / 'assets' / f, OUT / 'assets' / f)
    for velho in (OUT / 'assets').glob('site.*.css'): velho.unlink()
    for velho in (OUT / 'assets').glob('app.*.js'): velho.unlink()
    # nome fixo (cache curto no _headers): mexer no CSS/JS não obriga a regravar as 1.700 páginas
    CSS, JS = 'assets/site.css', 'assets/app.js'
    shutil.copy(AQUI / 'assets' / 'site.css', OUT / CSS); shutil.copy(AQUI / 'assets' / 'app.js', OUT / JS)
    # abertura da home (cena do primeiro protótipo): GSAP/ScrollTrigger/Lenis locais, camadas da bike, CSS e JS próprios
    for pasta in ('vendor', 'cena'):
        (OUT / 'assets' / pasta).mkdir(parents=True, exist_ok=True)
        for f in (AQUI / 'assets' / pasta).iterdir(): shutil.copy(f, OUT / 'assets' / pasta / f.name)
    for f in ('cena.css', 'cena.js'): shutil.copy(AQUI / 'assets' / f, OUT / 'assets' / f)
    for velho in (OUT / 'assets').glob('hero-*.webp'): velho.unlink()

CATS = []
def menu_arvore(cats, nivel=0):
    out = '<ul class="arvore">' if nivel == 0 else '<ul>'
    for c in cats:
        tem = bool(c['filhos'])
        out += (f'<li><div class="arvore-linha"><a href="/c/{c["slug"]}/">{E(c["nome"])}<span class="qtd">{c["total"]}</span></a>'
                + (f'<button type="button" class="abre" aria-expanded="false" aria-label="Abrir {E(c["nome"])}">{ico("baixo")}</button>' if tem else '')
                + '</div>' + (menu_arvore(c['filhos'], nivel + 1) if tem else '') + '</li>')
    return out + '</ul>'

NAV_CURTO = {'Capacetes e Óculos': 'Capacetes', 'Manutenção e Limpeza': 'Manutenção', 'Nutrição Esportiva': 'Nutrição'}

def pagina(caminho, titulo, corpo, desc='', atual='', extra_head=''):
    nav = ''.join(f'<a href="/c/{c["slug"]}/"{" aria-current=page" if atual == c["slug"] else ""}>{E(NAV_CURTO.get(c["nome"], c["nome"]))}</a>' for c in CATS)
    doc = f'''<!doctype html>
<html lang="pt-BR" data-raiz="/">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titulo)}</title>
<meta name="description" content="{E(desc or 'Impacto Bike, loja de bicicletas em Arcos/MG: bikes, peças Shimano, acessórios e oficina. Envio para todo o Brasil.')}">
<meta name="robots" content="noindex,nofollow">
<meta name="theme-color" content="#0B0D10">
<meta name="referrer" content="strict-origin-when-cross-origin">
<link rel="icon" href="/assets/favicon.png" type="image/png">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="preload" href="/assets/fontes/barlow-condensed-latin-800-italic.woff2" as="font" type="font/woff2" crossorigin>
<link rel="preload" href="/assets/fontes/inter-latin-400-normal.woff2" as="font" type="font/woff2" crossorigin>
<link rel="stylesheet" href="/{CSS}">
{extra_head}
<script src="/{JS}" defer></script>
</head>
<body>
{SPRITE}
<a class="pular" href="#conteudo">Pular para o conteúdo</a>
<header class="topo">
  <div class="envolve topo-linha">
    <a class="marca" href="/" aria-label="Impacto Bike, página inicial"><img src="/assets/logo.webp" alt="" width="44" height="44"><span class="marca-texto"><b>Impacto</b><i>Bike</i></span></a>
    <form class="busca" action="/busca/" method="get" role="search">
      <label class="oculto" for="q-topo">Buscar produtos</label>
      <input id="q-topo" name="q" type="search" placeholder="Buscar peça, bike, marca ou código" maxlength="80" autocomplete="off">
      <button type="submit" aria-label="Buscar">{ico('busca')}</button>
    </form>
    <div class="topo-acoes">
      <a class="topo-btn so-desk" href="{zap('Olá! Vim pelo site da Impacto Bike.')}" rel="noopener" target="_blank" aria-label="Falar no WhatsApp">{ico('zap')}</a>
      <a class="topo-btn" href="/sacola/" aria-label="Sacola">{ico('sacola')}<span class="contador" data-contador hidden>0</span></a>
    </div>
  </div>
  <nav class="envolve nav" aria-label="Categorias">
    <button type="button" class="btn-cats" data-abre="gaveta-cats">{ico('menu')}Categorias</button>
    {nav}
    <span class="sep" aria-hidden="true"></span>
    <a href="/oficina/"{" aria-current=page" if atual == "oficina" else ""}>Oficina</a>
    <a href="/quem-somos/"{" aria-current=page" if atual == "quem-somos" else ""}>Quem somos</a>
  </nav>
</header>
<div class="gaveta-fundo"></div>
<aside class="gaveta esq" id="gaveta-cats" aria-label="Todas as categorias" inert>
  <div class="gaveta-topo"><h2>Categorias</h2><button type="button" class="fechar" data-fecha aria-label="Fechar">{ico('x')}</button></div>
  <div class="gaveta-corpo">{menu_arvore(CATS)}</div>
</aside>
<main id="conteudo">
{corpo}
</main>
{rodape()}
<div class="aviso-add" role="status" aria-live="polite">{ico('check')}<span>Adicionado à sacola</span><a href="/sacola/">Ver sacola</a></div>
</body>
</html>'''
    destino = OUT / caminho
    GERADAS.add(destino.resolve())
    # o antivírus do Windows confere cada arquivo novo (~0,15 s): só grava o que mudou
    if destino.exists() and destino.read_text(encoding='utf-8') == doc: return
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(doc, encoding='utf-8')

GERADAS = set()
def limpa_sobras():
    n = 0
    for pasta in ('c', 'p', 'marca'):
        for f in (OUT / pasta).rglob('*.html'):
            if f.resolve() not in GERADAS: f.unlink(); n += 1
        for d in sorted((OUT / pasta).rglob('*'), key=lambda x: -len(x.parts)):
            if d.is_dir() and not any(d.iterdir()): d.rmdir()
    print(f'páginas antigas removidas: {n}')

def rodape():
    cats = ''.join(f'<li><a href="/c/{c["slug"]}/">{E(c["nome"])}</a></li>' for c in CATS)
    return f'''<footer class="rodape">
  <div class="envolve rodape-grade">
    <div>
      <a class="marca" href="/"><img src="/assets/logo.webp" alt="" width="44" height="44" loading="lazy"><span class="marca-texto"><b>Impacto</b><i>Bike</i></span></a>
      <p>Loja Shimano Concept e Shimano Service Center em Arcos/MG. Bikes, peças, acessórios e oficina.</p>
      <div class="pagamentos"><span>{ico('pix')}Pix</span><span>{ico('cartao')}Cartão de crédito</span><span>{ico('cadeado')}Compra segura</span></div>
    </div>
    <div><h3>Loja</h3><ul>{cats}</ul></div>
    <div><h3>Ajuda</h3><ul>
      <li><a href="/compra-segura/">Compra segura</a></li>
      <li><a href="/privacidade/">Privacidade e seus dados (LGPD)</a></li>
      <li><a href="/trocas-e-devolucoes/">Trocas e devoluções</a></li>
      <li><a href="/oficina/">Oficina e bike fit</a></li>
      <li><a href="/quem-somos/">Quem somos</a></li>
    </ul></div>
    <div><h3>Fale com a gente</h3><ul>
      <li><a href="{zap('Olá! Vim pelo site da Impacto Bike.')}" target="_blank" rel="noopener">WhatsApp {LOJA['zap']}</a></li>
      <li>Telefone {LOJA['fone']}</li>
      <li><a href="{LOJA['mapa']}" target="_blank" rel="noopener">{LOJA['endereco']}</a></li>
      <li>{LOJA['horario']}</li>
      <li><a href="{LOJA['insta']}" target="_blank" rel="noopener">Instagram @impactobikearcos</a></li>
    </ul></div>
  </div>
  <div class="rodape-base"><div class="envolve">{LOJA['razao']} · CNPJ {LOJA['cnpj']} · {LOJA['endereco']}.
  Preços válidos para compra no site. Fotos ilustrativas do produto.</div></div>
</footer>
<a class="zap-flutua" href="{zap('Olá! Vim pelo site da Impacto Bike.')}" target="_blank" rel="noopener" aria-label="Falar no WhatsApp">{ico('zap')}</a>'''

# ---------------------------------------------------------------- peças de página
def card(p, ordem=0):
    img = '/' + foto_url(p['imgs'][0], 'm') if p['imgs'] else ''
    vars_ = len(p['vars']) > 1
    return (f'<a class="card" href="/p/{p["id"]}/" data-marca="{E(p["marca"])}" data-preco="{p["preco_min"]}" '
            f'data-aro="{p["aro"] or ""}" data-vel="{p["vel"] or ""}" data-nome="{E(p["nome"])}" data-ordem="{ordem}">'
            f'<div class="card-foto"><img src="{img}" alt="" loading="lazy" decoding="async" width="420" height="420"></div>'
            f'<div class="card-info"><span class="card-marca">{E(p["marca"])}</span><span class="card-nome">{E(p["nome"])}</span>'
            f'<span class="card-preco">{"<small>a partir de</small>" if p["preco_min"] != p["preco_max"] else ""}{brl(p["preco_min"])}</span>'
            f'{"<span class=card-op>" + str(len(p["vars"])) + " opções</span>" if vars_ else ""}</div></a>')

def migalha(itens):
    out = ['<a href="/">Início</a>']
    for nome, url in itens:
        out.append('<span aria-hidden="true">/</span>')
        out.append(f'<a href="{url}">{E(nome)}</a>' if url else f'<span aria-current="page">{E(nome)}</span>')
    return '<nav class="migalha" aria-label="Você está em">' + ''.join(out) + '</nav>'

def selos():
    return f'''<section class="selos" aria-label="Por que comprar aqui">
  <div class="selo">{ico('cadeado')}<div><b>Compra segura</b><span>O cartão vai direto para o processador de pagamento. A loja não vê o número.</span></div></div>
  <div class="selo">{ico('pix')}<div><b>Pix ou cartão</b><span>Pague como preferir, com confirmação na hora.</span></div></div>
  <div class="selo">{ico('caminhao')}<div><b>Envio para todo o Brasil</b><span>Frete calculado pelo CEP no fechamento.</span></div></div>
  <div class="selo">{ico('loja')}<div><b>Retire em Arcos</b><span>Comprou no site, busca na loja sem pagar frete.</span></div></div>
</section>'''

FAIXAS = [(0, 50), (50, 100), (100, 300), (300, 1000), (1000, 5000), (5000, None)]
def rot_faixa(a, b):
    return f'Até {brl(b)}' if a == 0 else (f'Acima de {brl(a)}' if b is None else f'{brl(a)} a {brl(b)}')

def painel_filtros(ps):
    blocos = []
    marcas = collections.Counter(p['marca'] for p in ps if p['marca'])
    if len(marcas) >= 2:
        ops = ''
        for i, (m, n) in enumerate(marcas.most_common()):
            ops += (f'<label class="opcao"{" data-extra hidden" if i >= 8 else ""}><input type="checkbox" name="marca" value="{E(m)}" data-rotulo="{E(m)}">'
                    f'{E(m)}<span class="qtd">{n}</span></label>')
        if len(marcas) > 8: ops += f'<button type="button" class="ver-mais-op">Ver todas as {len(marcas)} marcas</button>'
        blocos.append(('Marca', ops, ''))
    faixas = []
    for a, b in FAIXAS:
        n = sum(1 for p in ps if p['preco_min'] >= a and (b is None or p['preco_min'] < b))
        if n: faixas.append(f'<label class="opcao"><input type="checkbox" name="preco" value="{a}-{"" if b is None else b}" data-rotulo="{rot_faixa(a, b)}">{rot_faixa(a, b)}<span class="qtd">{n}</span></label>')
    if len(faixas) >= 2: blocos.append(('Preço', ''.join(faixas), ''))
    for chave, titulo, fmt in (('aro', 'Aro', lambda v: v if v == '700c' else f'Aro {v}'), ('vel', 'Velocidades', lambda v: v.upper())):
        vals = collections.Counter(p[chave] for p in ps if p[chave])
        if len(vals) >= 2:
            ordem = sorted(vals, key=lambda v: (len(v), v))
            ops = ''.join(f'<label class="opcao"><input type="checkbox" name="{chave}" value="{v}" data-rotulo="{fmt(v)}"><span>{fmt(v)}</span></label>' for v in ordem)
            blocos.append((titulo, ops, ' opcoes-pilula'))
    corpo = ''.join(f'<details class="filtro"{" open" if i < 2 else ""}><summary>{t}{ico("baixo")}</summary><div class="opcoes{cls}">{ops}</div></details>'
                    for i, (t, ops, cls) in enumerate(blocos))
    return corpo, bool(blocos)

def round_robin(grupos):
    # alterna subcategorias para a página de cima mostrar variedade; dentro de cada uma, do mais caro ao mais barato
    filas = [sorted(g, key=lambda p: -p['preco_min']) for g in grupos if g]
    out = []
    while any(filas):
        for f in filas:
            if f: out.append(f.pop(0))
    return out

def lista(caminho_saida, titulo, sub, ps, migs, subcats_html='', atual='', desc='', grupos=None):
    ordem = round_robin(grupos) if grupos else sorted(ps, key=lambda p: -p['preco_min'])
    filtros, tem_filtro = painel_filtros(ps)
    cards = ''.join(card(p, i) for i, p in enumerate(ordem))
    corpo = f'''<div class="envolve">
{migalha(migs)}
<div class="lista-topo"><h1>{E(titulo)}</h1>{f"<p>{sub}</p>" if sub else ""}</div>
{subcats_html}
</div>
<div class="barra"><div class="envolve barra-linha">
  {f'<button type="button" class="btn-filtro" data-abre="gaveta-filtros">{ico("filtro")}Filtros<span class="n" id="n-filtros" hidden>0</span></button>' if tem_filtro else ''}
  <span class="total" data-total>{len(ps)} produtos</span>
  <label class="ordenar"><span>Ordenar</span><select id="ordem" aria-label="Ordenar por">
    <option value="destaque">Destaques</option><option value="menor">Menor preço</option><option value="maior">Maior preço</option><option value="az">Nome (A–Z)</option>
  </select></label>
</div></div>
<div class="envolve">
<div class="chips" id="chips" aria-live="polite"></div>
<div class="grade" id="grade" data-lista>{cards}</div>
<div class="vazio" id="vazio" hidden><b>Nenhum produto com esses filtros.</b>Tire algum filtro ou fale com a gente no WhatsApp: a loja tem mais itens do que o site mostra.</div>
<div class="mais"><button type="button" class="btn btn-preto" id="mais" hidden>Mostrar mais produtos</button></div>
</div>
<aside class="gaveta dir" id="gaveta-filtros" aria-label="Filtros" inert>
  <div class="gaveta-topo"><h2>Filtros</h2><button type="button" class="fechar" data-fecha aria-label="Fechar">{ico('x')}</button></div>
  <form class="gaveta-corpo" id="form-filtros">{filtros}</form>
  <div class="gaveta-pe"><button type="button" class="btn btn-linha" id="limpar-filtros">Limpar</button><button type="button" class="btn btn-azul btn-largo" id="ver-n" data-fecha>Ver produtos</button></div>
</aside>'''
    pagina(caminho_saida, f'{titulo} | Impacto Bike', corpo, desc=desc, atual=atual)

# ---------------------------------------------------------------- páginas
def representante(ps):
    com = [p for p in ps if p['imgs']]
    return max(com, key=lambda p: p['preco_min']) if com else None

def subcats(c, produtos_de, atual_slug=None):
    if not c['filhos']: return ''
    itens = ''
    for f in c['filhos']:
        r = representante(produtos_de(f['caminho']))
        img = f'<img src="/{foto_url(r["imgs"][0], "m")}" alt="" width="40" height="40" loading="lazy">' if r else ''
        itens += f'<a class="subcat" href="/c/{f["slug"]}/"{" aria-current=page" if f["slug"] == atual_slug else ""}>{img}{E(f["nome"])}<span class="qtd">{f["total"]}</span></a>'
    return f'<nav class="subcats" aria-label="Subcategorias de {E(c["nome"])}">{itens}</nav>'

def gera_categorias(produtos):
    def de(cam): return [p for p in produtos if p['cat'][:len(cam)] == cam]
    def anda(c, pais):
        ps = de(c['caminho'])
        migs = [(x['nome'], f'/c/{x["slug"]}/') for x in pais] + [(c['nome'], None)]
        if c['filhos']:
            sub_html = subcats(c, de); grupos = [de(f['caminho']) for f in c['filhos']]
        else:
            irmao = pais[-1] if pais else None
            sub_html = subcats(irmao, de, c['slug']) if irmao else ''; grupos = None
        sub = f'{c["total"]} produtos com foto e preço de balcão.'
        lista(f'c/{c["slug"]}/index.html', c['nome'], sub, ps, migs, sub_html, atual=c['slug'].split('/')[0],
              desc=f'{c["nome"]} na Impacto Bike, Arcos/MG. {c["total"]} produtos com envio para todo o Brasil.', grupos=grupos)
        for f in c['filhos']: anda(f, pais + [c])
    for c in CATS: anda(c, [])

def gera_marcas(produtos):
    cont = collections.Counter(p['marca'] for p in produtos if p['marca'])
    for m, n in cont.items():
        if n < 8: continue
        ps = [p for p in produtos if p['marca'] == m]
        lista(f'marca/{slug(m)}/index.html', m, f'{n} produtos {E(m)} na Impacto Bike.', ps, [('Marcas', None), (m, None)],
              desc=f'Produtos {m} na Impacto Bike, Arcos/MG.')

def gera_produtos(produtos):
    por_folha = collections.defaultdict(list)
    for p in produtos: por_folha[tuple(p['cat'])].append(p)
    for p in produtos:
        imgs = p['imgs'] or []
        vars_js = [dict(sku=v['sku'], attrs=v['attrs'], preco=v['preco'], img=('/' + foto_url(v['img'])) if v['img'] else None) for v in p['vars']]
        nomes = list(p['vars'][0]['attrs'].keys())
        sel = ''
        for n in nomes:
            vals = []
            for v in p['vars']:
                if v['attrs'].get(n) not in vals: vals.append(v['attrs'].get(n))
            if all(re.fullmatch(r'\d+(\.\d+)?', x or '') for x in vals): vals.sort(key=float)
            btns = ''.join(f'<button type="button" data-nome="{E(n)}" data-valor="{E(x)}" aria-pressed="false">{E(x)}</button>' for x in vals)
            sel += f'<div class="variacao"><b>{E(n)}</b><div class="variacao-ops" role="group" aria-label="{E(n)}">{btns}</div></div>'
        principal = '/' + foto_url(imgs[0]) if imgs else ''
        minis = ''
        if len(imgs) > 1:
            minis = '<div class="miniaturas">' + ''.join(
                f'<button type="button" data-foto="/{foto_url(a)}" aria-current="{"true" if i == 0 else "false"}" aria-label="Foto {i + 1}"><img src="/{foto_url(a, "m")}" alt="" width="64" height="64" loading="lazy"></button>'
                for i, a in enumerate(imgs)) + '</div>'
        rel = sorted((x for x in por_folha[tuple(p['cat'])] if x['id'] != p['id']), key=lambda x: abs(x['preco_min'] - p['preco_min']))[:8]
        cat_migs = []
        for i in range(len(p['cat'])):
            cam = p['cat'][:i + 1]
            cat_migs.append((cam[-1], '/c/' + '/'.join(slug(x) for x in cam) + '/'))
        v0 = p['vars'][0]
        ld = {'@context': 'https://schema.org', '@type': 'Product', 'name': p['nome'], 'sku': v0['sku'],
              'image': [principal] if principal else [], 'brand': {'@type': 'Brand', 'name': p['marca']} if p['marca'] else None,
              'offers': {'@type': 'AggregateOffer' if len(p['vars']) > 1 else 'Offer', 'priceCurrency': 'BRL',
                         **({'lowPrice': p['preco_min'], 'highPrice': p['preco_max']} if len(p['vars']) > 1 else {'price': p['preco_min']}),
                         'availability': 'https://schema.org/InStock'}}
        ld = {k: v for k, v in ld.items() if v is not None}
        dados = json.dumps(dict(nome=p['nome'], vars=vars_js), ensure_ascii=False).replace('</', '<\\/')
        corpo = f'''<div class="envolve">
{migalha(cat_migs + [(p['nome'], None)])}
<article class="produto">
  <div class="galeria">
    <div class="galeria-principal"><img src="{principal}" alt="{E(p['nome'])}" width="1000" height="1000" fetchpriority="high"></div>
    {minis}
  </div>
  <div class="ficha">
    <span class="card-marca">{E(p['marca'])}</span>
    <h1>{E(p['nome'])}</h1>
    <span class="sku">Cód. <span id="sku">{E(v0['sku'])}</span></span>
    <div class="preco-grande" id="preco">{brl(v0['preco'])}</div>
    <div class="preco-nota">Pix ou cartão de crédito. Frete calculado pelo CEP no fechamento.</div>
    {sel}
    <div class="comprar">
      <div class="qtd-box"><button type="button" data-qtd="-1" aria-label="Diminuir">−</button><input id="qtd" type="number" min="1" max="99" value="1" aria-label="Quantidade"><button type="button" data-qtd="1" aria-label="Aumentar">+</button></div>
      <button type="button" class="btn btn-azul" id="btn-add">Adicionar à sacola</button>
      <a class="btn btn-zap" id="btn-zap" target="_blank" rel="noopener" href="{zap(f"Olá! Vi no site e quero saber sobre: {p['nome']} · cód. {v0['sku']}")}">{ico('zap')}Tirar dúvida de compatibilidade no WhatsApp</a>
    </div>
    <ul class="garantias">
      <li>{ico('cadeado')}<span><b>Compra segura.</b> O número do cartão vai direto para o processador de pagamento. <a href="/compra-segura/">Entenda</a></span></li>
      <li>{ico('caminhao')}<span><b>Envio para todo o Brasil</b> ou retirada grátis na loja em Arcos/MG.</span></li>
      <li>{ico('troca')}<span><b>7 dias para desistir</b> da compra feita no site. <a href="/trocas-e-devolucoes/">Trocas e devoluções</a></span></li>
    </ul>
  </div>
</article>
<section class="descricao"><h2>Descrição</h2>{p['desc']}</section>
{f'<section class="secao"><div class="secao-titulo"><h2>Na mesma <span>categoria</span></h2></div><div class="faixa">{"".join(card(x) for x in rel)}</div></section>' if rel else ''}
</div>'''
        head = (f'<script type="application/ld+json">{json.dumps(ld, ensure_ascii=False)}</script>\n'
                f'<script type="application/json" id="dados-produto">{dados}</script>')
        pagina(f'p/{p["id"]}/index.html', p['seo_titulo'] or f'{p["nome"]} | Impacto Bike', corpo, desc=p['seo_desc'],
               atual=slug(p['cat'][0]), extra_head=head)

def gera_indice(produtos):
    d = {'p': [dict(i=p['id'], n=p['nome'], m=p['marca'], c=' '.join(p['cat']), p=p['preco_min'],
                    q=1 if p['preco_min'] != p['preco_max'] else 0, f=foto_url(p['imgs'][0], 'm') if p['imgs'] else '',
                    v=[[v['sku'], ' / '.join(v['attrs'].values()), v['preco'], foto_url(v['img'], 'm') if v['img'] else None] for v in p['vars']])
               for p in produtos]}
    (OUT / 'dados').mkdir(exist_ok=True)
    (OUT / 'dados' / 'indice.json').write_text(json.dumps(d, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')

def coroa_svg(n):
    # coroa da bike desenhada (mesma do protótipo), gerada aqui para não precisar de script inline
    import math
    R, r, passo, d = 96, 84, 2 * math.pi / n, []
    for i in range(n):
        a = i * passo
        for k, (rr, aa) in enumerate(((r, a), (R, a + passo * .22), (R, a + passo * .56), (r, a + passo * .78))):
            d.append(('M' if i == 0 and k == 0 else 'L') + f'{100 + rr * math.cos(aa):.1f} {100 + rr * math.sin(aa):.1f}')
    furos = ''
    for i in range(5):
        b = i / 5 * 2 * math.pi; b1, b2 = b + .5, b + .78
        p = lambda raio, ang: f'{100 + raio * math.cos(ang):.1f} {100 + raio * math.sin(ang):.1f}'
        furos += f'<path d="M{p(70, b)}A70 70 0 0 1 {p(70, b1)}L{p(28, b2)}L{p(28, b + .3)}Z"/>'
    return (f'<svg viewBox="0 0 200 200" fill="currentColor" aria-hidden="true"><mask id="cm{n}"><rect width="200" height="200" fill="#fff"/>'
            f'<g fill="#000">{furos}</g><circle cx="100" cy="100" r="9" fill="#000"/></mask><path mask="url(#cm{n})" d="{"".join(d)}Z"/></svg>')

def cena_html(produtos):
    def tot(slug_):
        def busca(cs):
            for c in cs:
                if c['slug'] == slug_: return c['total']
                t = busca(c['filhos'])
                if t: return t
        return busca(CATS) or 0
    def rot(cls, titulo, slug_, sub=None):
        return (f'<a class="rot {cls}" href="/c/{slug_}/"><b>{titulo}</b><span>{sub or str(tot(slug_)) + " produtos"} →</span></a>')
    total = len(produtos)
    return f'''<div id="abertura" aria-hidden="true"><div class="ab-coroa">{coroa_svg(34)}</div><div class="ab-num"><span id="ab-pct">0</span>%</div></div>
<section id="inicio" class="cena" aria-label="Impacto Bike">
  <div class="cena-fixa">
    <canvas id="luz" aria-hidden="true"></canvas>
    <div class="horizonte" aria-hidden="true"></div>
    <div class="coroa-fundo" aria-hidden="true">{coroa_svg(46)}</div>
    <div class="palavra" aria-hidden="true">Impacto</div>
    <div class="b b0" id="b0"><h1>Na Impacto Bike você vai mais longe <span class="roda-texto" data-roda="na trilha|na estrada|na cidade|na subida"></span></h1></div>
    <div class="palco-area">
      <div class="palco" id="palco">
        <div class="sombra" aria-hidden="true"></div>
        <div class="parte roda" id="p-rt"><img src="/assets/cena/roda-tras.webp" alt="" class="g" width="840" height="840"><img src="/assets/cena/roda-tras-giro.webp" alt="" class="g giro" width="840" height="840">
          {rot('rot-rt', 'Rodas e pneus', 'pecas/rodas-e-pneus')}</div>
        <div class="parte roda" id="p-rf"><img src="/assets/cena/roda-frente.webp" alt="" class="g" width="840" height="840"><img src="/assets/cena/roda-frente-giro.webp" alt="" class="g giro" width="840" height="840">
          {rot('rot-rf', 'Freios e discos', 'pecas/freios')}</div>
        <div class="parte" id="p-qd"><img src="/assets/cena/quadro.webp" alt="Bicicleta de carbono vinho com transmissão Shimano" width="1054" height="870">
          {rot('rot-qd1', 'Quadros e suspensões', 'pecas/quadros-e-suspensoes')}
          {rot('rot-qd2', 'Transmissão Shimano', 'pecas/transmissao')}</div>
        <div class="parte" id="p-fr"><img src="/assets/cena/frente.webp" alt="" width="377" height="760">
          {rot('rot-fr1', 'Suspensões e garfos', 'pecas/quadros-e-suspensoes/suspensoes-e-garfos')}
          {rot('rot-fr2', 'Guidão, mesa e manete', 'pecas/componentes')}</div>
        <div class="parte" id="p-se"><img src="/assets/cena/selim.webp" alt="">
          {rot('rot-se', 'Selins', 'pecas/componentes/selins')}</div>
      </div>
    </div>
    <div class="b b0b" id="b0b">
      <p>Bikes, peças originais Shimano e oficina Shimano Service Center em Arcos/MG. Agora com envio para todo o Brasil.</p>
      <div class="acoes"><a href="/c/bicicletas/" class="btn btn-azul">Ver bikes</a><a href="/c/pecas/" class="btn btn-linha btn-linha-claro">Comprar peças</a></div>
      <div class="desca"><i></i>Role e veja a bike</div>
    </div>
    <div class="b b1" id="b1">
      <span class="rotulo">Loja Shimano Concept</span>
      <h2>{total:,} produtos <em>com foto e preço.</em></h2>
      <p>Do parafuso à bike completa, direto do estoque da loja.</p>
    </div>
    <div class="b b2" id="b2">
      <span class="rotulo">Oficina Shimano Service Center</span>
      <h2>A gente conhece<br>peça por peça.</h2>
    </div>
    <div class="b b3" id="b3">
      <h2>Da loja pra sua casa.</h2>
      <p>Envio para todo o Brasil ou retirada na loja em Arcos.</p>
    </div>
    <div class="cortina" id="cortina" aria-hidden="true"><div class="cortina-txt">Pra onde você vai?</div></div>
  </div>
</section>'''.replace(f'{total:,}', f'{total:,}'.replace(',', '.'))

def gera_home(produtos):
    def acha(rx):
        for p in produtos:
            if re.search(rx, p['nome']) and p['imgs']: return p
    escolha = {'Bicicletas': r'Oggi 29 Cattura Pro', 'Peças': r'Câmbio Traseiro Shimano XT RD-M8100', 'Acessórios': r'Ciclocomputador GPS Navihood L3',
               'Capacetes e Óculos': r'Capacete Road Strada Kineticore Team Shimano', 'Vestuário': r'Sapatilha Road Shimano SH-RC902',
               'Manutenção e Limpeza': r'Lubrificante Finish Line Cera', 'Ferramentas': r'Canivete Absolute Slim 12', 'Nutrição Esportiva': r'C90 FourLab Pote 1kg'}
    tiles = ''
    for c in CATS:
        p = acha(escolha.get(c['nome'], '^$')) or representante([x for x in produtos if x['cat'][0] == c['nome']])
        tiles += (f'<a class="cat-card" href="/c/{c["slug"]}/"><img src="/{foto_url(p["imgs"][0], "m")}" alt="" width="420" height="420" loading="lazy">'
                  f'<div><b>{E(c["nome"])}</b><span>{c["total"]} produtos</span></div></a>')
    bikes = sorted((p for p in produtos if p['cat'][0] == 'Bicicletas'), key=lambda p: -p['preco_min'])[:10]
    shimano = [p for p in produtos if p['marca'] == 'Shimano' and p['cat'][:2] == ['Peças', 'Transmissão']]
    vitrine_sh = []
    for rx in (r'^Câmbio Traseiro Shimano', r'^Cassete Shimano 12V', r'^Corrente Shimano CN-M', r'^Alavanca de Câmbio Shimano Deore', r'^Pedivela Shimano Deore', r'^Movimento Central SM-BB'):
        vitrine_sh += [p for p in shimano if re.search(rx, p['nome'])][:2]
    n_sh = sum(1 for p in produtos if p['marca'] == 'Shimano')
    corpo = f'''{cena_html(produtos)}
<section class="secao" id="loja"><div class="envolve">
  <div class="secao-titulo"><h2>Pra onde você <span>vai?</span></h2></div>
  <div class="cat-grade">{tiles}</div>
</div></section>
{selos()}
<section class="secao secao-cinza"><div class="envolve">
  <div class="secao-titulo"><h2>Bikes <span>na loja</span></h2><a class="ver-tudo" href="/c/bicicletas/">Ver todas {ico('dir')}</a></div>
  <div class="faixa">{''.join(card(p) for p in bikes)}</div>
</div></section>
<section class="secao"><div class="envolve">
  <div class="bloco-preto duas">
    <div>
      <span class="hero-sobre">Shimano Concept · Shimano Service Center</span>
      <h2>A peça certa, <em>original Shimano.</em></h2>
      <p>São {n_sh} itens Shimano no site, de câmbio a roldana. Ficou na dúvida se serve na sua bike? Mande o modelo no WhatsApp que a oficina confere antes de você comprar.</p>
      <div class="hero-botoes"><a class="btn btn-azul" href="/marca/shimano/">Ver tudo Shimano</a><a class="btn btn-linha" href="{zap('Olá! Quero conferir se uma peça serve na minha bike.')}" target="_blank" rel="noopener">Conferir compatibilidade</a></div>
    </div>
    <div class="faixa">{''.join(card(p) for p in vitrine_sh[:6])}</div>
  </div>
</div></section>
<section class="secao secao-cinza"><div class="envolve duas">
  <div>
    <div class="secao-titulo"><h2>Oficina e <span>bike fit</span></h2></div>
    <p>Revisão, regulagem e troca de peças na oficina Shimano Service Center, e bike fit para ajustar a bike ao seu corpo. Agende pelo WhatsApp.</p>
    <div class="hero-botoes"><a class="btn btn-preto" href="/oficina/">Conhecer a oficina</a><a class="btn btn-zap" href="{zap('Olá! Quero agendar a oficina.')}" target="_blank" rel="noopener">{ico('zap')}Agendar</a></div>
  </div>
  <div>
    <div class="numero-grande">4,7 {ico('estrela', 'ico cheio')}</div>
    <p><b>Nota no Google</b>, com 82 avaliações. Os clientes elogiam o atendimento, a oficina e a variedade.</p>
    <a class="ver-tudo" href="/quem-somos/">Quem somos {ico('dir')}</a>
  </div>
</div></section>'''
    head = ('<link rel="stylesheet" href="/assets/cena.css">\n'
            '<link rel="preload" as="image" href="/assets/cena/quadro.webp">\n'
            '<script src="/assets/vendor/gsap.min.js" defer></script>\n'
            '<script src="/assets/vendor/ScrollTrigger.min.js" defer></script>\n'
            '<script src="/assets/vendor/lenis.min.js" defer></script>\n'
            '<script src="/assets/cena.js" defer></script>')
    pagina('index.html', 'Impacto Bike | Bikes, peças Shimano e oficina em Arcos/MG', corpo, extra_head=head)

def gera_institucionais():
    zap_atend = zap('Olá! Tenho uma dúvida sobre meus dados / meu pedido.')
    # ---------- quem somos
    pagina('quem-somos/index.html', 'Quem somos | Impacto Bike', f'''<div class="envolve">
{migalha([('Quem somos', None)])}
<div class="texto">
  <h1>Quem somos</h1>
  <p class="lead">A Impacto Bike é a loja de bicicletas da Avenida Governador Valadares, no Centro de Arcos/MG. Bike, peça, acessório e oficina no mesmo lugar.</p>
  <p>Na nossa fachada está escrito <b>“Paixão por pedalar”, “Peças originais” e “Atendimento técnico”</b>. É o que a gente entrega todo dia, para quem pedala na cidade e, agora pelo site, para o Brasil inteiro.</p>
</div>
<div class="bloco-preto duas">
  <div>
    <span class="hero-sobre">Shimano Concept · Shimano Service Center</span>
    <h2>A Shimano confia <em>na nossa equipe.</em></h2>
    <p>Somos loja <b>Shimano Concept</b> e oficina <b>Shimano Service Center</b>: a marca nos credencia para vender, montar e dar assistência aos componentes dela. Em 2026, recebemos o prêmio Shimano Concept.</p>
  </div>
  <ul class="lista-check">
    <li>{ico('check')}Peças originais, com nota fiscal</li>
    <li>{ico('check')}Oficina com mecânico treinado e bike fit</li>
    <li>{ico('check')}Envio para todo o Brasil e retirada na loja</li>
    <li>{ico('check')}Atendimento de verdade no WhatsApp, antes e depois da compra</li>
  </ul>
</div>
<div class="texto">
  <h2>O que os clientes dizem</h2>
  <p><b>Nota 4,7 no Google</b>, com 82 avaliações. Os elogios que mais se repetem: atendimento, oficina e variedade. Um cliente resumiu assim: “uma das melhores lojas de bicicleta do centro-oeste mineiro”.</p>
  <h2>Venha conhecer</h2>
  <table class="tabela"><tbody>
    <tr><th>Endereço</th><td><a href="{LOJA['mapa']}" target="_blank" rel="noopener">{LOJA['endereco']}</a></td></tr>
    <tr><th>Horário</th><td>{LOJA['horario']}</td></tr>
    <tr><th>WhatsApp</th><td><a href="{zap('Olá! Vim pelo site da Impacto Bike.')}" target="_blank" rel="noopener">{LOJA['zap']}</a></td></tr>
    <tr><th>Telefone</th><td>{LOJA['fone']}</td></tr>
    <tr><th>Instagram</th><td><a href="{LOJA['insta']}" target="_blank" rel="noopener">@impactobikearcos</a></td></tr>
    <tr><th>Empresa</th><td>{LOJA['razao']} · CNPJ {LOJA['cnpj']}</td></tr>
  </tbody></table>
</div>
</div>''', desc='Conheça a Impacto Bike: loja Shimano Concept e Shimano Service Center em Arcos/MG.', atual='quem-somos')

    # ---------- oficina
    pagina('oficina/index.html', 'Oficina e bike fit | Impacto Bike', f'''<div class="envolve">
{migalha([('Oficina', None)])}
<div class="texto">
  <h1>Oficina Shimano Service Center</h1>
  <p class="lead">Sua bike nas mãos de quem a Shimano credenciou. Revisão, regulagem, troca de peças e bike fit, em Arcos/MG.</p>
</div>
<div class="camadas">
  <div class="camada">{ico('chave')}<b>Revisão e manutenção</b><p>Bike conferida de ponta a ponta, com peça original quando precisa trocar.</p></div>
  <div class="camada">{ico('bike')}<b>Regulagem de câmbio e freio</b><p>Troca de marcha certinha e freio no ponto, do básico ao 12 velocidades.</p></div>
  <div class="camada">{ico('pessoa')}<b>Bike fit</b><p>Ajuste da bike ao seu corpo: mais conforto, mais rendimento, menos dor.</p></div>
  <div class="camada">{ico('escudo')}<b>Compatibilidade antes da compra</b><p>Comprou peça no site e quer instalar aqui? Mande o modelo da bike que a gente confere antes.</p></div>
</div>
<div class="bloco-preto duas">
  <div><h2>Agende <em>pelo WhatsApp.</em></h2><p>Fale o modelo da bike e o que ela está fazendo. A equipe responde com o horário e o orçamento.</p></div>
  <div><a class="btn btn-azul" href="{zap('Olá! Quero agendar a oficina. Minha bike é: ')}" target="_blank" rel="noopener">{ico('zap')}Agendar no WhatsApp</a><p>{LOJA['horario']}<br>{LOJA['endereco']}</p></div>
</div>
</div>''', desc='Oficina Shimano Service Center e bike fit da Impacto Bike em Arcos/MG.', atual='oficina')

    # ---------- compra segura
    pagina('compra-segura/index.html', 'Compra segura | Impacto Bike', f'''<div class="envolve">
{migalha([('Compra segura', None)])}
<div class="texto">
  <h1>Compra segura</h1>
  <p class="lead">Você digita o cartão aqui, mas quem recebe o número é o processador de pagamento. A Impacto Bike nunca vê, nem guarda, o número do seu cartão.</p>
  <h2>Como o pagamento funciona</h2>
  <div class="caixa-azul"><p><b>Cartão:</b> o campo do cartão é do processador de pagamento, uma empresa certificada no padrão internacional de segurança de cartões (PCI DSS). Ele fala direto com o banco. A loja recebe só a resposta, aprovado ou recusado, e os 4 últimos números para você reconhecer a compra.</p></div>
  <div class="caixa-azul"><p><b>Pix:</b> o código é gerado pelo processador e o pagamento cai em nome de <b>{LOJA['razao']}</b>. Confira esse nome no app do banco antes de confirmar.</p></div>
  <h2>As camadas de proteção do site</h2>
</div>
<div class="camadas">
  <div class="camada">{ico('cadeado')}<b>Conexão criptografada</b><p>Todo o site roda em HTTPS. O que você digita viaja embaralhado do seu aparelho até o servidor.</p></div>
  <div class="camada">{ico('robo')}<b>Proteção contra robôs</b><p>Verificação invisível no cadastro, no login e no fechamento, limite de tentativas e bloqueio de quem testa cartão em série.</p></div>
  <div class="camada">{ico('escudo')}<b>Preço conferido no servidor</b><p>Valor, frete e desconto são recalculados do nosso lado. Ninguém muda o preço mexendo na página.</p></div>
  <div class="camada">{ico('banco')}<b>Seus dados guardados com cadeado</b><p>CPF e endereço ficam criptografados no banco de dados. Senha nunca é guardada como texto.</p></div>
  <div class="camada">{ico('pessoa')}<b>Painel da loja protegido</b><p>Só a equipe da loja entra, com senha e código no celular, e cada acesso fica registrado.</p></div>
  <div class="camada">{ico('olho')}<b>Vigilância e cópia de segurança</b><p>Monitoramento de ataques, alerta de erro e cópia diária criptografada dos dados.</p></div>
</div>
<div class="texto">
  <h2>Cuidado com golpes</h2>
  <ul class="lista-check">
    <li>{ico('check')}A Impacto Bike <b>nunca pede senha</b>, código que chega por SMS ou foto do cartão.</li>
    <li>{ico('check')}Nosso único WhatsApp é o <b>{LOJA['zap']}</b>. Desconfie de outro número usando nosso nome.</li>
    <li>{ico('check')}Pagamento só pelo site ou na loja. Não pagamos nem cobramos por link enviado por terceiros.</li>
  </ul>
  <p>Quer saber quais dados guardamos e por quê? Leia a <a href="/privacidade/">Política de Privacidade</a>.</p>
</div>
</div>''', desc='Como a Impacto Bike protege sua compra e seus dados.')

    # ---------- privacidade (LGPD)
    pagina('privacidade/index.html', 'Privacidade e seus dados | Impacto Bike', f'''<div class="envolve">
{migalha([('Privacidade', None)])}
<div class="texto">
  <h1>Privacidade e seus dados</h1>
  <p class="lead">Aqui explicamos, sem juridiquês, quais dados pessoais usamos, por que, com quem dividimos e como você controla tudo isso. Seguimos a Lei Geral de Proteção de Dados (LGPD, Lei 13.709/2018).</p>
  <div class="caixa-azul"><p><b>Resumo:</b> pedimos só o que a compra precisa (entregar, emitir nota e falar com você sobre o pedido). Não vendemos dados. O número do seu cartão não passa pela loja. Você pode pedir para ver, corrigir ou apagar seus dados quando quiser.</p></div>

  <h2>Quem cuida dos seus dados</h2>
  <p><b>{LOJA['razao']}</b>, CNPJ {LOJA['cnpj']}, {LOJA['endereco']}. É a empresa que decide como seus dados são usados (a “controladora”, no termo da lei).</p>

  <h2>Quais dados usamos e por quê</h2>
  <table class="tabela"><thead><tr><th>Dado</th><th>Para quê</th><th>Base na LGPD</th></tr></thead><tbody>
    <tr><td>Nome e CPF</td><td>Identificar o comprador e emitir a nota fiscal</td><td>Execução do contrato e obrigação legal</td></tr>
    <tr><td>E-mail e celular</td><td>Avisar sobre o pedido, o pagamento e a entrega</td><td>Execução do contrato</td></tr>
    <tr><td>Endereço</td><td>Calcular o frete e entregar</td><td>Execução do contrato</td></tr>
    <tr><td>Pagamento</td><td>Cobrar a compra. O número do cartão fica com o processador de pagamento; a loja recebe só o resultado e os 4 últimos números</td><td>Execução do contrato</td></tr>
    <tr><td>Registro de acesso (IP, data e hora)</td><td>Segurança do site e exigência do Marco Civil da Internet</td><td>Obrigação legal e legítimo interesse</td></tr>
    <tr><td>Ofertas por e-mail ou WhatsApp</td><td>Só se você marcar que quer receber</td><td>Consentimento (pode retirar quando quiser)</td></tr>
  </tbody></table>

  <h2>O que não fazemos</h2>
  <ul class="lista-check">
    <li>{ico('check')}Não vendemos nem alugamos seus dados.</li>
    <li>{ico('check')}Não guardamos o número do seu cartão.</li>
    <li>{ico('check')}Não usamos cookie de propaganda. Se um dia usarmos, vamos pedir sua permissão antes.</li>
  </ul>

  <h2>Com quem dividimos</h2>
  <p>Só com quem precisa para a sua compra acontecer: o <b>processador de pagamento</b> (cobrança), a <b>transportadora ou os Correios</b> (entrega), a <b>contabilidade e a Receita/SEFAZ</b> (nota fiscal) e autoridades, quando a lei exigir.</p>

  <h2>Por quanto tempo guardamos</h2>
  <table class="tabela"><tbody>
    <tr><th>Pedido e nota fiscal</th><td>5 anos, pelo prazo da lei fiscal</td></tr>
    <tr><th>Registros de acesso</th><td>6 meses, como manda o Marco Civil da Internet</td></tr>
    <tr><th>Cadastro de cliente</th><td>Até você pedir para apagar (o que a lei obriga a guardar fica guardado só pelo prazo dela)</td></tr>
  </tbody></table>

  <h2>Seus direitos</h2>
  <p>A LGPD (artigo 18) garante que você pode, a qualquer momento: confirmar se usamos seus dados; ver quais são; corrigir o que estiver errado; pedir para apagar o que não for obrigatório guardar; levar seus dados para outra empresa; saber com quem dividimos; e retirar uma permissão que deu.</p>
  <p><b>Como pedir:</b> fale com a gente pelo <a href="{zap_atend}" target="_blank" rel="noopener">WhatsApp {LOJA['zap']}</a>. Para sua segurança, vamos confirmar que é você antes de passar qualquer dado. Respondemos em até 15 dias. Se achar que não fomos corretos, você também pode reclamar na Autoridade Nacional de Proteção de Dados (ANPD).</p>

  <h2>Cookies e armazenamento no navegador</h2>
  <p>O site guarda no seu navegador só o que faz ele funcionar, como os itens da sacola. Isso fica no seu aparelho e você pode apagar limpando os dados do navegador.</p>

  <h2>Segurança</h2>
  <p>Conexão criptografada, dados sensíveis criptografados no banco, proteção contra robôs, painel com verificação em duas etapas e cópia diária. Veja tudo em <a href="/compra-segura/">Compra segura</a>.</p>

  <p><small>Atualizada em {HOJE}.</small></p>
</div>
</div>''', desc='Política de privacidade da Impacto Bike (LGPD).')

    # ---------- trocas
    pagina('trocas-e-devolucoes/index.html', 'Trocas e devoluções | Impacto Bike', f'''<div class="envolve">
{migalha([('Trocas e devoluções', None)])}
<div class="texto">
  <h1>Trocas e devoluções</h1>
  <p class="lead">Comprou e não era o que esperava? Veja como resolver.</p>
  <h2>7 dias para desistir</h2>
  <p>Na compra pelo site, você tem <b>7 dias corridos, contados do recebimento</b>, para desistir, sem precisar explicar o motivo (Código de Defesa do Consumidor, artigo 49). Devolvemos o valor pago, frete incluído. O produto deve voltar com tudo o que veio na caixa.</p>
  <h2>Produto com defeito</h2>
  <p>Você tem <b>90 dias</b> para reclamar de defeito em produto durável (peça, bike, acessório) e <b>30 dias</b> em produto não durável (como suplementos), pelo Código de Defesa do Consumidor. Além disso vale a garantia do fabricante, quando houver.</p>
  <h2>Troca de tamanho</h2>
  <p>Sapatilha, luva, capacete ou roupa não serviu? Fale com a gente antes de devolver, que a gente orienta a troca.</p>
  <h2>Como pedir</h2>
  <p>Mande o número do pedido no <a href="{zap('Olá! Quero trocar ou devolver o pedido número: ')}" target="_blank" rel="noopener">WhatsApp {LOJA['zap']}</a>. A gente responde com o passo a passo do envio.</p>
</div>
</div>''', desc='Política de trocas e devoluções da Impacto Bike.')

def gera_funcionais():
    pagina('busca/index.html', 'Busca | Impacto Bike', f'''<div class="envolve">
{migalha([('Busca', None)])}
<div class="lista-topo"><h1>Busca <span id="busca-termo"></span></h1><p id="busca-total">Procurando…</p></div>
<div class="grade" id="resultado-busca"></div>
<div class="vazio" id="vazio" hidden><b>Não achamos esse produto no site.</b>A loja tem mais itens do que o site mostra. <a class="ver-tudo" href="{zap('Olá! Procurei no site e não achei: ')}" target="_blank" rel="noopener">Pergunte no WhatsApp</a></div>
</div>''')
    pagina('sacola/index.html', 'Sacola | Impacto Bike', f'''<div class="envolve">
{migalha([('Sacola', None)])}
<div class="lista-topo"><h1>Sua sacola</h1></div>
<div class="vazio" id="sacola-vazia"><b>Sua sacola está vazia.</b><a class="btn btn-azul" href="/">Ver produtos</a></div>
<div class="sacola-grade" id="sacola-cheia" hidden>
  <div id="itens-sacola"></div>
  <aside class="resumo">
    <h2>Resumo</h2>
    <div class="linha-resumo"><span>Subtotal</span><span data-subtotal>R$ 0,00</span></div>
    <div class="linha-resumo"><span>Frete</span><span>no próximo passo</span></div>
    <div class="linha-resumo total-final"><span>Total</span><span data-subtotal>R$ 0,00</span></div>
    <a class="btn btn-azul btn-largo" href="/finalizar/">Finalizar compra</a>
    <ul class="garantias"><li>{ico('cadeado')}<span>Pagamento seguro: o cartão vai direto para o processador.</span></li></ul>
  </aside>
</div>
</div>''')
    pagina('finalizar/index.html', 'Finalizar compra | Impacto Bike', f'''<div class="envolve">
{migalha([('Sacola', '/sacola/'), ('Finalizar', None)])}
<div class="lista-topo"><h1>Finalizar compra</h1></div>
<div class="aviso-previa"><b>Prévia.</b> O pagamento entra quando o processador de pagamento for ligado. Nada do que você digitar aqui sai do seu navegador.</div>
<form class="sacola-grade" id="form-finalizar" novalidate autocomplete="on">
  <div>
    <section class="passo"><h2><i>1</i>Seus dados</h2>
      <div class="campos dois">
        <div class="campo"><label for="nome">Nome completo</label><input id="nome" name="nome" autocomplete="name" required maxlength="120"></div>
        <div class="campo"><label for="cpf">CPF</label><input id="cpf" name="cpf" inputmode="numeric" required maxlength="14"><small>Para a nota fiscal.</small></div>
        <div class="campo"><label for="email">E-mail</label><input id="email" name="email" type="email" autocomplete="email" required maxlength="120"></div>
        <div class="campo"><label for="cel">Celular (WhatsApp)</label><input id="cel" name="cel" type="tel" autocomplete="tel" inputmode="tel" required maxlength="20"></div>
      </div>
      <div class="mel" aria-hidden="true"><label for="site-url">Não preencha</label><input id="site-url" name="site" tabindex="-1" autocomplete="off"></div>
    </section>
    <section class="passo"><h2><i>2</i>Entrega</h2>
      <div class="campos dois">
        <div class="campo"><label for="cep">CEP</label><input id="cep" name="cep" autocomplete="postal-code" inputmode="numeric" required maxlength="9"><small id="frete-msg" aria-live="polite"></small></div>
        <div class="campo"><label for="numero">Número</label><input id="numero" name="numero" autocomplete="address-line2" maxlength="10"></div>
        <div class="campo"><label for="rua">Rua</label><input id="rua" name="rua" autocomplete="address-line1" maxlength="120"></div>
        <div class="campo"><label for="bairro">Bairro e complemento</label><input id="bairro" name="bairro" maxlength="120"></div>
      </div>
      <div class="opc-entrega" id="op-retirada" hidden>
        <label><input type="radio" name="entrega" value="envio" checked> Envio pela transportadora ou Correios</label>
        <label><input type="radio" name="entrega" value="retirada"> Retirar na loja em Arcos (grátis)</label>
      </div>
    </section>
    <section class="passo"><h2><i>3</i>Pagamento</h2>
      <div class="opc-entrega">
        <label><input type="radio" name="pag" value="pix" checked>{ico('pix')} Pix</label>
        <label><input type="radio" name="pag" value="cartao">{ico('cartao')} Cartão de crédito</label>
      </div>
      <div class="cartao-seguro">{ico('cadeado')}<div><b>Aqui entra o campo seguro do cartão.</b> Ele é do processador de pagamento: o número que você digitar vai direto para ele, sem passar pela loja. <a href="/compra-segura/">Como funciona</a></div></div>
    </section>
  </div>
  <aside class="resumo">
    <h2>Seu pedido</h2>
    <div id="resumo-itens"></div>
    <div class="linha-resumo total-final"><span>Subtotal</span><span data-subtotal>R$ 0,00</span></div>
    <p class="consent"><input type="checkbox" id="ofertas" name="ofertas"><label for="ofertas">Quero receber ofertas da Impacto por e-mail ou WhatsApp (opcional, dá para sair quando quiser).</label></p>
    <p class="consent">Ao finalizar, você concorda com a <a href="/privacidade/">Política de Privacidade</a> e as <a href="/trocas-e-devolucoes/">regras de troca</a>.</p>
    <button class="btn btn-azul btn-largo" type="submit">Finalizar pedido</button>
    <div class="aviso-previa" id="msg-final" tabindex="-1" hidden><b>Esta é a prévia.</b> Na versão final, aqui o pagamento é processado e o pedido chega na loja. Nenhum dado foi enviado.</div>
  </aside>
</form>
</div>''')
    pagina('404.html', 'Página não encontrada | Impacto Bike', f'''<div class="envolve"><div class="vazio"><b>Essa página não existe.</b>
<a class="btn btn-azul" href="/">Voltar ao início</a></div></div>''')

def seguranca():
    # cabeçalhos de segurança (Netlify). CSP fechada: só o próprio site; WhatsApp e Maps abrem em outra aba.
    csp = ("default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; font-src 'self'; "
           "connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'; object-src 'none'; upgrade-insecure-requests")
    (OUT / '_headers').write_text(f'''/*
  Content-Security-Policy: {csp}
  Strict-Transport-Security: max-age=63072000; includeSubDomains
  X-Content-Type-Options: nosniff
  X-Frame-Options: DENY
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()
  Cross-Origin-Opener-Policy: same-origin
  X-Robots-Tag: noindex, nofollow
/assets/fontes/*
  Cache-Control: public, max-age=31536000, immutable
/assets/site.css
  Cache-Control: public, max-age=600
/assets/app.js
  Cache-Control: public, max-age=600
/img/*
  Cache-Control: public, max-age=604800
''', encoding='utf-8')
    (OUT / 'robots.txt').write_text('User-agent: *\nDisallow: /\n', encoding='utf-8')

def main():
    global CATS
    d = json.load(open(AQUI / 'dados' / 'catalogo.json', encoding='utf-8'))
    CATS = d['categorias']; produtos = d['produtos']
    OUT.mkdir(exist_ok=True)
    assets(); converte_fotos(produtos)
    gera_home(produtos); gera_categorias(produtos); gera_marcas(produtos); gera_produtos(produtos)
    gera_indice(produtos); gera_institucionais(); gera_funcionais(); seguranca(); limpa_sobras()
    n = sum(1 for _ in OUT.rglob('*.html'))
    print(f'{n} páginas em {OUT}')

if __name__ == '__main__':
    main()
