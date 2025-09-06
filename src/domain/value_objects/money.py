"""Money value object."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Union


@dataclass(frozen=True)
class Money:
    """Immutable money value object."""

    amount: Decimal
    currency: str = "EUR"

    def __post_init__(self):
        """Validate and normalize amount."""
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, 'amount', Decimal(str(self.amount)))

        # Round to 2 decimal places
        object.__setattr__(self, 'amount',
                          self.amount.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

        if self.amount < 0:
            raise ValueError("Money amount cannot be negative")

        if not self.currency or len(self.currency) != 3:
            raise ValueError("Currency must be a 3-letter code")

    def __add__(self, other: 'Money') -> 'Money':
        """Add two money values."""
        if not isinstance(other, Money):
            raise TypeError("Can only add Money to Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot add different currencies: {self.currency} and {other.currency}")

        return Money(self.amount + other.amount, self.currency)

    def __sub__(self, other: 'Money') -> 'Money':
        """Subtract two money values."""
        if not isinstance(other, Money):
            raise TypeError("Can only subtract Money from Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot subtract different currencies: {self.currency} and {other.currency}")

        result = self.amount - other.amount
        if result < 0:
            raise ValueError("Subtraction would result in negative money")

        return Money(result, self.currency)

    def __mul__(self, factor: Union[int, float, Decimal]) -> 'Money':
        """Multiply money by a factor."""
        if not isinstance(factor, (int, float, Decimal)):
            raise TypeError("Can only multiply Money by a number")

        return Money(self.amount * Decimal(str(factor)), self.currency)

    def __truediv__(self, divisor: Union[int, float, Decimal]) -> 'Money':
        """Divide money by a divisor."""
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Can only divide Money by a number")

        if divisor == 0:
            raise ValueError("Cannot divide by zero")

        return Money(self.amount / Decimal(str(divisor)), self.currency)

    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, Money):
            return False
        return self.amount == other.amount and self.currency == other.currency

    def __lt__(self, other: 'Money') -> bool:
        """Less than comparison."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")

        return self.amount < other.amount

    def __le__(self, other: 'Money') -> bool:
        """Less than or equal comparison."""
        return self == other or self < other

    def __gt__(self, other: 'Money') -> bool:
        """Greater than comparison."""
        if not isinstance(other, Money):
            raise TypeError("Can only compare Money with Money")
        if self.currency != other.currency:
            raise ValueError(f"Cannot compare different currencies: {self.currency} and {other.currency}")

        return self.amount > other.amount

    def __ge__(self, other: 'Money') -> bool:
        """Greater than or equal comparison."""
        return self == other or self > other

    def __str__(self) -> str:
        """String representation."""
        return f"{self.currency} {self.amount:,.2f}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Money(amount={self.amount}, currency='{self.currency}')"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'amount': str(self.amount),
            'currency': self.currency
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'Money':
        """Create from dictionary."""
        return cls(
            amount=Decimal(data['amount']),
            currency=data['currency']
        )

    @classmethod
    def zero(cls, currency: str = "EUR") -> 'Money':
        """Create zero money."""
        return cls(Decimal('0'), currency)
