/* LeadPortal — Stripe Elements integration for wallet top-ups.
 *
 * Loaded only when STRIPE_PUBLISHABLE_KEY is configured. Expects:
 *   window.PORTAL_STRIPE_KEY — publishable key
 *   #topupModal, #topupForm, #topupAmount, #payment-element, #topupSubmit, #topupMessage
 *   POST {csrf, amount} → /client/wallet/topup-intent/ returns {client_secret}
 */
(function () {
    'use strict';
    if (!window.Stripe || !window.PORTAL_STRIPE_KEY) return;

    const stripe = Stripe(window.PORTAL_STRIPE_KEY);
    let elements = null;
    let clientSecret = null;

    const modalEl = document.getElementById('topupModal');
    if (!modalEl) return;

    const amountInput = document.getElementById('topupAmount');
    const submitBtn = document.getElementById('topupSubmit');
    const messageEl = document.getElementById('topupMessage');

    async function ensureIntent() {
        const amount = parseFloat(amountInput.value || '0');
        if (!(amount > 0)) {
            messageEl.textContent = 'Enter an amount greater than 0.';
            return false;
        }
        const csrf = document.querySelector('#topupForm [name=csrfmiddlewaretoken]').value;
        const fd = new FormData();
        fd.set('amount', amount);
        const resp = await fetch('/client/wallet/topup-intent/', {
            method: 'POST',
            headers: { 'X-CSRFToken': csrf },
            body: fd,
        });
        const j = await resp.json();
        if (!resp.ok) {
            messageEl.textContent = j.error || 'Failed to create payment intent.';
            return false;
        }
        clientSecret = j.client_secret;
        elements = stripe.elements({ clientSecret });
        const paymentElement = elements.create('payment');
        const mount = document.getElementById('payment-element');
        mount.innerHTML = '';
        paymentElement.mount('#payment-element');
        return true;
    }

    amountInput.addEventListener('change', () => {
        clientSecret = null;
        document.getElementById('payment-element').innerHTML = '';
    });

    submitBtn.addEventListener('click', async () => {
        messageEl.textContent = '';
        if (!clientSecret) {
            const ok = await ensureIntent();
            if (!ok) return;
            messageEl.textContent = 'Card details ready — click Pay again to charge.';
            return;
        }
        submitBtn.disabled = true;
        const { error } = await stripe.confirmPayment({
            elements,
            confirmParams: { return_url: window.location.href },
            redirect: 'if_required',
        });
        submitBtn.disabled = false;
        if (error) {
            messageEl.textContent = error.message || 'Payment failed.';
            return;
        }
        window.showToast('Payment submitted — wallet credits when webhook confirms.', 'success');
        bootstrap.Modal.getInstance(modalEl).hide();
        setTimeout(() => window.location.reload(), 1500);
    });
})();
