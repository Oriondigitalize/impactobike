<?php
/*
 * Sincroniza preço e estoque do sistema da loja com o site.
 *
 *   php sincronizar.php rapido     -> só o que mudou desde a última vez (cron a cada 10 min)
 *   php sincronizar.php completo   -> tudo de novo (cron 1x por noite) e marca o que sumiu como indisponível
 *
 * Código de saída: 0 ok · 1 erro · 2 sistema da loja fora do ar (nada alterado) · 3 já tem outra rodando.
 */
declare(strict_types=1);

if (PHP_SAPI !== 'cli') {
    http_response_code(404);
    exit;
}
require __DIR__ . '/ekoos.php';
require __DIR__ . '/banco.php';
date_default_timezone_set('America/Sao_Paulo');

$modo = $argv[1] ?? 'rapido';
if (!in_array($modo, ['rapido', 'completo'], true)) {
    fwrite(STDERR, "Uso: php sincronizar.php rapido|completo\n");
    exit(1);
}

function registrar(string $msg): void
{
    $linha = date('Y-m-d H:i:s') . " $msg\n";
    echo $linha;
    $dir = __DIR__ . '/dados';
    if (!is_dir($dir)) {
        mkdir($dir, 0700, true);
    }
    file_put_contents("$dir/sincronizar.log", $linha, FILE_APPEND | LOCK_EX);
}

// Uma de cada vez: se a anterior ainda está rodando, esta sai.
if (!is_dir(__DIR__ . '/dados')) {
    mkdir(__DIR__ . '/dados', 0700, true);
}
$trava = fopen(__DIR__ . '/dados/sincronizar.lock', 'c');
if (!flock($trava, LOCK_EX | LOCK_NB)) {
    registrar("[$modo] outra sincronização ainda está rodando, pulei");
    exit(3);
}

try {
    $c = carregar_config();
    $api = new Ekoos($c);
    $pdo = abrir_banco($c);

    try {
        $api->status();
    } catch (EkoosErro $e) {
        registrar("[$modo] sistema da loja fora do ar ou sem resposta, nada alterado: " . $e->getMessage());
        exit(2);
    }

    $inicio = date('Y-m-d H:i:s');
    $ultima = ler_controle($pdo, 'ultima_sincronizacao');
    if ($modo === 'rapido' && $ultima === null) {
        registrar('[rapido] primeira vez: fazendo a carga completa');
        $modo = 'completo';
    }
    $desde = null;
    if ($modo === 'rapido') {
        $folga = (int) ($c['folga_minutos'] ?? 10);
        $desde = date('Y-m-d\TH:i:s', strtotime($ultima) - $folga * 60);
    }

    $antes = (int) $pdo->query('SELECT COUNT(*) FROM estoque_produtos WHERE ativo = 1')->fetchColumn();
    $lidos = $gravados = $sem_codigo = 0;
    $pdo->beginTransaction();
    foreach ($api->produtos($desde) as $item) {
        $lidos++;
        $p = normalizar($item, $c['campos']);
        if ($p === null) {
            $sem_codigo++;
            continue;
        }
        gravar_produto($pdo, $p, $inicio);
        $gravados++;
        if ($gravados % 500 === 0) {
            $pdo->commit();
            $pdo->beginTransaction();
        }
    }
    $pdo->commit();

    if ($modo === 'completo' && $gravados === 0) {
        throw new RuntimeException("carga completa veio vazia ($lidos lidos). Empresa errada no config.php? Nada foi alterado.");
    }

    $sumidos = 0;
    if ($modo === 'completo') {
        // Segurança: só marca sumidos se a lista veio inteira (pelo menos 80% dos ativos que já tínhamos).
        if ($gravados > 0 && $gravados >= 0.8 * $antes) {
            $st = $pdo->prepare('UPDATE estoque_produtos SET ativo = 0, estoque = 0, atualizado_em = ? WHERE visto_em < ? AND ativo = 1');
            $st->execute([$inicio, $inicio]);
            $sumidos = $st->rowCount();
        } else {
            registrar("[completo] AVISO: vieram $gravados de $antes produtos; não marquei nenhum como sumido");
        }
    }

    gravar_controle($pdo, 'ultima_sincronizacao', $inicio);
    $pub = exportar_publico($pdo, $c);
    registrar("[$modo] ok: $lidos lidos, $gravados gravados, $sem_codigo sem código, $sumidos sumidos, $pub no arquivo público");
    exit(0);
} catch (Throwable $e) {
    if (isset($pdo) && $pdo->inTransaction()) {
        $pdo->rollBack();
    }
    registrar("[$modo] ERRO: " . $e->getMessage());
    exit(1);
}
