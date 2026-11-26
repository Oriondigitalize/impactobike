/*
 * Estoque e preço do sistema da loja no site (Impacto Bike).
 * Incluir DEPOIS do app.js:  <script src="/assets/estoque-site.js" defer></script>
 *
 * - Página de produto: mostra "Esgotado" e acerta o preço pelo último sincronismo (/dados/estoque.json).
 * - Sacola e fechamento: confere na hora com o sistema (/api/conferir-estoque.php) antes de seguir.
 *
 * Se a versão do site mudou os ids, ajuste só o bloco SEL abaixo.
 * O preço que vale na cobrança é sempre o do back-end (privado/conferir.php), nunca o da tela.
 */
(function () {
  'use strict';

  var SEL = {
    dadosProduto: '#dados-produto',   // existe só na página de produto
    sku: '#sku',                      // código da variação escolhida
    preco: '#preco',
    botaoAdd: '#btn-add',
    listaSacola: '#itens-sacola',     // página da sacola
    formFinalizar: '#form-finalizar', // página de fechamento
    chaveSacola: 'ib-sacola'          // localStorage usado pelo app.js
  };
  var BASE = document.documentElement.getAttribute('data-raiz') || '/';
  var URL_ESTOQUE = BASE + 'dados/estoque.json';
  var URL_CONFERIR = BASE + 'api/conferir-estoque.php';

  function $(s, r) { return (r || document).querySelector(s); }
  function brl(v) { return v.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }); }

  function lerSacola() {
    try {
      var s = JSON.parse(localStorage.getItem(SEL.chaveSacola) || '[]');
      return Array.isArray(s) ? s.filter(function (i) { return i && /^\d{1,9}$/.test(i.sku) && i.q > 0 && i.q < 100; }) : [];
    } catch (e) { return []; }
  }

  function aviso(el, texto, tipo) {
    var id = 'aviso-estoque';
    var a = document.getElementById(id);
    if (!texto) { if (a) a.remove(); return; }
    if (!a) {
      a = document.createElement('div');
      a.id = id;
      a.setAttribute('role', 'alert');
      a.className = 'aviso-estoque';
      el.parentNode.insertBefore(a, el);
    }
    a.dataset.tipo = tipo || 'erro';
    a.textContent = texto;
  }

  /* ---------- página de produto ---------- */
  function paginaProduto(dados) {
    var skuEl = $(SEL.sku), btn = $(SEL.botaoAdd), precoEl = $(SEL.preco);
    if (!skuEl || !btn) return;
    var textoOriginal = btn.textContent;

    function aplica() {
      var cod = (skuEl.textContent || '').replace(/\D/g, '').replace(/^0+(?=\d)/, '');
      var it = dados.itens[cod];
      if (!it) return;                          // produto ainda não sincronizado: deixa como está
      var preco = it[0], q = it[1];
      if (preco && precoEl) precoEl.textContent = brl(preco);
      if (q <= 0) {
        btn.disabled = true;
        btn.textContent = 'Esgotado';
        btn.dataset.esgotado = '1';
      } else if (btn.dataset.esgotado) {
        delete btn.dataset.esgotado;
        btn.disabled = false;
        btn.textContent = textoOriginal;
      }
    }
    // O app.js troca o código quando o cliente escolhe cor ou tamanho: reaplica.
    new MutationObserver(aplica).observe(skuEl, { childList: true, characterData: true, subtree: true });
    aplica();
  }

  /* ---------- conferência ao vivo ---------- */
  function conferir(itens) {
    return fetch(URL_CONFERIR, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ itens: itens.map(function (i) { return { sku: String(i.sku), q: i.q }; }) })
    }).then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    });
  }

  function problemas(resp) {
    var lista = [];
    Object.keys(resp.itens || {}).forEach(function (cod) {
      var i = resp.itens[cod];
      if (!i.disponivel) lista.push('cód. ' + cod + ' esgotou');
      else if (!i.estoque_ok) lista.push('cód. ' + cod + ' não tem ' + i.pedido + ' unidades');
    });
    return lista;
  }

  function paginaSacola(lista) {
    var itens = lerSacola();
    if (!itens.length) return;
    conferir(itens).then(function (r) {
      var p = problemas(r);
      aviso(lista, p.length ? 'Atenção: ' + p.join('; ') + '. Ajuste a sacola antes de fechar.' : '');
    }).catch(function () { /* sem conferência agora: o fechamento confere de novo */ });
  }

  function paginaFinalizar(form) {
    var liberado = false;
    // Captura antes do app.js: só deixa o envio seguir depois de conferir o estoque.
    form.addEventListener('submit', function (e) {
      if (liberado) { liberado = false; return; }
      e.preventDefault();
      e.stopImmediatePropagation();
      var itens = lerSacola();
      if (!itens.length) { aviso(form, 'Sua sacola está vazia.'); return; }
      var botao = form.querySelector('[type="submit"]');
      if (botao) botao.disabled = true;
      conferir(itens).then(function (r) {
        var p = problemas(r);
        if (!r.ok) {
          aviso(form, p.length ? 'Não deu para fechar: ' + p.join('; ') + '. Volte à sacola e ajuste.'
                               : 'Algum item mudou de preço ou saiu do catálogo. Volte à sacola e confira.');
          return;
        }
        aviso(form, '');
        liberado = true;
        if (form.requestSubmit) form.requestSubmit(); else form.dispatchEvent(new Event('submit', { cancelable: true }));
      }).catch(function () {
        aviso(form, 'Não conseguimos conferir o estoque agora. Tente de novo em instantes ou chame no WhatsApp.');
      }).then(function () { if (botao) botao.disabled = false; });
    }, true);
  }

  /* ---------- início ---------- */
  if ($(SEL.dadosProduto)) {
    fetch(URL_ESTOQUE + '?v=' + Math.floor(Date.now() / 300000), { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (d) { if (d && d.itens) paginaProduto(d); })
      .catch(function () { /* sem arquivo de estoque: a página segue como está */ });
  }
  var lista = $(SEL.listaSacola);
  if (lista) paginaSacola(lista);
  var form = $(SEL.formFinalizar);
  if (form) paginaFinalizar(form);
})();
