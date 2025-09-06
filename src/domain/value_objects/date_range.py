"""Date range value object."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Optional, Union


@dataclass(frozen=True)
class DateRange:
    """Immutable date range value object."""

    start: date
    end: date

    def __post_init__(self):
        """Validate date range."""
        # Convert datetime to date if needed
        if isinstance(self.start, datetime):
            object.__setattr__(self, 'start', self.start.date())
        if isinstance(self.end, datetime):
            object.__setattr__(self, 'end', self.end.date())

        if self.start > self.end:
            raise ValueError(f"Start date {self.start} must be before or equal to end date {self.end}")

    @property
    def days(self) -> int:
        """Number of days in the range (inclusive)."""
        return (self.end - self.start).days + 1

    @property
    def months(self) -> int:
        """Approximate number of months in the range."""
        return ((self.end.year - self.start.year) * 12 +
                self.end.month - self.start.month)

    @property
    def years(self) -> float:
        """Number of years in the range."""
        return self.days / 365.25

    def contains(self, date_value: Union[date, datetime]) -> bool:
        """Check if a date is within the range."""
        if isinstance(date_value, datetime):
            date_value = date_value.date()
        return self.start <= date_value <= self.end

    def overlaps(self, other: 'DateRange') -> bool:
        """Check if this range overlaps with another."""
        if not isinstance(other, DateRange):
            raise TypeError("Can only check overlap with another DateRange")

        return not (self.end < other.start or self.start > other.end)

    def intersection(self, other: 'DateRange') -> Optional['DateRange']:
        """Get the intersection of two date ranges."""
        if not isinstance(other, DateRange):
            raise TypeError("Can only intersect with another DateRange")

        if not self.overlaps(other):
            return None

        return DateRange(
            max(self.start, other.start),
            min(self.end, other.end)
        )

    def union(self, other: 'DateRange') -> Optional['DateRange']:
        """Get the union of two date ranges if they overlap or are adjacent."""
        if not isinstance(other, DateRange):
            raise TypeError("Can only union with another DateRange")

        # Check if ranges overlap or are adjacent
        if not self.overlaps(other) and (self.end + timedelta(days=1)) != other.start and (other.end + timedelta(days=1)) != self.start:
            return None

        return DateRange(
            min(self.start, other.start),
            max(self.end, other.end)
        )

    def extend(self, days: int) -> 'DateRange':
        """Extend the range by a number of days on both ends."""
        return DateRange(
            self.start - timedelta(days=days),
            self.end + timedelta(days=days)
        )

    def shift(self, days: int) -> 'DateRange':
        """Shift the entire range by a number of days."""
        delta = timedelta(days=days)
        return DateRange(
            self.start + delta,
            self.end + delta
        )

    def split_by_month(self) -> list['DateRange']:
        """Split the range into monthly ranges."""
        ranges = []
        current = self.start

        while current <= self.end:
            # Find the last day of the current month
            if current.month == 12:
                next_month = date(current.year + 1, 1, 1)
            else:
                next_month = date(current.year, current.month + 1, 1)

            month_end = next_month - timedelta(days=1)

            # Create range for this month
            ranges.append(DateRange(
                current,
                min(month_end, self.end)
            ))

            # Move to next month
            current = next_month
            if current > self.end:
                break

        return ranges

    def split_by_year(self) -> list['DateRange']:
        """Split the range into yearly ranges."""
        ranges = []
        current = self.start

        while current <= self.end:
            year_end = date(current.year, 12, 31)

            ranges.append(DateRange(
                current,
                min(year_end, self.end)
            ))

            current = date(current.year + 1, 1, 1)
            if current > self.end:
                break

        return ranges

    def iter_days(self) -> Iterator[date]:
        """Iterate over all days in the range."""
        current = self.start
        while current <= self.end:
            yield current
            current += timedelta(days=1)

    def __contains__(self, date_value: Union[date, datetime]) -> bool:
        """Check if a date is within the range (for 'in' operator)."""
        return self.contains(date_value)

    def __eq__(self, other) -> bool:
        """Check equality."""
        if not isinstance(other, DateRange):
            return False
        return self.start == other.start and self.end == other.end

    def __lt__(self, other: 'DateRange') -> bool:
        """Less than comparison (by start date, then end date)."""
        if not isinstance(other, DateRange):
            raise TypeError("Can only compare DateRange with DateRange")

        if self.start != other.start:
            return self.start < other.start
        return self.end < other.end

    def __str__(self) -> str:
        """String representation."""
        return f"{self.start.isoformat()} to {self.end.isoformat()}"

    def __repr__(self) -> str:
        """Developer representation."""
        return f"DateRange(start={self.start!r}, end={self.end!r})"

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'start': self.start.isoformat(),
            'end': self.end.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'DateRange':
        """Create from dictionary."""
        return cls(
            start=date.fromisoformat(data['start']),
            end=date.fromisoformat(data['end'])
        )

    @classmethod
    def from_month(cls, year: int, month: int) -> 'DateRange':
        """Create a range for a specific month."""
        start = date(year, month, 1)

        if month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, month + 1, 1) - timedelta(days=1)

        return cls(start, end)

    @classmethod
    def from_year(cls, year: int) -> 'DateRange':
        """Create a range for a specific year."""
        return cls(date(year, 1, 1), date(year, 12, 31))

    @classmethod
    def from_quarter(cls, year: int, quarter: int) -> 'DateRange':
        """Create a range for a specific quarter."""
        if quarter not in [1, 2, 3, 4]:
            raise ValueError(f"Quarter must be 1-4, got {quarter}")

        start_month = (quarter - 1) * 3 + 1
        end_month = quarter * 3

        start = date(year, start_month, 1)
        if end_month == 12:
            end = date(year, 12, 31)
        else:
            end = date(year, end_month + 1, 1) - timedelta(days=1)

        return cls(start, end)
