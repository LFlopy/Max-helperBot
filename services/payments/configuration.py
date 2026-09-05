from config import PAYMENT_PROVIDER
from services.payments.fake import FakePaymentProvider
from services.payments.provider import PaymentProvider


class PaymentProviderUnavailableError(Exception):
    pass


_fake_provider = FakePaymentProvider()


def get_payment_provider() -> PaymentProvider:
    if PAYMENT_PROVIDER == "fake":
        return _fake_provider
    raise PaymentProviderUnavailableError("Payment provider is disabled")
