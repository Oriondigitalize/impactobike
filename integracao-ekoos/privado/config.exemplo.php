<?php
/*
 * Configuração da integração com o sistema da loja (EkoOS Relay).
 *
 * Copie este arquivo para "config.php" (na mesma pasta) e preencha.
 * O config.php fica FORA do public_html e nunca vai para o GitHub nem para o WhatsApp.
 */
return [
    // Endereço da API (sem barra no fim).
    'api_url' => 'https://relay.ekoosweb.com:8095',

    // Token que o Rider mandou. Só aqui, em nenhum outro lugar.
    'token' => 'COLE_O_TOKEN_AQUI',

    // Como o token vai na chamada. O "php testar.php" descobre e diz o que colocar aqui.
    // tipo: 'header' (cabeçalho) ou 'query' (parâmetro na URL).
    'auth' => ['tipo' => 'header', 'nome' => 'Authorization', 'prefixo' => 'Bearer '],

    // Número da empresa da Impacto no sistema (perguntar ao Rider).
    'empresa' => 1,

    // Certificado do servidor da API.
    // '' = certificado normal (Let's Encrypt etc.).
    // Caminho de um .pem = confiar SÓ nesse certificado (enquanto o servidor usar certificado próprio).
    // NUNCA desligar a verificação.
    'certificado' => __DIR__ . '/ekoos-cert.pem',

    // Banco local onde ficam preço e estoque sincronizados.
    // SQLite (padrão, não precisa criar nada) ou MySQL da Hostinger:
    //   'banco' => 'mysql:host=localhost;dbname=uXXXX_impacto;charset=utf8mb4',
    'banco'         => 'sqlite:' . __DIR__ . '/dados/estoque.sqlite',
    'banco_usuario' => null,
    'banco_senha'   => null,

    // Arquivo público que o site lê (preço e disponibilidade, sem custo e sem quantidade exata).
    // Ajuste para o public_html do domínio.
    'arquivo_publico' => dirname(__DIR__) . '/public_html/dados/estoque.json',

    'fuso'           => 'America/Sao_Paulo',
    'tamanho_pagina' => 500,
    // Folga ao pedir "alterado_desde", para não perder mudança gravada perto do horário da última sincronização.
    'folga_minutos'  => 10,
    // Teto de quantidade mostrado ao site (o público não precisa saber o estoque exato).
    'teto_publico'   => 10,

    // Nomes possíveis de cada campo na resposta da API (o primeiro que existir é usado).
    // O "php testar.php" mostra os nomes reais; ajuste se precisar.
    // Só estes campos são guardados. Custo nunca é lido.
    'campos' => [
        'codigo'    => ['cod_produto', 'codigo', 'cod', 'id_produto', 'id'],
        'preco'     => ['preco_venda', 'vlr_venda', 'valor_venda', 'preco', 'venda', 'pr_venda', 'preco1'],
        'estoque'   => ['estoque', 'saldo', 'qtd_estoque', 'estoque_atual', 'saldo_estoque', 'quantidade', 'qtde'],
        'descricao' => ['descricao', 'desc_produto', 'nome', 'produto'],
        'ativo'     => ['ativo', 'situacao', 'status', 'inativo'],
    ],
];
