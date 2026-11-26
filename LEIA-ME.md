# Site próprio da Impacto Bike

*Começado em 19/11/2026, depois que o Chefe trocou a Nuvemshop por site próprio.*

## Como está

**Prévia da vitrine pronta**, com o catálogo real: 1.610 produtos (1.881 variações de cor e tamanho), todos com foto
conferida e o **preço de venda de balcão** do sistema (coluna "Venda" do relatório de 06/11; o custo nunca vai para o site).

O **back-end ainda não existe**: a sacola funciona no navegador e o "Finalizar compra" é prévia (nada sai do navegador).
O back-end entra quando o gateway de pagamento for escolhido (ver "Próximo passo").

## Pastas

| Caminho | O que é |
|---|---|
| `_fonte/catalogo.py` | lê `nuvemshop/produtos-com-foto.csv`, corrige categoria e nome, tira o que tem preço duvidoso, gera `_fonte/dados/catalogo.json` |
| `_fonte/gerar.py` | gera o site estático em `publico/` (páginas, fotos WebP, índice da busca, cabeçalhos de segurança) |
| `_fonte/assets/` | `site.css`, `app.js`, fontes, logo |
| `_fonte/assets/cena.js`, `cena.css`, `cena/`, `vendor/` | **abertura animada da home** (veio do primeiro protótipo): Caloi em camadas que entra rodando, desmonta na rolagem e sai; cortina azul abre a loja. GSAP 3.13, ScrollTrigger e Lenis locais (sem CDN) |
| `_fonte/fotos/hero-oggi-cattura.png` | recorte antigo da Oggi (descartado: pixelado; não usar) |
| `relatorios/fora-do-site.csv` | **mandar para a loja:** 52 itens fora do site e o motivo (preço zero, custo maior que preço, caixa × unidade) |
| `relatorios/categorias-corrigidas.csv` | 99 produtos que mudaram de categoria (de → para) |
| `publico/` | o site pronto para subir (não editar à mão: o script sobrescreve) |

## Rodar de novo

```
cd site/_fonte
python -I catalogo.py
python -I gerar.py          # fotos já convertidas são puladas
```
Ver no PC: `python -m http.server 8080 -d ../publico` e abrir http://localhost:8080

## Decisões desta versão

- **Home em duas partes (Chefe, 19/11):** em cima, a abertura futurista do primeiro protótipo (motions das referências do
  21dev), agora em azul Shimano; cada peça que desmonta é um link para a categoria da loja, com a quantidade real. Embaixo,
  depois da cortina, a loja limpa. Quem desativa animação no sistema vê a bike parada. A bike da cena é a Caloi Elite Carbon
  (foto oficial da marca, do protótipo), usada como imagem de abertura, sem preço.

- **Identidade:** azul Shimano `#0099DC` em destaque (tirado do logo oficial atual da Shimano; a versão antiga em
  CorelDRAW usa `#0066B3`), preto `#0B0D10` e vermelho do logo da loja `#C8383F` (tirado do recorte do Instagram,
  baixa resolução: conferir com o vetor). Botão azul com texto preto (contraste AA). Fontes Barlow Condensed e Inter, locais.
- **Categorias:** 8 de topo no menu. Clicou numa, aparecem as subcategorias com foto; os filtros (marca, preço, aro,
  velocidades) ficam escondidos no botão "Filtros" e só aparecem os que fazem sentido na página.
- **Categorias novas:** Bicicletas > Urbanas e Passeio; Peças > Transmissão > Grupos e Kits.
- **Nomes corrigidos:** "Movimento Central Absolute Selim" virou "Selado" (SEL. no sistema = selado); "Bicicleta Quadro"
  virou "Quadro"; acentos (Hidratação, Pistões, Tubeless etc.).
- **Fora até a loja confirmar:** item com preço zero; custo maior que preço; nome de caixa/tubo/display/metro com preço de
  unidade (ex.: "Rolamento Tubo C/ 10" a R$ 35 é o preço de 1 rolamento).
- **Segurança já ativa na vitrine:** CSP fechada (só scripts e estilos do próprio site, nada inline), HSTS, nosniff,
  X-Frame-Options DENY, Permissions-Policy, COOP; nenhum script de terceiro; WhatsApp e mapa abrem em outra aba;
  campo-armadilha anti-robô no fechamento. Fora do Google (`noindex` e `robots.txt`) enquanto for prévia.
- **LGPD:** páginas Privacidade, Compra segura e Trocas e devoluções; checkout pede só o necessário; ofertas só com
  caixa marcada (opcional); sem cookie de propaganda.

## Pendente de validação (não inventar)

- [PENDENTE] Número do endereço (619, 595 sala SS1 ou 680). O site mostra sem número.
- [PENDENTE] E-mail de contato da loja (Privacidade usa só o WhatsApp como canal do titular).
- [PENDENTE] Lista de serviços da oficina (texto genérico de revisão, regulagem, bike fit).
- [PENDENTE] Regra própria de troca de tamanho (página mostra só o mínimo do CDC e "fale com a gente").
- [PENDENTE] CEP de Arcos para liberar retirada (usei 35588-000, do Google da loja).
- [PENDENTE] Prêmio Shimano Concept 2026 (citado em Quem somos; pedir a foto).
- [PENDENTE] Logo em vetor.

## Próximo passo: back-end

Depende de escolher o **gateway** (Rede da loja, Mercado Pago ou Pagar.me). Com ele: pedido no servidor com preço
recalculado, cartão por campo seguro do gateway (a loja nunca vê o número), Pix, webhook assinado, verificação
anti-robô (Turnstile) e limite de tentativas, banco com CPF e endereço criptografados, painel da loja com 2 etapas,
backup diário. Tudo descrito para o cliente em `/compra-segura/`.

## Integração com o sistema da loja

Em `integracao-ekoos/`: sincronização de preço e estoque com o sistema da loja (EkoOS) e conferência na hora da
compra. Passo a passo da instalação na Hostinger em `integracao-ekoos/LEIA-ME.md`.
