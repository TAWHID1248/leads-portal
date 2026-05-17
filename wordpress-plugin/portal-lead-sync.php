<?php
/**
 * Plugin Name: Portal Lead Sync
 * Description: Forwards form submissions from WPForms, Contact Form 7, Elementor Pro, or any form to the LeadPortal ingest API.
 * Version: 0.1.0
 * Author: LeadPortal
 * License: MIT
 */

if (!defined('ABSPATH')) {
    exit;
}

define('PLS_OPTION_KEY', 'portal_lead_sync_settings');
define('PLS_NONCE_ACTION', 'portal_lead_sync_save');
define('PLS_TEST_NONCE_ACTION', 'portal_lead_sync_test');

/* ---------- Settings storage ---------- */

function pls_get_settings() {
    $defaults = [
        'api_url'       => '',
        'api_key'       => '',
        'default_niche' => 'solar-usa',
        'source_type'   => 'SOLAR',
        'form_plugin'   => 'wpforms',
        'form_id'       => '',
        'field_map'     => "firstName=name\nlastName=last_name\nemail=email\nphone=phone\nstate=state",
    ];
    $stored = get_option(PLS_OPTION_KEY, []);
    return array_merge($defaults, is_array($stored) ? $stored : []);
}

/* ---------- Admin menu ---------- */

add_action('admin_menu', function () {
    add_options_page(
        'Portal Lead Sync',
        'Portal Lead Sync',
        'manage_options',
        'portal-lead-sync',
        'pls_render_settings_page'
    );
});

add_action('admin_post_portal_lead_sync_save', 'pls_handle_save');
add_action('admin_post_portal_lead_sync_test', 'pls_handle_test');

function pls_handle_save() {
    if (!current_user_can('manage_options')) {
        wp_die('Insufficient permissions.');
    }
    check_admin_referer(PLS_NONCE_ACTION);

    $new = [
        'api_url'       => esc_url_raw(trim($_POST['api_url'] ?? '')),
        'api_key'       => sanitize_text_field($_POST['api_key'] ?? ''),
        'default_niche' => sanitize_text_field($_POST['default_niche'] ?? ''),
        'source_type'   => in_array($_POST['source_type'] ?? '', ['SOLAR', 'SWEEPSTAKES'], true)
            ? $_POST['source_type'] : 'SOLAR',
        'form_plugin'   => sanitize_text_field($_POST['form_plugin'] ?? 'wpforms'),
        'form_id'       => sanitize_text_field($_POST['form_id'] ?? ''),
        'field_map'     => sanitize_textarea_field($_POST['field_map'] ?? ''),
    ];
    update_option(PLS_OPTION_KEY, $new);

    wp_safe_redirect(add_query_arg(['page' => 'portal-lead-sync', 'pls_saved' => 1], admin_url('options-general.php')));
    exit;
}

function pls_handle_test() {
    if (!current_user_can('manage_options')) {
        wp_die('Insufficient permissions.');
    }
    check_admin_referer(PLS_TEST_NONCE_ACTION);

    $sample = [
        'sourceType'   => 'SOLAR',
        'niche'        => 'solar-usa',
        'firstName'    => 'PluginTest',
        'lastName'     => 'Connection',
        'email'        => 'plugin-test+' . time() . '@example.com',
        'phone'        => '555-000-' . rand(1000, 9999),
        'state'        => 'TX',
        'isHomeowner'  => true,
        'monthlyBill'  => '$200-$300',
        'creditScore'  => 'Good',
        'sourcePage'   => home_url('/'),
        'utmSource'    => 'plugin-test',
    ];
    $result = pls_post_lead($sample, true);

    set_transient('pls_test_result', $result, 60);
    wp_safe_redirect(add_query_arg(['page' => 'portal-lead-sync', 'pls_tested' => 1], admin_url('options-general.php')));
    exit;
}

/* ---------- Settings page ---------- */

function pls_render_settings_page() {
    $s = pls_get_settings();
    $test_result = get_transient('pls_test_result');
    if ($test_result) {
        delete_transient('pls_test_result');
    }
    ?>
    <div class="wrap">
        <h1>Portal Lead Sync</h1>

        <?php if (!empty($_GET['pls_saved'])): ?>
            <div class="notice notice-success is-dismissible"><p>Settings saved.</p></div>
        <?php endif; ?>

        <?php if (!empty($_GET['pls_tested']) && $test_result): ?>
            <?php if (!empty($test_result['ok'])): ?>
                <div class="notice notice-success is-dismissible">
                    <p><strong>Test succeeded.</strong> HTTP <?php echo (int) $test_result['code']; ?>.
                       <code><?php echo esc_html(substr($test_result['body'], 0, 240)); ?></code></p>
                </div>
            <?php else: ?>
                <div class="notice notice-error is-dismissible">
                    <p><strong>Test failed.</strong> <?php echo esc_html($test_result['error'] ?? ''); ?></p>
                    <?php if (!empty($test_result['body'])): ?>
                        <p><code><?php echo esc_html(substr($test_result['body'], 0, 240)); ?></code></p>
                    <?php endif; ?>
                </div>
            <?php endif; ?>
        <?php endif; ?>

        <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
            <input type="hidden" name="action" value="portal_lead_sync_save">
            <?php wp_nonce_field(PLS_NONCE_ACTION); ?>

            <table class="form-table" role="presentation">
                <tr>
                    <th><label for="pls_api_url">Portal API URL</label></th>
                    <td><input id="pls_api_url" name="api_url" type="url" class="regular-text"
                               value="<?php echo esc_attr($s['api_url']); ?>"
                               placeholder="https://leads.example.com/api/v1/leads/ingest">
                        <p class="description">Full URL of the ingest endpoint.</p></td>
                </tr>
                <tr>
                    <th><label for="pls_api_key">API Key</label></th>
                    <td><input id="pls_api_key" name="api_key" type="text" class="regular-text"
                               value="<?php echo esc_attr($s['api_key']); ?>"></td>
                </tr>
                <tr>
                    <th><label for="pls_default_niche">Default Niche</label></th>
                    <td><input id="pls_default_niche" name="default_niche" type="text" class="regular-text"
                               value="<?php echo esc_attr($s['default_niche']); ?>"
                               placeholder="solar-usa"></td>
                </tr>
                <tr>
                    <th><label for="pls_source_type">Source Type</label></th>
                    <td><select id="pls_source_type" name="source_type">
                        <option value="SOLAR" <?php selected($s['source_type'], 'SOLAR'); ?>>SOLAR</option>
                        <option value="SWEEPSTAKES" <?php selected($s['source_type'], 'SWEEPSTAKES'); ?>>SWEEPSTAKES</option>
                    </select></td>
                </tr>
                <tr>
                    <th><label for="pls_form_plugin">Form plugin</label></th>
                    <td><select id="pls_form_plugin" name="form_plugin">
                        <option value="wpforms" <?php selected($s['form_plugin'], 'wpforms'); ?>>WPForms</option>
                        <option value="cf7" <?php selected($s['form_plugin'], 'cf7'); ?>>Contact Form 7</option>
                        <option value="elementor" <?php selected($s['form_plugin'], 'elementor'); ?>>Elementor Pro</option>
                        <option value="generic" <?php selected($s['form_plugin'], 'generic'); ?>>Generic (manual hook)</option>
                    </select></td>
                </tr>
                <tr>
                    <th><label for="pls_form_id">Form ID</label></th>
                    <td><input id="pls_form_id" name="form_id" type="text" class="regular-text"
                               value="<?php echo esc_attr($s['form_id']); ?>"
                               placeholder="(blank = all forms of the chosen plugin)"></td>
                </tr>
                <tr>
                    <th><label for="pls_field_map">Field mapping</label></th>
                    <td><textarea id="pls_field_map" name="field_map" rows="8" cols="60" class="large-text code"
                                  placeholder="firstName=name&#10;lastName=last_name&#10;email=email&#10;phone=phone"><?php
                            echo esc_textarea($s['field_map']);
                        ?></textarea>
                        <p class="description">One mapping per line. Left side is the portal field (camelCase), right side is the source field key in the submitted form.</p></td>
                </tr>
            </table>

            <?php submit_button('Save Settings'); ?>
        </form>

        <hr>

        <h2>Test connection</h2>
        <form method="post" action="<?php echo esc_url(admin_url('admin-post.php')); ?>">
            <input type="hidden" name="action" value="portal_lead_sync_test">
            <?php wp_nonce_field(PLS_TEST_NONCE_ACTION); ?>
            <p>Sends a sample SOLAR lead to your configured endpoint.</p>
            <?php submit_button('Send test lead', 'secondary'); ?>
        </form>
    </div>
    <?php
}

/* ---------- Field map parsing ---------- */

function pls_parse_field_map($text) {
    $map = [];
    foreach (preg_split("/\r\n|\n|\r/", (string) $text) as $line) {
        $line = trim($line);
        if ($line === '' || str_starts_with($line, '#')) {
            continue;
        }
        $pos = strpos($line, '=');
        if ($pos === false) {
            continue;
        }
        $portal_key = trim(substr($line, 0, $pos));
        $source_key = trim(substr($line, $pos + 1));
        if ($portal_key !== '' && $source_key !== '') {
            $map[$portal_key] = $source_key;
        }
    }
    return $map;
}

function pls_build_payload(array $fields, array $settings) {
    $map = pls_parse_field_map($settings['field_map']);
    $payload = [
        'sourceType' => $settings['source_type'],
        'niche'      => $settings['default_niche'],
        'sourcePage' => isset($_SERVER['HTTP_REFERER']) ? esc_url_raw($_SERVER['HTTP_REFERER']) : '',
    ];
    foreach ($map as $portal_key => $source_key) {
        if (array_key_exists($source_key, $fields)) {
            $payload[$portal_key] = $fields[$source_key];
        }
    }
    return $payload;
}

/* ---------- HTTP post ---------- */

function pls_post_lead(array $payload, $blocking = false) {
    $s = pls_get_settings();
    if (empty($s['api_url']) || empty($s['api_key'])) {
        return ['ok' => false, 'error' => 'API URL or API key missing.'];
    }
    $args = [
        'timeout'   => 5,
        'blocking'  => (bool) $blocking,
        'headers'   => [
            'Content-Type' => 'application/json',
            'X-API-KEY'    => $s['api_key'],
        ],
        'body'      => wp_json_encode($payload),
    ];
    $response = wp_remote_post($s['api_url'], $args);

    if (is_wp_error($response)) {
        $msg = $response->get_error_message();
        error_log('[portal-lead-sync] error: ' . $msg);
        return ['ok' => false, 'error' => $msg];
    }
    $code = wp_remote_retrieve_response_code($response);
    $body = wp_remote_retrieve_body($response);
    if ($blocking) {
        error_log('[portal-lead-sync] response ' . $code . ' ' . substr((string) $body, 0, 240));
    }
    return [
        'ok'   => $code >= 200 && $code < 300,
        'code' => $code,
        'body' => (string) $body,
    ];
}

/* ---------- Form plugin hooks ---------- */

function pls_should_handle($form_id_actual, $expected_plugin) {
    $s = pls_get_settings();
    if ($s['form_plugin'] !== $expected_plugin) {
        return false;
    }
    if (!empty($s['form_id']) && (string) $s['form_id'] !== (string) $form_id_actual) {
        return false;
    }
    return true;
}

// WPForms — fields keyed by ID; we mirror them under name where available.
add_action('wpforms_process_complete', function ($fields, $entry, $form_data, $entry_id) {
    if (!pls_should_handle($form_data['id'] ?? '', 'wpforms')) {
        return;
    }
    $flat = [];
    foreach ((array) $fields as $field) {
        if (!is_array($field)) {
            continue;
        }
        $key = $field['name'] ?? ($field['id'] ?? null);
        if ($key !== null) {
            $flat[(string) $key] = $field['value'] ?? '';
        }
        if (!empty($field['id'])) {
            $flat[(string) $field['id']] = $field['value'] ?? '';
        }
    }
    pls_post_lead(pls_build_payload($flat, pls_get_settings()), false);
}, 10, 4);

// Contact Form 7
add_action('wpcf7_mail_sent', function ($contact_form) {
    $form_id = method_exists($contact_form, 'id') ? $contact_form->id() : '';
    if (!pls_should_handle($form_id, 'cf7')) {
        return;
    }
    $submission = class_exists('WPCF7_Submission') ? WPCF7_Submission::get_instance() : null;
    if (!$submission) {
        return;
    }
    $data = $submission->get_posted_data();
    pls_post_lead(pls_build_payload((array) $data, pls_get_settings()), false);
});

// Elementor Pro
add_action('elementor_pro/forms/new_record', function ($record, $handler) {
    $form_id = $record->get_form_settings('id');
    if (!pls_should_handle($form_id, 'elementor')) {
        return;
    }
    $fields = $record->get('fields');
    $flat = [];
    foreach ((array) $fields as $id => $field) {
        $key = $field['id'] ?? $id;
        $flat[(string) $key] = $field['value'] ?? '';
    }
    pls_post_lead(pls_build_payload($flat, pls_get_settings()), false);
}, 10, 2);
