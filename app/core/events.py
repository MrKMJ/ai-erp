"""Minimal in-process domain event bus.

Even in a modular monolith the ERP publishes domain events (InvoiceCreated,
InventoryChanged, ...). Subscribers (accounting, AI monitors, notifications) react.
Swap this for Redis Streams / Kafka when extracting services.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger("erp.events")


@dataclass(slots=True)
class DomainEvent:
    name: str
    tenant_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))


Handler = Callable[[DomainEvent], None]


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Handler]] = defaultdict(list)

    def subscribe(self, event_name: str, handler: Handler) -> None:
        self._handlers[event_name].append(handler)

    def on(self, event_name: str) -> Callable[[Handler], Handler]:
        def deco(fn: Handler) -> Handler:
            self.subscribe(event_name, fn)
            return fn

        return deco

    def publish(self, event: DomainEvent) -> None:
        logger.info("event %s tenant=%s payload=%s", event.name, event.tenant_id, event.payload)
        for handler in list(self._handlers.get(event.name, [])):
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - a bad subscriber must not break the transaction
                logger.exception("event handler failed for %s", event.name)


bus = EventBus()
