<?php
/* Banco local com o espelho de preço e estoque. Funciona com SQLite (padrão) ou MySQL. */
declare(strict_types=1);

function abrir_banco(array $c): PDO
{
    $dsn = $c['banco'];
    if (str_starts_with($dsn, 'sqlite:')) {
        $dir = dirname(substr($dsn, 7));
        if (!is_dir($dir)) {
            mkdir($dir, 0700, true);
        }
    }
    $pdo = new PDO($dsn, $c['banco_usuario'] ?? null, $c['banco_senha'] ?? null, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
    $mysql = $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql';
    if (!$mysql) {
        $pdo->exec('PRAGMA journal_mode=WAL');
        $pdo->exec('PRAGMA busy_timeout=5000');
    }
    $txt = $mysql ? 'VARCHAR(32)' : 'TEXT';
    $pdo->exec("CREATE TABLE IF NOT EXISTS estoque_produtos (
        codigo $txt PRIMARY KEY,
        preco DECIMAL(12,2) NULL,
        estoque DECIMAL(12,3) NULL,
        descricao VARCHAR(200) NULL,
        ativo SMALLINT NOT NULL DEFAULT 1,
        atualizado_em VARCHAR(19) NOT NULL,
        visto_em VARCHAR(19) NOT NULL
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS estoque_controle (
        chave $txt PRIMARY KEY,
        valor VARCHAR(255) NOT NULL
    )");
    $pdo->exec("CREATE TABLE IF NOT EXISTS estoque_limite (
        chave VARCHAR(80) PRIMARY KEY,
        janela INTEGER NOT NULL,
        total INTEGER NOT NULL
    )");
    return $pdo;
}

function eh_mysql(PDO $pdo): bool
{
    return $pdo->getAttribute(PDO::ATTR_DRIVER_NAME) === 'mysql';
}

function gravar_produto(PDO $pdo, array $p, string $agora): void
{
    static $sql = [];
    $k = eh_mysql($pdo) ? 'm' : 's';
    $sql[$k] ??= $pdo->prepare($k === 'm'
        ? 'INSERT INTO estoque_produtos (codigo,preco,estoque,descricao,ativo,atualizado_em,visto_em)
           VALUES (:c,:p,:e,:d,:a,:t,:t)
           ON DUPLICATE KEY UPDATE preco=VALUES(preco), estoque=VALUES(estoque), descricao=VALUES(descricao),
             ativo=VALUES(ativo), atualizado_em=VALUES(atualizado_em), visto_em=VALUES(visto_em)'
        : 'INSERT INTO estoque_produtos (codigo,preco,estoque,descricao,ativo,atualizado_em,visto_em)
           VALUES (:c,:p,:e,:d,:a,:t,:t)
           ON CONFLICT(codigo) DO UPDATE SET preco=excluded.preco, estoque=excluded.estoque,
             descricao=excluded.descricao, ativo=excluded.ativo, atualizado_em=excluded.atualizado_em,
             visto_em=excluded.visto_em');
    $sql[$k]->execute([
        ':c' => $p['codigo'], ':p' => $p['preco'], ':e' => $p['estoque'],
        ':d' => $p['descricao'], ':a' => $p['ativo'] ? 1 : 0, ':t' => $agora,
    ]);
}

function ler_controle(PDO $pdo, string $chave): ?string
{
    $st = $pdo->prepare('SELECT valor FROM estoque_controle WHERE chave = ?');
    $st->execute([$chave]);
    $v = $st->fetchColumn();
    return $v === false ? null : (string) $v;
}

function gravar_controle(PDO $pdo, string $chave, string $valor): void
{
    $pdo->prepare('DELETE FROM estoque_controle WHERE chave = ?')->execute([$chave]);
    $pdo->prepare('INSERT INTO estoque_controle (chave, valor) VALUES (?, ?)')->execute([$chave, $valor]);
}

/** Limite simples por chave (ex.: IP) dentro de uma janela de 60 s. Devolve false se passou do limite. */
function dentro_do_limite(PDO $pdo, string $chave, int $max): bool
{
    $janela = intdiv(time(), 60);
    $pdo->beginTransaction();
    try {
        $st = $pdo->prepare('SELECT janela, total FROM estoque_limite WHERE chave = ?');
        $st->execute([$chave]);
        $r = $st->fetch();
        $total = ($r && (int) $r['janela'] === $janela) ? (int) $r['total'] + 1 : 1;
        $pdo->prepare('DELETE FROM estoque_limite WHERE chave = ? OR janela < ?')->execute([$chave, $janela - 5]);
        $pdo->prepare('INSERT INTO estoque_limite (chave, janela, total) VALUES (?, ?, ?)')->execute([$chave, $janela, $total]);
        $pdo->commit();
    } catch (Throwable $e) {
        $pdo->rollBack();
        throw $e;
    }
    return $total <= $max;
}

/** Escreve o arquivo público lido pelo site: só preço e disponibilidade (quantidade limitada ao teto). */
function exportar_publico(PDO $pdo, array $c): int
{
    $teto = (int) ($c['teto_publico'] ?? 10);
    $itens = [];
    foreach ($pdo->query('SELECT codigo, preco, estoque, ativo FROM estoque_produtos') as $r) {
        $q = ($r['ativo'] && $r['estoque'] !== null) ? (int) max(0, min($teto, floor((float) $r['estoque']))) : 0;
        $itens[$r['codigo']] = [$r['preco'] === null ? null : round((float) $r['preco'], 2), $q];
    }
    ksort($itens, SORT_NATURAL);
    $json = json_encode(['gerado_em' => date('c'), 'teto' => $teto, 'itens' => $itens],
        JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);

    $destino = $c['arquivo_publico'];
    if (!is_dir(dirname($destino))) {
        mkdir(dirname($destino), 0755, true);
    }
    $tmp = $destino . '.tmp';
    file_put_contents($tmp, $json, LOCK_EX);
    rename($tmp, $destino);   // troca de uma vez: o site nunca lê arquivo pela metade
    return count($itens);
}
