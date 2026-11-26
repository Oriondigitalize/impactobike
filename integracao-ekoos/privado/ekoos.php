<?php
/*
 * Cliente da API do sistema da loja (EkoOS Relay) e normalização dos produtos.
 * Só leitura. O token nunca aparece em mensagem de erro nem em log.
 */
declare(strict_types=1);

final class EkoosErro extends RuntimeException
{
    public function __construct(string $msg, public readonly int $http = 0)
    {
        parent::__construct($msg);
    }
}

function carregar_config(): array
{
    $arq = __DIR__ . '/config.php';
    if (!is_file($arq)) {
        throw new RuntimeException('Falta privado/config.php (copie de config.exemplo.php e preencha).');
    }
    $c = require $arq;
    if (!is_array($c) || empty($c['token']) || $c['token'] === 'COLE_O_TOKEN_AQUI') {
        throw new RuntimeException('config.php sem token.');
    }
    date_default_timezone_set($c['fuso'] ?? 'America/Sao_Paulo');
    return $c;
}

final class Ekoos
{
    /** $tentativas: 3 na sincronização; 1 na compra, para o cliente não ficar esperando. */
    public function __construct(private array $c, private int $tentativas = 3)
    {
    }

    /** GET numa rota da API. Devolve o JSON já decodificado. */
    public function get(string $rota, array $params = [], ?array $auth = null): mixed
    {
        $auth ??= $this->c['auth'];
        $headers = ['Accept: application/json'];
        if (($auth['tipo'] ?? 'header') === 'query') {
            $params[$auth['nome']] = $this->c['token'];
        } else {
            $headers[] = $auth['nome'] . ': ' . ($auth['prefixo'] ?? '') . $this->c['token'];
        }
        $params = array_filter($params, fn($v) => $v !== null && $v !== '');
        $url = rtrim($this->c['api_url'], '/') . $rota . ($params ? '?' . http_build_query($params) : '');

        $tentativas = max(1, $this->tentativas);
        for ($i = 1; ; $i++) {
            try {
                return $this->requisitar($url, $headers);
            } catch (EkoosErro $e) {
                // Repete só em falha de rede ou erro do servidor (5xx). 4xx é erro nosso: não adianta repetir.
                $temporario = $e->http === 0 || $e->http >= 500;
                if (!$temporario || $i >= $tentativas) {
                    throw $e;
                }
                sleep($i * 2);
            }
        }
    }

    private function requisitar(string $url, array $headers): mixed
    {
        $ch = curl_init($url);
        $opts = [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER     => $headers,
            CURLOPT_CONNECTTIMEOUT => $this->tentativas > 1 ? 10 : 5,
            CURLOPT_TIMEOUT        => $this->tentativas > 1 ? 60 : 15,
            CURLOPT_SSL_VERIFYPEER => true,   // nunca desligar
            CURLOPT_SSL_VERIFYHOST => 2,      // nunca desligar
            CURLOPT_ENCODING       => '',     // aceita gzip
            CURLOPT_USERAGENT      => 'ImpactoBike-Site/1.0',
        ];
        $cert = $this->c['certificado'] ?? '';
        if ($cert !== '') {
            if (!is_file($cert)) {
                throw new EkoosErro("Certificado configurado não existe: $cert");
            }
            $opts[CURLOPT_CAINFO] = $cert;    // confia só nesse certificado
        }
        curl_setopt_array($ch, $opts);
        $corpo = curl_exec($ch);
        $http = (int) curl_getinfo($ch, CURLINFO_RESPONSE_CODE);
        $erro = curl_error($ch);
        curl_close($ch);

        if ($corpo === false) {
            throw new EkoosErro('Sem resposta da API: ' . $erro, 0);
        }
        if ($http < 200 || $http >= 300) {
            $trecho = mb_substr(preg_replace('/\s+/', ' ', (string) $corpo), 0, 200);
            throw new EkoosErro("API respondeu HTTP $http: $trecho", $http);
        }
        return decodificar($corpo);
    }

    public function status(): mixed
    {
        return $this->get('/status');
    }

    /**
     * Percorre todas as páginas de /cadastros/produtos.
     * @return Generator<int, array> cada item bruto, como veio da API
     */
    public function produtos(?string $alteradoDesde = null, ?int $codProduto = null, ?string $busca = null): Generator
    {
        $tam = (int) ($this->c['tamanho_pagina'] ?? 500);
        for ($pagina = 1; $pagina <= 1000; $pagina++) {
            $resp = $this->get('/cadastros/produtos', [
                'empresa'        => $this->c['empresa'],
                'alterado_desde' => $alteradoDesde,
                'cod_produto'    => $codProduto,
                'busca'          => $busca,
                'pagina'         => $pagina,
                'tamanho'        => $tam,
            ]);
            $itens = extrair_lista($resp);
            foreach ($itens as $item) {
                yield $item;
            }
            if (count($itens) < $tam || $codProduto !== null) {
                return;
            }
        }
        throw new EkoosErro('Paginação passou de 1000 páginas: resposta inesperada da API.');
    }
}

/** A documentação diz que a resposta é "string": pode vir JSON dentro de texto. Trata os dois casos. */
function decodificar(string $corpo): mixed
{
    $d = json_decode($corpo, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        throw new EkoosErro('Resposta da API não é JSON.');
    }
    for ($i = 0; $i < 2 && is_string($d); $i++) {
        $d2 = json_decode($d, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            break;
        }
        $d = $d2;
    }
    return $d;
}

/** Acha a lista de produtos na resposta, venha ela solta ou dentro de uma chave. */
function extrair_lista(mixed $resp): array
{
    if (!is_array($resp)) {
        return [];
    }
    if (array_is_list($resp)) {
        return array_values(array_filter($resp, 'is_array'));
    }
    foreach (['produtos', 'dados', 'data', 'items', 'itens', 'resultado', 'registros', 'rows'] as $k) {
        foreach ($resp as $chave => $v) {
            if (strtolower((string) $chave) === $k && is_array($v) && array_is_list($v)) {
                return array_values(array_filter($v, 'is_array'));
            }
        }
    }
    // Um produto só, sem lista em volta.
    return [$resp];
}

/** Lê número em formato brasileiro ou americano: "1.234,56", "1234.56", 1234.56. */
function numero(mixed $v): ?float
{
    if ($v === null || $v === '' || is_bool($v)) {
        return null;
    }
    if (is_int($v) || is_float($v)) {
        return (float) $v;
    }
    $s = preg_replace('/[^\d,.\-]/', '', (string) $v);
    if ($s === '' || $s === '-') {
        return null;
    }
    if (str_contains($s, ',')) {
        $s = str_replace('.', '', $s);
        $s = str_replace(',', '.', $s);
    } elseif (substr_count($s, '.') > 1) {
        $s = str_replace('.', '', $s);
    }
    return is_numeric($s) ? (float) $s : null;
}

function achar_campo(array $item, array $nomes): array
{
    $baixo = array_change_key_case($item, CASE_LOWER);
    foreach ($nomes as $n) {
        $n = strtolower($n);
        if (array_key_exists($n, $baixo)) {
            return [true, $baixo[$n], $n];
        }
    }
    return [false, null, null];
}

/**
 * Converte o item da API no formato do site. Só os campos da lista "campos" do config são lidos:
 * custo e qualquer outro dado interno ficam de fora.
 * @return array{codigo:string, preco:?float, estoque:?float, descricao:?string, ativo:bool}|null
 */
function normalizar(array $item, array $campos): ?array
{
    [$tem, $cod] = achar_campo($item, $campos['codigo']);
    if (!$tem || $cod === null || $cod === '') {
        return null;
    }
    $codigo = preg_replace('/\D/', '', (string) $cod);
    if ($codigo === '') {
        return null;
    }
    $codigo = ltrim($codigo, '0') ?: '0';

    [, $preco] = achar_campo($item, $campos['preco']);
    [, $estoque] = achar_campo($item, $campos['estoque']);
    [, $desc] = achar_campo($item, $campos['descricao']);
    [$temAtivo, $ativo, $nomeAtivo] = achar_campo($item, $campos['ativo']);

    $ok = true;
    if ($temAtivo && $ativo !== null) {
        $a = is_string($ativo) ? strtolower(trim($ativo)) : $ativo;
        $verdade = in_array($a, [true, 1, '1', 's', 'sim', 'a', 'ativo', 'true', 't'], true);
        $ok = $nomeAtivo === 'inativo' ? !$verdade : $verdade;
    }

    return [
        'codigo'    => $codigo,
        'preco'     => numero($preco),
        'estoque'   => numero($estoque),
        'descricao' => $desc === null ? null : mb_substr(trim((string) $desc), 0, 200),
        'ativo'     => $ok,
    ];
}
