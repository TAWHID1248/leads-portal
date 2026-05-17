(function () {
    'use strict';

    function getCookie(name) {
        const match = document.cookie.match(new RegExp('(?:^|; )' + name.replace(/([.$?*|{}()\[\]\\\/+^])/g, '\\$1') + '=([^;]*)'));
        return match ? decodeURIComponent(match[1]) : null;
    }

    // ---------- HTMX CSRF ----------
    // base.html already sets hx-headers on <body>, but cover the case where a fragment
    // is rendered without that wrapper (e.g. an htmx response that triggers another request).
    document.addEventListener('htmx:configRequest', function (evt) {
        const token = getCookie('csrftoken') ||
            (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value;
        if (token && !evt.detail.headers['X-CSRFToken']) {
            evt.detail.headers['X-CSRFToken'] = token;
        }
    });

    // ---------- Toasts ----------
    const TOAST_LEVELS = {
        success: { bg: 'text-bg-success', icon: 'bi-check-circle-fill' },
        info:    { bg: 'text-bg-primary', icon: 'bi-info-circle-fill' },
        warning: { bg: 'text-bg-warning', icon: 'bi-exclamation-triangle-fill' },
        error:   { bg: 'text-bg-danger',  icon: 'bi-x-octagon-fill' },
        danger:  { bg: 'text-bg-danger',  icon: 'bi-x-octagon-fill' },
        debug:   { bg: 'text-bg-secondary', icon: 'bi-bug-fill' },
    };

    window.showToast = function (message, level) {
        const cfg = TOAST_LEVELS[level] || TOAST_LEVELS.success;
        const container = document.getElementById('toastContainer');
        if (!container || !message) return;

        const el = document.createElement('div');
        el.className = 'toast align-items-center border-0 ' + cfg.bg;
        el.setAttribute('role', 'alert');
        el.setAttribute('aria-live', 'assertive');
        el.setAttribute('aria-atomic', 'true');
        el.innerHTML =
            '<div class="d-flex">' +
                '<div class="toast-body">' +
                    '<i class="bi ' + cfg.icon + ' me-2"></i>' +
                    String(message) +
                '</div>' +
                '<button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>' +
            '</div>';
        container.appendChild(el);

        if (window.bootstrap && window.bootstrap.Toast) {
            const t = new bootstrap.Toast(el, { delay: 5000 });
            t.show();
            el.addEventListener('hidden.bs.toast', () => el.remove());
        } else {
            setTimeout(() => el.remove(), 5000);
        }
    };

    // HX-Trigger: {"showToast": {"message": "...", "level": "success"}}
    document.body.addEventListener('showToast', function (evt) {
        const d = evt.detail || {};
        window.showToast(d.message || d.value, d.level || 'success');
    });

    // ---------- Copy to clipboard ----------
    window.copyToClipboard = function (text, successMessage) {
        const done = () => window.showToast(successMessage || 'Copied to clipboard', 'success');
        const fail = () => window.showToast('Unable to copy', 'error');

        if (navigator.clipboard && window.isSecureContext) {
            navigator.clipboard.writeText(text).then(done, fail);
            return;
        }
        try {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.opacity = '0';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
            done();
        } catch (e) {
            fail();
        }
    };

    // ---------- Sidebar toggle (mobile) ----------
    document.addEventListener('click', function (evt) {
        const toggle = evt.target.closest('#sidebarToggle');
        if (toggle) {
            const sidebar = document.getElementById('portalSidebar');
            if (sidebar) sidebar.classList.toggle('show');
            return;
        }
        // Click outside to close on mobile
        if (window.innerWidth < 992) {
            const sidebar = document.getElementById('portalSidebar');
            if (sidebar && sidebar.classList.contains('show') && !evt.target.closest('#portalSidebar')) {
                sidebar.classList.remove('show');
            }
        }
    });

    // ---------- [data-copy] buttons ----------
    document.addEventListener('click', function (evt) {
        const btn = evt.target.closest('[data-copy]');
        if (!btn) return;
        evt.preventDefault();
        window.copyToClipboard(btn.getAttribute('data-copy'));
    });

    // ---------- Leads page module: bulk select + drawer ----------
    const selected = new Set();

    function csrfToken() {
        return getCookie('csrftoken') ||
            (document.querySelector('[name=csrfmiddlewaretoken]') || {}).value || '';
    }

    function refreshBulkBar() {
        const bar = document.getElementById('bulkActionsBar');
        if (!bar) return;
        const count = document.getElementById('bulkCount');
        if (count) count.textContent = String(selected.size);
        bar.classList.toggle('d-none', selected.size === 0);
        bar.classList.toggle('d-flex', selected.size > 0);
    }

    function restoreCheckboxes() {
        document.querySelectorAll('.lead-row-check').forEach((cb) => {
            cb.checked = selected.has(cb.value);
        });
        const all = document.getElementById('selectAllRows');
        if (all) {
            const rows = Array.from(document.querySelectorAll('.lead-row-check'));
            all.checked = rows.length > 0 && rows.every((cb) => cb.checked);
        }
    }

    function init() {
        // Row checkboxes
        document.addEventListener('change', function (evt) {
            const cb = evt.target.closest('.lead-row-check');
            if (cb) {
                if (cb.checked) selected.add(cb.value);
                else selected.delete(cb.value);
                refreshBulkBar();
                restoreCheckboxes();
                return;
            }
            const all = evt.target.closest('#selectAllRows');
            if (all) {
                document.querySelectorAll('.lead-row-check').forEach((row) => {
                    row.checked = all.checked;
                    if (all.checked) selected.add(row.value);
                    else selected.delete(row.value);
                });
                refreshBulkBar();
            }
        });

        // After HTMX swaps the table, restore the checkbox state.
        document.body.addEventListener('htmx:afterSwap', function (evt) {
            if (evt.target && evt.target.id === 'leads-table') {
                restoreCheckboxes();
                refreshBulkBar();
            }
        });

        // Open the assign modal pre-filled with the row's lead id.
        const assignModal = document.getElementById('assignModal');
        if (assignModal) {
            assignModal.addEventListener('show.bs.modal', function (evt) {
                const trigger = evt.relatedTarget;
                const leadId = trigger && trigger.getAttribute('data-lead-id');
                const form = document.getElementById('assignForm');
                const leadInput = document.getElementById('assignLeadId');
                const bulkBox = document.getElementById('assignBulkIds');
                const bulkCount = document.getElementById('assignBulkCount');
                bulkBox.innerHTML = '';
                if (leadId) {
                    leadInput.value = leadId;
                    form.setAttribute('action', '/super/leads/' + leadId + '/assign/');
                    form.setAttribute('hx-post', '/super/leads/' + leadId + '/assign/');
                    if (bulkCount) bulkCount.textContent = '';
                } else if (selected.size > 0) {
                    leadInput.value = '';
                    form.setAttribute('action', '/super/leads/bulk-assign/');
                    form.setAttribute('hx-post', '/super/leads/bulk-assign/');
                    selected.forEach((id) => {
                        const i = document.createElement('input');
                        i.type = 'hidden'; i.name = 'ids'; i.value = id;
                        bulkBox.appendChild(i);
                    });
                    if (bulkCount) bulkCount.textContent = ' (' + selected.size + ' leads)';
                }
                if (window.htmx) window.htmx.process(form);
            });
        }

        // Bulk export — submits a hidden form so the browser triggers a file download.
        const exportBtn = document.getElementById('bulkExportBtn');
        if (exportBtn) {
            exportBtn.addEventListener('click', function () {
                if (selected.size === 0) return;
                const form = document.createElement('form');
                form.method = 'POST'; form.action = '/super/leads/bulk-export/';
                form.innerHTML = '<input type="hidden" name="csrfmiddlewaretoken" value="' + csrfToken() + '">';
                selected.forEach((id) => {
                    form.innerHTML += '<input type="hidden" name="ids" value="' + id + '">';
                });
                document.body.appendChild(form);
                form.submit();
                form.remove();
            });
        }

        const rejectBtn = document.getElementById('bulkRejectBtn');
        if (rejectBtn) {
            rejectBtn.addEventListener('click', async function () {
                if (selected.size === 0) return;
                if (!confirm('Reject ' + selected.size + ' lead(s)?')) return;
                const body = new FormData();
                selected.forEach((id) => body.append('ids', id));
                const resp = await fetch('/super/leads/bulk-reject/', {
                    method: 'POST',
                    headers: { 'X-CSRFToken': csrfToken() },
                    body,
                });
                if (resp.ok) {
                    const j = await resp.json();
                    window.showToast(j.count + ' lead(s) rejected', 'success');
                    selected.clear(); refreshBulkBar();
                    if (window.htmx) htmx.ajax('GET', window.location.pathname + window.location.search, '#leads-table');
                } else {
                    window.showToast('Bulk reject failed', 'error');
                }
            });
        }

        const clearBtn = document.getElementById('bulkClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', function () {
                selected.clear();
                restoreCheckboxes();
                refreshBulkBar();
            });
        }

        restoreCheckboxes();
        refreshBulkBar();
    }

    function openDrawer() {
        const el = document.getElementById('leadDrawer');
        if (!el || !window.bootstrap) return;
        const inst = window.bootstrap.Offcanvas.getOrCreateInstance(el);
        inst.show();
    }

    function handleAssignResponse(event) {
        const xhr = event && event.detail && event.detail.xhr;
        if (!xhr) return;
        const modalEl = document.getElementById('assignModal');
        if (xhr.status >= 200 && xhr.status < 300) {
            // For bulk JSON response, show toast and reload table.
            const ct = xhr.getResponseHeader('Content-Type') || '';
            if (ct.indexOf('application/json') >= 0) {
                try {
                    const j = JSON.parse(xhr.responseText);
                    window.showToast(j.created + ' lead(s) assigned (of ' + j.total + ')', 'success');
                    if (window.htmx) htmx.ajax('GET', window.location.pathname + window.location.search, '#leads-table');
                    selected.clear();
                } catch (e) {}
            }
            if (modalEl) window.bootstrap.Modal.getInstance(modalEl).hide();
        } else {
            window.showToast('Assignment failed: ' + (xhr.responseText || xhr.status), 'error');
        }
    }

    window.portalLeads = { init, openDrawer, handleAssignResponse };
})();
