"""Percentage value object."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Union


@dataclass(frozen=True)
class Percentage:
    """Immutable percentage value object."""

    value: Decimal

    def __post_init__(self):
        """Validate and normalize value."""
        if not isinstance(self.value, Decimal):
            object.__setattr__(self, 'value', Decimal(str(self.value)))

        # Round to 4 decimal places (0.01% precision)
        object.__setattr__(self, 'value',
                          self.value.quantize(Decimal('0.0001'), rounding=ROUND_HALF_UP))

        if self.value < -100 or self.value > 1000:
            raise ValueError(f"Percentage value {self.value} is out of reasonable range [-100, 1000]")

    @classmethod
    def from_ratio(cls, ratio: Union[float, Decimal]) -> 'Percentage':
        """Create percentage from ratio (0.15 -> 15%)."""
        return cls(Decimal(str(ratio)) * 100)

    def to_ratio(self) -> Decimal:
        """Convert percentage to ratio (15% -> 0.15)."""
        return self.value / 100

    def __add__(self, other: 'Percentage') -> 'Percentage':
        """Add two percentages."""
        if not isinstance(other, Percentage):
            raise TypeError("Can only add Percentage to Percentage")

        return Percentage(self.value + other.value)

    def __sub__(self, other: 'Percentage') -> 'Percentage':
        """Subtract two percentages."""
        if not isinstance(other, Percentage):
            raise TypeError("Can only subtract Percentage from Percentage")

        return Percentage(self.value - other.value)

    def __mul__(self, factor: Union[int, float, Decimal]) -> 'Percentage':
        """Multiply percentage by a factor."""
        if not isinstance(factor, (int, float, Decimal)):
            raise TypeError("Can only multiply Percentage by a number")

        return Percentage(self.value * Decimal(str(factor)))

    def __truediv__(self, divisor: Union[int, float, Decimal]) -> 'Percentage':
        """Divide percentage by a divisor."""
        if not isinstance(divisor, (int, float, Decimal)):
            raise TypeError("Can only divide Percentage by a number")

        if divisor == 0:
            raise ValueError("Cannot divide by zero")

        return Percentage(self.value / Decimal(str(divisor)))

    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, Percentage):
            return False
        return self.value == other.value

    def __lt__(self, other: 'Percentage') -> bool:
        """Less than comparison."""
        if not isinstance(other, Percentage):
            raise TypeError("Can only compare Percentage with Percentage")

        return self.value < other.value

    def __le__(self, other: 'Percentage') -> bool:
        """Less than or equal comparison."""
        return self == other or self < other

    def __gt__(self, other: 'Percentage') -> bool:
        """Greater than comparison."""
        if not isinstance(other, Percentage):
            raise TypeError("Can only compare Percentage with Percentage")

        return self.value > other.value

    def __ge__(self, other: 'Percentage') -> bool:
        """Greater than or equal comparison."""
        return self == other or self > other

    def __neg__(self) -> 'Percentage':
        """Negate percentage."""
        return Percentage(-self.value)

    def __abs__(self) -> 'Percentage':
        """Absolute value of percentage."""
        return Percentage(abs(self.value))

    def __str__(self) -> str:
        """String representation."""
        return f"{self.value:.2f}%"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"Percentage(value={self.value})"

    def apply_to(self, amount: Union[int, float, Decimal]) -> Decimal:
        """Apply percentage to an amount."""
        return Decimal(str(amount)) * self.to_ratio()

    def is_positive(self) -> bool:
        """Check if percentage is positive."""
        return self.value > 0

    def is_negative(self) -> bool:
        """Check if percentage is negative."""
        return self.value < 0

    def is_zero(self) -> bool:
        """Check if percentage is zero."""
        return self.value == 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {'value': str(self.value)}

    @classmethod
    def from_dict(cls, data: dict) -> 'Percentage':
        """Create from dictionary."""
        return cls(value=Decimal(data['value']))

    @classmethod
    def zero(cls) -> 'Percentage':
        """Create zero percentage."""
        return cls(Decimal('0'))
