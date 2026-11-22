"""Monta o catálogo do site próprio da Impacto Bike.

Entrada: nuvemshop/produtos-com-foto.csv e nuvemshop/imagens.csv (estoque de 06/11, fotos conferidas).
Saída:   site/_fonte/dados/catalogo.json
         site/relatorios/fora-do-site.csv          (o que ficou fora e por quê: mandar pra loja confirmar)
         site/relatorios/categorias-corrigidas.csv (produto, de, para)

Preço = coluna "Venda" do relatório do sistema (preço de balcão). Custo nunca vai para o site.
Uso: python -I catalogo.py   (dentro de site/_fonte)
"""
import csv, json, re, unicodedata, collections
from pathlib import Path

AQUI = Path(__file__).resolve().parent
PROJ = AQUI.parent.parent
NUV = PROJ / 'nuvemshop'
REL = AQUI.parent / 'relatorios'
DADOS = AQUI / 'dados'

def slug(s):
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')

# ---------------------------------------------------------------- correções de categoria (conferidas uma a uma em 19/11)
P = 'Peças'
CORRECOES = [
    (r'^Bico Universal para Mangueiras de Hidrata', 'Acessórios > Caramanholas e Suportes'),
    (r'^Cartucho Hidráulico para Garfo', f'{P} > Quadros e Suspensões > Suspensões e Garfos'),
    (r'^Trava Braco Esquerdo Pedivela', f'{P} > Transmissão > Pedivelas e Coroas'),
    (r'^Trava com Regulagem para Sapatilha', 'Vestuário > Sapatilhas'),          # fivela/catraca da sapatilha
    (r'^Trava do Cassete', f'{P} > Transmissão > Cassetes e Roda Livre'),
    (r'^Trava para Garfo', f'{P} > Quadros e Suspensões > Suspensões e Garfos'),
    (r'^Sensor de Velocidade E-bike', f'{P} > Componentes > Outros Componentes'),
    (r'^Capa Borracha', f'{P} > Componentes > Peças de STI e Manetes'),
    (r'^Castanha de Selim', f'{P} > Componentes > Selins'),
    (r'^Ciclo Treinador Interativo', 'Acessórios > Rolos de Treino'),
    (r'^Fita para Aro', f'{P} > Rodas e Pneus > Tubeless e Reparo'),
    (r'^Fita para Guidão', f'{P} > Componentes > Manoplas e Fitas de Guidão'),
    (r'^Kit Adaptador Boost', f'{P} > Componentes > Eixos, Rolamentos e Parafusos'),
    (r'^Kit Conduíte Pro Jagwire', f'{P} > Componentes > Canotes e Abraçadeiras'),
    (r'^Cabo Pro Dropper', f'{P} > Componentes > Canotes e Abraçadeiras'),
    (r'^Kit Conversão Single Speed', f'{P} > Transmissão > Grupos e Kits'),
    (r'^Kit Reparo Boa Sapatilha', 'Vestuário > Sapatilhas'),
    (r'^Kit Upgrade Shimano', f'{P} > Transmissão > Grupos e Kits'),
    (r'^Kit de Seringas', f'{P} > Freios > Adaptadores e Reparos'),
    (r'^Miolo de Válvula', f'{P} > Rodas e Pneus > Tubeless e Reparo'),
    (r'^Ponta para Martelo', 'Ferramentas'),
    (r'^Protetor Cabeamento Interno', f'{P} > Freios > Cabos, Conduítes e Mangueiras'),
    (r'^Squeeze Suplemento', 'Acessórios > Caramanholas e Suportes'),
    (r'^Tec 50 Fluido', 'Manutenção e Limpeza > Lubrificantes'),
    (r'^Bicicleta Aro 20 Barbie', 'Bicicletas > Infantis e Juvenis'),
    (r'^Bicicleta Aro 26 .*Model Feminina com Cest', 'Bicicletas > Urbanas e Passeio'),
    (r'^Bicicleta Foxer Maori', 'Bicicletas > Urbanas e Passeio'),
    (r'^Bicicleta Super Forte', 'Bicicletas > Urbanas e Passeio'),
    (r'^Ferramenta Reparo Tubel', f'{P} > Rodas e Pneus > Tubeless e Reparo'),
    (r'^Cola Unium', f'{P} > Rodas e Pneus > Tubeless e Reparo'),
    (r'^Creme Anti Atrito', 'Acessórios > Outros Acessórios'),
    (r'^Adaptador Alumínio (FM|PM)/', f'{P} > Freios > Adaptadores e Reparos'),
    (r'^Adaptador Suporte de Garrafa', 'Acessórios > Caramanholas e Suportes'),
    (r'^Adaptador de Válvula', f'{P} > Rodas e Pneus > Câmaras de Ar'),
    (r'^Espaçador .*(Caixa de Direção|A Set)', f'{P} > Componentes > Caixa de Direção'),
    (r'^Espaçador do Cassete', f'{P} > Transmissão > Cassetes e Roda Livre'),
    (r'^Núcleo (Completo|para Roda)', f'{P} > Rodas e Pneus > Cubos'),
    (r'^Parafuso de Sangria|^Parafuso do Banjo', f'{P} > Freios > Adaptadores e Reparos'),
    (r'^Pino de Reposição Chave Corrente', 'Ferramentas'),
    (r'^Reparo Ictus GPS', 'Acessórios > Ciclocomputadores e GPS'),
    (r'^Tampa (de )?Válvula', f'{P} > Rodas e Pneus > Câmaras de Ar'),
    (r'^Rolamento Tripeak Caixa de Direção', f'{P} > Componentes > Caixa de Direção'),
    (r'^Suporte (Bicicleta Vertical|de Chão|para Bicicleta)', 'Acessórios > Transbikes e Suportes de Bike'),
    (r'^Suporte Ictus CO2', 'Acessórios > Bombas e CO2'),
    (r'^Suporte Roda para Rolo', 'Acessórios > Rolos de Treino'),
    (r'^Apoio de Roda Absolute', 'Acessórios > Rolos de Treino'),             # calço da roda dianteira no rolo
    (r'^Correia para Rolo', 'Acessórios > Rolos de Treino'),
    (r'^Espelho Retrovisor', 'Acessórios > Buzinas, Luzes e Retrovisores'),
    (r'^Selim Assento Dianteiro', 'Acessórios > Infantil'),                  # assento infantil no quadro
    (r'^Cabo (de )?Câmbio', f'{P} > Transmissão > Peças de Câmbio'),
    (r'^Mola Interna Freehub', f'{P} > Rodas e Pneus > Cubos'),
    (r'^Mola de Tens', f'{P} > Transmissão > Peças de Câmbio'),
    (r'^Alavanca (de Freio|do Manete de Freio)', f'{P} > Freios > Manetes'),
    (r'^Lock Ring Coroa', f'{P} > Transmissão > Pedivelas e Coroas'),
    (r'^(Kit Transmissão|Transmissão )', f'{P} > Transmissão > Grupos e Kits'),
    (r'^Movimento de Direção', f'{P} > Componentes > Caixa de Direção'),
]
CORRECOES = [(re.compile(a), b) for a, b in CORRECOES]

# ---------------------------------------------------------------- nomes
TROCAS = [  # palavra errada -> certa (palavra inteira)
    ('Hidratacao', 'Hidratação'), ('Tubelles', 'Tubeless'), ('Perfomance', 'Performance'), ('Perfomanc', 'Performance'),
    ('Remocao', 'Remoção'), ('Tensao', 'Tensão'), ('Vedacao', 'Vedação'), ('Braco', 'Braço'), ('Reversivel', 'Reversível'),
    ('Pistoes', 'Pistões'), ('Pistaos', 'Pistões'), ('Pistoe', 'Pistões'), ('Multifuncao', 'Multifunção'),
    ('Assimetrica', 'Assimétrica'), ('Cadencia', 'Cadência'), ('Macico', 'Maciço'), ('Litio', 'Lítio'),
    ('Vasado', 'Vazado'), ('Vasada', 'Vazada'), ('Tubarao', 'Tubarão'), ('Serie', 'Série'),
]
def corrige_nome(nome, cat):
    for a, b in TROCAS:
        nome = re.sub(rf'\b{a}\b', b, nome)
    if cat.endswith('Movimento Central'):
        nome = nome.replace(' Selim ', ' Selado ')                      # "MOV. CENTRAL SEL." = selado
    nome = re.sub(r'^Bicicleta Quadro ', 'Quadro ', nome)
    nome = re.sub(r'^Bicicleta Pro X Aro 20 QUADRO/GARFO', 'Quadro e Garfo Pro X Aro 20', nome)
    nome = re.sub(r'^QUADRO/GARFO', 'Quadro e Garfo', nome)
    nome = re.sub(r'^CICLOCOMPUTADOR/GPS', 'Ciclocomputador GPS', nome)
    nome = re.sub(r'^BAR-ENDS', 'Bar End', nome)
    return nome

# ---------------------------------------------------------------- fora do site (até a loja confirmar)
# nome fala em caixa/tubo/display/rolo, mas o preço do sistema é por unidade ou por metro: o cliente ia achar que leva a caixa
UNIDADE_DUVIDOSA = {
    '9020', '4034', '2170', '9097', '8440', '8020', '8021', '6313', '7086', '8411', '6959', '5805', '817', '1992',
    '7801', '7802', '7284', '7101', '7107', '7109', '7108', '7106',
}

MARCAS_EXTRA = ['Giro', 'Fizik', 'Finish Line', 'Zéfal', 'Park Tool', 'Jagwire', 'Manitou', 'Kineticore', 'Elleven',
                'Tripeak', 'Token', 'Navihood', 'Xplova', 'Vzan', 'Arisun', 'Chaoyang', 'Levorin', 'Kenda', 'Pirelli',
                'Tacx', 'GTA', 'ERT', 'Foxer', 'Caloi', 'Oggi', 'Sense', 'Athor', 'Nathor', 'Wester', 'Vipal', 'Prologo',
                'Kalf', 'Sentec', 'High One', 'WG Sports', 'Absolute', 'Shimano', 'SRAM', 'Ictus', 'KMC', 'Motul', 'Algoo',
                'FourLab', 'Beta Fuel', 'Wellgo', 'ZTTO', 'TSW', 'Streetgo', 'Velo', 'Elite', 'Morgan Blue', 'Tec Bike']
NORMALIZA_MARCA = {'Fsa': 'FSA', 'Pro': 'PRO'}

def num(s):
    try: return float(s.replace(',', '.'))
    except Exception: return 0.0

COM_ARO = ('Bicicletas', 'Peças > Rodas e Pneus > Pneus', 'Peças > Rodas e Pneus > Câmaras', 'Peças > Rodas e Pneus > Rodas',
           'Peças > Quadros e Suspensões', 'Acessórios > Infantil')

def aro_de(nome):
    m = re.search(r'\bAro (\d{2})\b', nome) or re.search(r'\b(12|14|16|20|24|26|29)(?=[x" ]|\.\d|$)', nome) \
        or re.search(r'\b(700)\s?[xXC]', nome)
    if not m: return None
    a = m.group(1)
    return '700c' if a == '700' else a

def vel_de(nome):
    m = re.search(r'\b(\d{1,2}) ?V(el|eloc|elocidades)?\b', nome) or re.search(r'\b(\d{1,2}) ?Speed\b', nome) \
        or re.search(r'\b(\d{1,2})S\b', nome)
    if not m: return None
    v = int(m.group(1))
    return f'{v}v' if 6 <= v <= 12 else None

def main():
    linhas = list(csv.DictReader(open(NUV / 'produtos-com-foto.csv', encoding='utf-8'), delimiter=';'))
    imgs = list(csv.DictReader(open(NUV / 'imagens.csv', encoding='utf-8-sig')))
    img_por_prod = collections.defaultdict(list); img_por_sku = {}
    for x in imgs:
        a = x['Arquivo']
        if a not in img_por_prod[x['Identificador URL']]: img_por_prod[x['Identificador URL']].append(a)
        img_por_sku.setdefault(x['SKU'], a)

    marcas_conhecidas = sorted({x['Marca'] for x in linhas if x['Marca']} | set(MARCAS_EXTRA), key=len, reverse=True)
    grupos = collections.OrderedDict()
    for x in linhas: grupos.setdefault(x['Identificador URL'], []).append(x)

    produtos, fora, corrigidas = [], [], []
    for ident, rows in grupos.items():
        base = rows[0]
        cat = base['Categorias']
        for rx, nova in CORRECOES:
            if rx.search(base['Nome']):
                if nova != cat: corrigidas.append((base['SKU'], base['Nome'], cat, nova))
                cat = nova; break
        nome_antigo = base['Nome']
        nome = corrige_nome(nome_antigo, cat)
        marca = NORMALIZA_MARCA.get(base['Marca'], base['Marca'])
        if not marca:
            for m in marcas_conhecidas:
                if re.search(rf'(?<![\w]){re.escape(m)}(?![\w])', nome, re.I): marca = NORMALIZA_MARCA.get(m, m); break
        vars_ = []
        for r in rows:
            preco, custo = num(r['Preço']), num(r['Custo'])
            motivo = None
            if preco <= 0: motivo = 'sem preço de venda no sistema'
            elif custo > preco: motivo = f'custo (R$ {custo:.2f}) maior que o preço (R$ {preco:.2f}): cadastro por caixa ou preço errado'
            elif r['SKU'] in UNIDADE_DUVIDOSA: motivo = 'nome fala em caixa/tubo/display/metro, mas o preço é de unidade: confirmar como vende'
            rot = [v for v in (r['Valor da variação 1'], r['Valor da variação 2'], r['Valor da variação 3']) if v]
            if motivo:
                fora.append((r['SKU'], nome + (' · ' + ' / '.join(rot) if rot else ''), f'{preco:.2f}', motivo)); continue
            attrs = {}
            for i in (1, 2, 3):
                n, v = r[f'Nome da variação {i}'], r[f'Valor da variação {i}']
                if n and v: attrs[n] = v
            vars_.append(dict(sku=r['SKU'], attrs=attrs, preco=round(preco, 2),
                              img=img_por_sku.get(r['SKU']), peso=num(r['Peso (kg)'])))
        if not vars_: continue
        desc = base['Descrição'].replace(nome_antigo, nome)
        for a, b in TROCAS: desc = re.sub(rf'\b{a}\b', b, desc)
        precos = [v['preco'] for v in vars_]
        produtos.append(dict(
            id=ident, nome=nome, cat=cat.split(' > '), marca=marca or '', desc=desc,
            seo_titulo=corrige_nome(base['Título para SEO'], cat), seo_desc=base['Descrição para SEO'].replace(nome_antigo, nome),
            preco_min=min(precos), preco_max=max(precos), vars=vars_, imgs=img_por_prod.get(ident, []),
            aro=aro_de(nome) if cat.startswith(COM_ARO) else None,
            vel=vel_de(nome) if cat.startswith(f'{P} > Transmissão') else None,
        ))

    # bike igual em tamanhos diferentes (ex.: Oggi Cattura L e M) vira um produto só, com "Tamanho" na variação
    TAM = r'(?:\bTam\. (PP|XS|S|M|L|XL|G|GG)\b| (PP|XS|S|M|L|XL)(?= \d{4}$))'
    def tam(nome):
        m = re.search(TAM, nome); return m and (m.group(1) or m.group(2))
    def chave(p):
        return tuple(sorted(w for w in re.sub(TAM, ' ', p['nome']).split() if w != 'Tam.'))
    bikes = collections.defaultdict(list)
    for p in produtos:
        if p['cat'][0] == 'Bicicletas' and re.search(TAM, p['nome']) and len(p['vars']) == 1: bikes[chave(p)].append(p)
    for grupo in bikes.values():
        if len(grupo) < 2: continue
        base = grupo[0]
        novas = []
        for p in grupo:
            v = dict(p['vars'][0]); v['attrs'] = {'Tamanho': tam(p['nome'])}
            novas.append(v)
        base['vars'] = sorted(novas, key=lambda v: ['PP', 'XS', 'S', 'P', 'M', 'L', 'G', 'XL', 'GG'].index(v['attrs']['Tamanho']))
        antigo = base['nome']
        base['nome'] = re.sub(r'\s+', ' ', re.sub(TAM, ' ', base['nome'])).strip()
        base['desc'] = base['desc'].replace(antigo, base['nome'])
        base['seo_desc'] = base['seo_desc'].replace(antigo, base['nome'])
        base['seo_titulo'] = base['nome'] + ' | Impacto Bike'
        for p in grupo:
            for a in p['imgs']:
                if a not in base['imgs']: base['imgs'].append(a)
        base['preco_min'] = min(v['preco'] for v in base['vars']); base['preco_max'] = max(v['preco'] for v in base['vars'])
        for p in grupo[1:]: produtos.remove(p)
        print('  bike juntada por tamanho:', base['nome'], [v['attrs']['Tamanho'] for v in base['vars']])

    # ordem fixa do menu
    ORDEM = ['Bicicletas', 'Peças', 'Acessórios', 'Capacetes e Óculos', 'Vestuário', 'Manutenção e Limpeza', 'Ferramentas',
             'Nutrição Esportiva']
    arvore = {}
    for p in produtos:
        no = arvore
        for parte in p['cat']: no = no.setdefault(parte, {})
    def monta(no, caminho):
        filhos = sorted(no, key=lambda k: (ORDEM.index(k) if k in ORDEM else 99, k)) if not caminho else sorted(no)
        out = []
        for k in filhos:
            cam = caminho + [k]
            n = sum(1 for p in produtos if p['cat'][:len(cam)] == cam)
            out.append(dict(nome=k, slug='/'.join(slug(c) for c in cam), caminho=cam, total=n, filhos=monta(no[k], cam)))
        return out
    cats = monta(arvore, [])

    DADOS.mkdir(parents=True, exist_ok=True); REL.mkdir(parents=True, exist_ok=True)
    json.dump(dict(categorias=cats, produtos=produtos), open(DADOS / 'catalogo.json', 'w', encoding='utf-8'), ensure_ascii=False)
    with open(REL / 'fora-do-site.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['Código', 'Produto', 'Preço no sistema', 'Por que ficou fora']); w.writerows(fora)
    with open(REL / 'categorias-corrigidas.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f, delimiter=';'); w.writerow(['Código', 'Produto', 'Estava em', 'Foi para']); w.writerows(corrigidas)
    skus = sum(len(p['vars']) for p in produtos)
    print(f'{len(produtos)} produtos ({skus} SKUs) no site · {len(fora)} SKUs fora · {len(corrigidas)} categorias corrigidas')
    for c in cats: print(f'  {c["total"]:5} {c["nome"]}')

if __name__ == '__main__':
    main()
