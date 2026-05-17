"""Wallet ledger. Every balance change goes through credit_wallet/debit_wallet
so WalletTransaction.balance_after stays in lockstep with Wallet.balance."""

from decimal import Decimal

from django.db import transaction

from apps.clients.models import Wallet, WalletTransaction


class InsufficientFunds(Exception):
    pass


def _get_or_create_wallet(client):
    wallet, _ = Wallet.objects.select_for_update().get_or_create(
        client=client, defaults={'balance': Decimal('0.00')},
    )
    return wallet


def get_balance(client):
    row = Wallet.objects.filter(client=client).values_list('balance', flat=True).first()
    return row if row is not None else Decimal('0.00')


@transaction.atomic
def credit_wallet(client, amount, tx_type, description='', reference=''):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError('amount must be positive')

    wallet = _get_or_create_wallet(client)
    wallet.balance = (wallet.balance or Decimal('0.00')) + amount
    wallet.save(update_fields=['balance'])

    return WalletTransaction.objects.create(
        wallet=wallet,
        amount=amount,
        tx_type=tx_type,
        description=description,
        reference=reference,
        balance_after=wallet.balance,
    )


@transaction.atomic
def debit_wallet(client, amount, tx_type, description='', reference=''):
    amount = Decimal(str(amount))
    if amount <= 0:
        raise ValueError('amount must be positive')

    wallet = _get_or_create_wallet(client)
    current = wallet.balance or Decimal('0.00')
    if current < amount:
        raise InsufficientFunds(
            f'Wallet balance {current} is less than debit amount {amount}.'
        )

    wallet.balance = current - amount
    wallet.save(update_fields=['balance'])

    return WalletTransaction.objects.create(
        wallet=wallet,
        amount=-amount,
        tx_type=tx_type,
        description=description,
        reference=reference,
        balance_after=wallet.balance,
    )
