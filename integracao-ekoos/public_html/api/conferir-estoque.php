<?php
/*
 * POST /api/conferir-estoque.php
 * Corpo: {"itens":[{"sku":"1234","q":1}, ...]}  (até 30 itens)
 * Resposta: {"ok":true|false, "fonte":"sistema"|"espelho", "itens":{"1234":{"pedido":1,"disponivel":true,"estoque_ok":true,"preco":199.9}}}
 *
 * Usado pela sacola e pelo fechamento para avisar o cliente antes de pagar.
 * Não substitui a conferência no back-end do pagamento (ver privado/conferir.php).
 */
declare(strict_types=1);

header('Content-Type: application/json; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

function responder(int $http, array $corpo): never
{
    http_response_code($http);
    echo json_encode($corpo, JSON_UNESCAPED_UNICODE);
    exit;
}

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    header('Allow: POST');
    responder(405, ['erro' => 'use POST']);
}
if (!str_starts_with(strtolower($_SERVER['CONTENT_TYPE'] ?? ''), 'application/json')) {
    responder(415, ['erro' => 'envie JSON']);
}
// Só o próprio site chama (o navegador manda Origin em POST).
$origem = $_SERVER['HTTP_ORIGIN'] ?? '';
$host = strtolower($_SERVER['HTTP_HOST'] ?? '');
$o = parse_url($origem);
$origemHost = strtolower(($o['host'] ?? '') . (isset($o['port']) ? ':' . $o['port'] : ''));
if ($origem !== '' && $origemHost !== $host) {
    responder(403, ['erro' => 'origem não permitida']);
}

$PRIVADO = dirname(__DIR__, 2) . '/privado';   // domains/<domínio>/privado
require $PRIVADO . '/conferir.php';

try {
    $c = carregar_config();
    $pdo = abrir_banco($c);

    $ip = $_SERVER['REMOTE_ADDR'] ?? '0';
    $chave = 'ip:' . substr(hash('sha256', $ip . '|' . $c['token']), 0, 32);   // não guarda o IP em claro
    if (!dentro_do_limite($pdo, $chave, 20)) {
        header('Retry-After: 60');
        responder(429, ['erro' => 'muitas consultas, tente em 1 minuto']);
    }

    $bruto = file_get_contents('php://input', false, null, 0, 8192);
    $dados = json_decode((string) $bruto, true);
    $itens = is_array($dados['itens'] ?? null) ? $dados['itens'] : [];
    if ($itens === [] || count($itens) > 30) {
        responder(400, ['erro' => 'mande de 1 a 30 itens']);
    }
    $pedido = [];
    foreach ($itens as $i) {
        $sku = is_array($i) ? (string) ($i['sku'] ?? '') : '';
        $q = is_array($i) ? (int) ($i['q'] ?? 0) : 0;
        if (!preg_match('/^\d{1,9}$/', $sku) || $q < 1 || $q > 99) {
            responder(400, ['erro' => 'item inválido']);
        }
        $pedido[$sku] = ($pedido[$sku] ?? 0) + $q;
    }

    responder(200, conferir_itens($pedido, $c, null, $pdo));
} catch (Throwable $e) {
    error_log('conferir-estoque: ' . $e->getMessage());
    responder(503, ['erro' => 'não deu para conferir agora']);
}
