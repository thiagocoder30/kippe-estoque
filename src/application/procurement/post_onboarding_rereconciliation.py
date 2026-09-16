"""
NF-001F — Post-Onboarding Deterministic Re-Reconciliation.

This boundary exists after an explicit human product-onboarding operation.

Its sole responsibility is to submit the same supplier-invoice evidence
back to the existing catalog reconciliation authority.

It deliberately does not:
- create or update products;
- invoke product onboarding;
- receive goods;
- mutate inventory;
- create batches;
- perform putaway;
- transform fiscal evidence.

All reconciliation semantics remain owned by the injected reconciliation
service.
"""


class PostOnboardingRereconciliationService:
    """
    Explicit application boundary for re-running catalog reconciliation
    after human catalog onboarding.
    """

    def __init__(
        self,
        reconciliation_service,
    ):
        self.reconciliation_service = (
            reconciliation_service
        )

    def execute(
        self,
        invoice,
    ):
        """
        Reconcile the exact invoice evidence supplied by the caller.

        The same object is delegated without normalization, copying or
        mutation by this orchestration boundary.
        """

        return self.reconciliation_service.reconcile(
            invoice
        )
