<?php
/*
 * Conferência na hora da compra: pergunta ao sistema da loja, produto a produto, se tem estoque e qual o preço.
 *
 * Uso no back-end do checkout (ANTES de cobrar):
 *   require '/caminho/privado/conferir.php';
 *   $r = conferir_itens(['1234' => 1, '5678' => 2]);
 *   if (!$r['ok']) { ... avisa o cliente e não cobra ... }
 *   // use $r['itens'][cod]['preco'] como preço oficial, nunca o preço que veio do navegador
 */
declare(strict_types=1);

require_once __DIR__ . '/ekoos.php';
require_once __DIR__ . '/banco.php';

/**
 * @param array<string,int> $pedido código => quantidade
 * @return array{ok:bool, fonte:string, itens:array<string,array{pedido:int, disponivel:bool, estoque_ok:bool, preco:?float}>}
 */
function conferir_itens(array $pedido, ?array $c = null, ?Ekoos $api = null, ?PDO $pdo = null): array
{
    $c ??= carregar_config();
    $api ??= new Ekoos($c, 1);   // uma tentativa só: se o sistema não responder, usa o espelho
    $pdo ??= abrir_banco($c);

    $agora = date('Y-m-d H:i:s');
    $fonte = 'sistema';
    $saida = [];
    $ok = true;

    foreach ($pedido as $cod => $q) {
        $cod = preg_replace('/\D/', '', (string) $cod);
        $q = (int) $q;
        if ($cod === '' || $q < 1) {
            continue;
        }
        $p = null;
        if ($fonte === 'sistema') {
            try {
                foreach ($api->produtos(null, (int) $cod) as $item) {
                    $n = normalizar($item, $c['campos']);
                    if ($n !== null && $n['codigo'] === (ltrim($cod, '0') ?: '0')) {
                        $p = $n;
                        break;
                    }
                }
                if ($p !== null) {
                    gravar_produto($pdo, $p, $agora);   // aproveita e atualiza o espelho
                } else {
                    $p = ['preco' => null, 'estoque' => 0.0, 'ativo' => false];   // não existe mais no sistema
                }
            } catch (EkoosErro $e) {
                $fonte = 'espelho';   // sistema fora: usa a última sincronização
            }
        }
        if ($fonte === 'espelho') {
            $st = $pdo->prepare('SELECT preco, estoque, ativo FROM estoque_produtos WHERE codigo = ?');
            $st->execute([ltrim($cod, '0') ?: '0']);
            $r = $st->fetch();
            $p = $r ? ['preco' => $r['preco'] === null ? null : (float) $r['preco'],
                       'estoque' => $r['estoque'] === null ? null : (float) $r['estoque'],
                       'ativo' => (bool) $r['ativo']]
                    : ['preco' => null, 'estoque' => 0.0, 'ativo' => false];
        }

        $estoque_ok = $p['ativo'] && $p['estoque'] !== null && $p['estoque'] >= $q;
        $disponivel = $p['ativo'] && $p['estoque'] !== null && $p['estoque'] >= 1;
        if (!$estoque_ok || $p['preco'] === null || $p['preco'] <= 0) {
            $ok = false;
        }
        $saida[$cod] = [
            'pedido'     => $q,
            'disponivel' => $disponivel,
            'estoque_ok' => $estoque_ok,
            'preco'      => $p['preco'] === null ? null : round($p['preco'], 2),
        ];
    }
    return ['ok' => $ok && $saida !== [], 'fonte' => $fonte, 'itens' => $saida];
}
