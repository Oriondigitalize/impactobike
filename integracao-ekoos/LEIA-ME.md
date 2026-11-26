# Integração do site com o sistema da loja (EkoOS)

Liga o site da Impacto Bike ao sistema da loja pela API que o Rider montou (`relay.ekoosweb.com:8095`).

**O que faz**
- A cada 10 minutos o servidor puxa do sistema o que mudou de preço e estoque. Uma vez por noite puxa tudo.
- Na página do produto, a variação sem estoque vira **"Esgotado"** e o preço segue o do sistema.
- Na sacola e no fechamento, confere **na hora** com o sistema se ainda tem estoque, antes de seguir.
- Se o sistema da loja cair, o site continua com os dados da última sincronização.

**O que não faz (a API não deixa, hoje)**
- **Não baixa o estoque no sistema quando o site vende.** A API só tem leitura. Até o Rider criar uma rota de
  venda, cada venda do site precisa ser lançada à mão no sistema.
- Não manda custo para o site: o custo nunca é lido nem guardado.

Testado com PHP 8.3 contra uma API simulada (certificado próprio, token em cabeçalho, JSON dentro de texto,
número no formato brasileiro, 3 páginas de produtos) e no navegador, com páginas reais do site.

---

## Onde cada coisa vai na Hostinger

Na Hostinger, cada domínio fica em `/home/uXXXXXXXXX/domains/<domínio>/`. O `public_html` é o que aparece
na internet. A pasta `privado` vai **ao lado** dele, nunca dentro.

```
/home/uXXXXXXXXX/domains/lojaimpactobike.com.br/
├── privado/                     <- NÃO público: token, banco, scripts
│   ├── config.php               (você cria a partir do config.exemplo.php)
│   ├── ekoos.php  banco.php  conferir.php  sincronizar.php  testar.php  .htaccess
│   └── dados/                   (criada sozinha: banco SQLite e log)
└── public_html/                 <- o site
    ├── api/conferir-estoque.php
    ├── assets/estoque-site.js   assets/estoque-site.css
    └── dados/estoque.json       (gerado sozinho pela sincronização)
```

Precisa de **PHP 8.1 ou mais novo** (hPanel → Avançado → Configuração do PHP). Usa as extensões curl e
pdo_sqlite, que vêm ligadas na Hostinger.

---

## Passo a passo

### 1. Subir os arquivos
Pelo Gerenciador de Arquivos do hPanel (ou FTP), copie `privado/` e o conteúdo de `public_html/` para os
lugares acima.

### 2. Configurar
Em `privado/`, copie `config.exemplo.php` para `config.php` e preencha:
- `token`: o token do Rider. **Só aqui.** Não comitar, não mandar por WhatsApp de novo.
- `empresa`: o número da empresa da Impacto no sistema (perguntar ao Rider).
- `arquivo_publico`: confira se aponta para o `public_html/dados/estoque.json` do domínio.

### 3. Certificado do servidor da API
Hoje o servidor do Rider usa certificado próprio. **Não desligue a verificação.** Pelo SSH (hPanel → Avançado → Acesso SSH):

```
cd ~/domains/lojaimpactobike.com.br/privado
php testar.php --certificado
```
Mande a "Impressão digital SHA-256" para o Rider e peça para ele confirmar que é a do servidor dele. Se for:
```
php testar.php --certificado --salvar
```
Se o Rider colocar um certificado válido (Let's Encrypt), troque no config para `'certificado' => ''`.

### 4. Testar
```
php testar.php
```
Ele confere o PHP, descobre como o token deve ir (e diz o que pôr em `auth` no config), traz 3 produtos,
mostra os campos que a API devolve (custo aparece como oculto) e diz se achou **código, preço e estoque**.
Se algum não for achado, ponha o nome certo em `campos` no `config.php` e rode de novo.

Se der **timeout de conexão**, a hospedagem pode estar bloqueando a porta 8095 de saída. Aí é pedir ao
Rider para expor a API também na 443, ou abrir chamado na Hostinger.

### 5. Primeira carga
```
php sincronizar.php completo
```
Deve terminar com `ok: N lidos, N gravados...` e criar o `public_html/dados/estoque.json`.

### 6. Agendar (hPanel → Avançado → Cron Jobs)

| Quando | Comando |
|---|---|
| a cada 10 min (`*/10 * * * *`) | `/usr/bin/php /home/uXXXXXXXXX/domains/lojaimpactobike.com.br/privado/sincronizar.php rapido` |
| 3h da manhã (`0 3 * * *`) | `/usr/bin/php /home/uXXXXXXXXX/domains/lojaimpactobike.com.br/privado/sincronizar.php completo` |

O log fica em `privado/dados/sincronizar.log`. Códigos de saída: 0 ok, 1 erro, 2 sistema da loja fora
(nada alterado), 3 a anterior ainda estava rodando.

### 7. Ligar no site
Em **todas as páginas**, logo depois do `app.js`:
```html
<script src="/assets/estoque-site.js" defer></script>
```
E o estilo do aviso: cole o conteúdo de `estoque-site.css` no fim do `site.css` (ou inclua o arquivo).

Na versão gerada por `_fonte/gerar.py`, é a linha do `<script src="/assets/app.js" defer>` no modelo da página.
Se a sua versão mudou os ids (`#sku`, `#preco`, `#btn-add`, `#itens-sacola`, `#form-finalizar`) ou a chave
da sacola (`ib-sacola`), ajuste só o bloco `SEL` no começo do `estoque-site.js`.

A política de segurança (`_headers`) já aceita: o script é do próprio site e a consulta vai para o próprio
domínio. Não precisa liberar nada.

### 8. No back-end do pagamento (quando existir)
Antes de cobrar, confira de novo **no servidor**, com o preço do sistema:
```php
require '/home/uXXXXXXXXX/domains/lojaimpactobike.com.br/privado/conferir.php';
$r = conferir_itens(['1082' => 1, '263' => 2]);   // código => quantidade
if (!$r['ok']) { /* não cobra; avisa o cliente */ }
// preço oficial: $r['itens']['1082']['preco']  (nunca o que veio do navegador)
```
Se `$r['fonte'] === 'espelho'`, o sistema não respondeu e a conferência usou a última sincronização:
dá para seguir, mas vale avisar a loja para conferir esse pedido.

---

## Segurança
- Token só no `config.php`, fora do `public_html`. Nunca aparece em erro nem em log.
- Verificação do certificado sempre ligada (só confia no certificado salvo e conferido com o Rider).
- O site público só recebe preço e se tem estoque (quantidade limitada a 10). Sem custo, sem estoque exato.
- `conferir-estoque.php`: só POST, só do próprio domínio, até 30 itens, 20 consultas por minuto por visitante
  (o IP não é guardado em claro).
- A carga completa só marca produto como sumido se a lista veio inteira (pelo menos 80% dos ativos).

## Perguntas em aberto para o Rider
1. Número da `empresa` da Impacto.
2. O `alterado_desde` pega mudança de **estoque** (venda no balcão, entrada de nota) ou só cadastro e preço?
   Se não pegar, o site fica até a carga da noite sem ver o estoque baixando (a conferência na compra cobre).
3. Rota para lançar a venda do site e baixar o estoque.
4. Certificado válido no servidor e token só de leitura para o site.
