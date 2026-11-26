<?php
/*
 * Teste de instalação. Rode no servidor (SSH da Hostinger):
 *
 *   php testar.php                         -> testa conexão, token, empresa e mostra os campos que a API devolve
 *   php testar.php --certificado           -> mostra o certificado do servidor da API (para conferir com o Rider)
 *   php testar.php --certificado --salvar  -> salva esse certificado em ekoos-cert.pem
 *
 * Nada aqui grava no banco nem altera o site. O token nunca é impresso.
 */
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
require __DIR__ . '/ekoos.php';

function ok(string $m): void { echo "  [ok]   $m\n"; }
function falha(string $m): void { echo "  [FALHA] $m\n"; }
function info(string $m): void { echo "         $m\n"; }

echo "\n== Integração Impacto Bike x sistema da loja ==\n\n";

foreach (['curl', 'pdo', 'json', 'mbstring'] as $ext) {
    extension_loaded($ext) ? ok("extensão $ext") : falha("extensão $ext não está ativa no PHP");
}
(extension_loaded('pdo_sqlite') || extension_loaded('pdo_mysql'))
    ? ok('banco: ' . implode(', ', array_filter(['pdo_sqlite', 'pdo_mysql'], 'extension_loaded')))
    : falha('nem pdo_sqlite nem pdo_mysql');

try {
    $c = carregar_config();
    ok('config.php lido (token com ' . strlen($c['token']) . ' caracteres)');
} catch (Throwable $e) {
    falha($e->getMessage());
    exit(1);
}

// ---------- certificado ----------
if (in_array('--certificado', $argv, true)) {
    $host = parse_url($c['api_url'], PHP_URL_HOST);
    $porta = parse_url($c['api_url'], PHP_URL_PORT) ?: 443;
    // Só para LER o certificado e mostrar a impressão digital. Nenhum dado é enviado nessa conexão.
    $ctx = stream_context_create(['ssl' => [
        'capture_peer_cert' => true, 'verify_peer' => false, 'verify_peer_name' => false, 'SNI_server_name' => $host,
    ]]);
    $s = @stream_socket_client("ssl://$host:$porta", $en, $es, 15, STREAM_CLIENT_CONNECT, $ctx);
    if (!$s) {
        falha("não conectou em $host:$porta ($es). A hospedagem pode bloquear essa porta de saída.");
        exit(1);
    }
    $cert = stream_context_get_params($s)['options']['ssl']['peer_certificate'];
    openssl_x509_export($cert, $pem);
    $d = openssl_x509_parse($cert);
    $digital = strtoupper(implode(':', str_split(openssl_x509_fingerprint($cert, 'sha256'), 2)));
    echo "\nCertificado de $host:$porta\n";
    info('Nome: ' . ($d['subject']['CN'] ?? '?') . ' · emitido por: ' . ($d['issuer']['CN'] ?? '?'));
    info('Nomes válidos: ' . ($d['extensions']['subjectAltName'] ?? '(nenhum)'));
    info('Validade: ' . date('d/m/Y', $d['validFrom_time_t']) . ' a ' . date('d/m/Y', $d['validTo_time_t']));
    info("Impressão digital SHA-256:\n         $digital");
    echo "\n  Confira essa impressão digital com o Rider ANTES de salvar.\n";
    if (in_array('--salvar', $argv, true)) {
        file_put_contents(__DIR__ . '/ekoos-cert.pem', $pem);
        chmod(__DIR__ . '/ekoos-cert.pem', 0644);
        ok('salvo em ekoos-cert.pem. No config.php: \'certificado\' => __DIR__ . \'/ekoos-cert.pem\'');
    }
    exit(0);
}

if (($c['certificado'] ?? '') !== '' && !is_file($c['certificado'])) {
    falha('o certificado configurado ainda não existe: ' . $c['certificado']);
    info('Rode: php testar.php --certificado   (confira a impressão digital com o Rider e depois use --salvar)');
    info("Se o Rider já colocou certificado válido (Let's Encrypt), use 'certificado' => '' no config.php.");
    exit(1);
}
$api = new Ekoos($c);

// ---------- 1. conexão e token ----------
echo "\n1. Conexão e token (/status)\n";
$formas = [
    'configurada'          => $c['auth'],
    'Authorization Bearer' => ['tipo' => 'header', 'nome' => 'Authorization', 'prefixo' => 'Bearer '],
    'X-API-Key'            => ['tipo' => 'header', 'nome' => 'X-API-Key', 'prefixo' => ''],
    'X-Token'              => ['tipo' => 'header', 'nome' => 'X-Token', 'prefixo' => ''],
    'token (cabeçalho)'    => ['tipo' => 'header', 'nome' => 'token', 'prefixo' => ''],
    '?token= na URL'       => ['tipo' => 'query', 'nome' => 'token'],
];
$funcionou = null;
foreach ($formas as $nome => $auth) {
    try {
        $r = $api->get('/status', [], $auth);
        ok("token aceito na forma: $nome");
        info('status: ' . mb_substr(json_encode($r, JSON_UNESCAPED_UNICODE), 0, 200));
        $funcionou = $auth;
        break;
    } catch (EkoosErro $e) {
        if ($e->http === 401 || $e->http === 403) {
            info("$nome: recusado ($e->http)");
            continue;
        }
        falha($e->getMessage());
        if (str_contains($e->getMessage(), 'certificate') || str_contains($e->getMessage(), 'SSL')) {
            info('Problema de certificado. Rode: php testar.php --certificado');
        } elseif ($e->http === 0) {
            info('Sem conexão. Se for timeout, a hospedagem pode estar bloqueando a porta '
                . (parse_url($c['api_url'], PHP_URL_PORT) ?: 443) . ': pedir ao Rider para usar a 443.');
        }
        exit(1);
    }
}
if ($funcionou === null) {
    falha('nenhuma forma de enviar o token funcionou. Perguntar ao Rider qual cabeçalho a API usa.');
    exit(1);
}
if ($funcionou !== $c['auth']) {
    info('Ajuste no config.php:');
    info("'auth' => " . str_replace(["\n", '  '], ['', ' '], var_export($funcionou, true)) . ',');
}
$c['auth'] = $funcionou;
$api = new Ekoos($c);

// ---------- 2. produtos ----------
echo "\n2. Produtos (empresa {$c['empresa']}, 3 itens)\n";
try {
    $resp = $api->get('/cadastros/produtos', ['empresa' => $c['empresa'], 'pagina' => 1, 'tamanho' => 3]);
} catch (EkoosErro $e) {
    falha($e->getMessage());
    if ($e->http === 422) {
        info('Parâmetro recusado. Conferir o número da empresa com o Rider.');
    }
    exit(1);
}
$itens = extrair_lista($resp);
if ($itens === []) {
    falha('nenhum produto veio. Empresa errada? Resposta: ' . mb_substr(json_encode($resp, JSON_UNESCAPED_UNICODE), 0, 200));
    exit(1);
}
ok(count($itens) . ' produtos vieram. Campos do primeiro:');
$sensivel = '/custo|compra|margem|lucro|fornecedor|cmv/i';
foreach ($itens[0] as $k => $v) {
    $mostra = preg_match($sensivel, (string) $k) ? '(oculto: dado interno)' : mb_substr(json_encode($v, JSON_UNESCAPED_UNICODE), 0, 60);
    info(str_pad((string) $k, 24) . gettype($v) . '  ' . $mostra);
}

echo "\n3. Leitura que o site vai fazer\n";
$todosOk = true;
foreach (['codigo', 'preco', 'estoque', 'descricao', 'ativo'] as $campo) {
    [$tem, , $nomeReal] = achar_campo($itens[0], $c['campos'][$campo]);
    if ($tem) {
        ok("$campo <- \"$nomeReal\"");
    } elseif (in_array($campo, ['codigo', 'preco', 'estoque'], true)) {
        falha("$campo não encontrado. Ponha o nome certo em 'campos' => '$campo' no config.php");
        $todosOk = false;
    } else {
        info("$campo não encontrado (opcional)");
    }
}
foreach ($itens as $i) {
    $n = normalizar($i, $c['campos']);
    if ($n) {
        info(sprintf('cód %-8s preço %-10s estoque %-8s %s', $n['codigo'],
            $n['preco'] === null ? '-' : number_format($n['preco'], 2, ',', '.'),
            $n['estoque'] === null ? '-' : rtrim(rtrim(number_format($n['estoque'], 3, ',', ''), '0'), ','),
            $n['ativo'] ? '' : '(inativo)'));
    }
}

// ---------- 4. incremental ----------
echo "\n4. Filtro \"alterado_desde\" (últimas 24 h)\n";
try {
    $r = $api->get('/cadastros/produtos', ['empresa' => $c['empresa'], 'pagina' => 1, 'tamanho' => 500,
        'alterado_desde' => date('Y-m-d\TH:i:s', time() - 86400)]);
    ok(count(extrair_lista($r)) . ' produtos alterados nas últimas 24 h (até 500)');
    info('Venda no balcão hoje? Se o produto vendido não aparece aqui, o filtro não pega estoque:');
    info('a carga completa da noite e a conferência na compra cobrem isso.');
} catch (EkoosErro $e) {
    falha($e->getMessage());
}

echo $todosOk ? "\nTudo certo. Próximo passo: php sincronizar.php completo\n\n" : "\nAjuste o config.php e rode de novo.\n\n";
exit($todosOk ? 0 : 1);
