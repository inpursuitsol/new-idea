<?php
/**
 * Plugin Name: InPursuit Jobs Discovery
 * Description: Makes /jobs/ and each role easier for search engines to list. Upload this file to wp-content/mu-plugins/ on inpursuit.co.in. Also upload the IndexNow key file from site/ to the web root.
 *
 * Hub page: canonical URL plus an ItemList of open roles.
 * Role page: rewrites JobPosting JSON-LD so titles are real characters (en dash) instead of &#8211;.
 */

if (!defined('ABSPATH')) {
    exit;
}

function inpursuit_is_jobs_hub(): bool
{
    if (is_page('jobs')) {
        return true;
    }
    return function_exists('is_post_type_archive') && is_post_type_archive('job');
}

function inpursuit_decode_schema_strings($value)
{
    if (is_string($value)) {
        return html_entity_decode($value, ENT_QUOTES | ENT_HTML5, 'UTF-8');
    }
    if (!is_array($value)) {
        return $value;
    }
    $out = [];
    foreach ($value as $key => $item) {
        $out[$key] = inpursuit_decode_schema_strings($item);
    }
    return $out;
}

function inpursuit_salary_from_title(string $title): ?array
{
    if (!preg_match('/(\d+(?:\.\d+)?)\s*lpa/i', $title, $match)) {
        return null;
    }
    $amount = (int) round(((float) $match[1]) * 100000);
    if ($amount <= 0) {
        return null;
    }
    return [
        '@type' => 'MonetaryAmount',
        'currency' => 'INR',
        'value' => [
            '@type' => 'QuantitativeValue',
            'value' => $amount,
            'unitText' => 'YEAR',
        ],
    ];
}

function inpursuit_enrich_jobposting(array $data): array
{
    $clean = inpursuit_decode_schema_strings($data);
    $title = (string) ($clean['title'] ?? '');
    if (empty($clean['baseSalary'])) {
        $salary = inpursuit_salary_from_title($title);
        if ($salary !== null) {
            $clean['baseSalary'] = $salary;
        }
    }
    $description = wp_strip_all_tags((string) ($clean['description'] ?? ''));
    $description = trim(preg_replace('/\s+/', ' ', $description) ?? $description);
    if (strlen($description) < 150) {
        $clean['description'] = trim((string) ($clean['description'] ?? ''))
            . '<p>Apply with your resume on InPursuit. This is a full-time role in India. '
            . 'Use the form on this page to send your CV.</p>';
    }
    return $clean;
}

add_action('wp_head', function () {
    if (!inpursuit_is_jobs_hub()) {
        return;
    }

    $url = 'https://inpursuit.co.in/jobs/';
    echo '<link rel="canonical" href="' . esc_url($url) . "\" />\n";

    $jobs = get_posts([
        'post_type' => 'job',
        'post_status' => 'publish',
        'numberposts' => 50,
        'orderby' => 'modified',
        'order' => 'DESC',
    ]);

    $items = [];
    $position = 1;
    foreach ($jobs as $job) {
        $items[] = [
            '@type' => 'ListItem',
            'position' => $position,
            'url' => get_permalink($job),
            'name' => html_entity_decode(get_the_title($job), ENT_QUOTES | ENT_HTML5, 'UTF-8'),
        ];
        $position++;
    }

    $graph = [
        '@context' => 'https://schema.org',
        '@type' => 'CollectionPage',
        '@id' => $url,
        'name' => 'Open jobs in India',
        'url' => $url,
        'isPartOf' => [
            '@type' => 'WebSite',
            'name' => 'InPursuit',
            'url' => 'https://inpursuit.co.in/',
        ],
        'mainEntity' => [
            '@type' => 'ItemList',
            'numberOfItems' => count($items),
            'itemListElement' => $items,
        ],
    ];

    echo '<script type="application/ld+json">'
        . wp_json_encode($graph, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES)
        . "</script>\n";
}, 20);

add_action('template_redirect', function () {
    if (!is_singular('job')) {
        return;
    }

    ob_start(function ($html) {
        if (!is_string($html) || $html === '') {
            return $html;
        }
        return preg_replace_callback(
            '#<script([^>]*type=["\']application/ld\+json["\'][^>]*)>(.*?)</script>#s',
            function ($match) {
                $data = json_decode($match[2], true);
                if (!is_array($data) || ($data['@type'] ?? '') !== 'JobPosting') {
                    return $match[0];
                }
                $clean = inpursuit_enrich_jobposting($data);
                $encoded = wp_json_encode($clean, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
                if (!is_string($encoded)) {
                    return $match[0];
                }
                return '<script' . $match[1] . '>' . $encoded . '</script>';
            },
            $html
        );
    });
});
