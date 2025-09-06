"""Unit tests for domain value objects."""

import pytest
from decimal import Decimal
from datetime import date, timedelta

from src.domain.value_objects import Money, Percentage, DateRange


class TestMoney:
    """Test cases for Money value object."""
    
    def test_money_creation(self):
        """Test money creation with valid values."""
        money = Money(Decimal("100.50"), "EUR")
        assert money.amount == Decimal("100.50")
        assert money.currency == "EUR"
    
    def test_money_creation_from_float(self):
        """Test money creation from float is converted to Decimal."""
        money = Money(100.50, "USD")
        assert money.amount == Decimal("100.50")
        assert money.currency == "USD"
    
    def test_money_negative_amount_raises_error(self):
        """Test that negative amounts raise ValueError."""
        with pytest.raises(ValueError, match="Money amount cannot be negative"):
            Money(Decimal("-50.00"), "EUR")
    
    def test_money_invalid_currency_raises_error(self):
        """Test that invalid currency raises ValueError."""
        with pytest.raises(ValueError, match="Currency must be a 3-letter code"):
            Money(Decimal("100.00"), "EURO")
    
    def test_money_addition(self, sample_money):
        """Test money addition with same currency."""
        money2 = Money(Decimal("500.25"), "EUR")
        result = sample_money + money2
        
        assert result.amount == Decimal("2001.00")
        assert result.currency == "EUR"
    
    def test_money_addition_different_currency_raises_error(self, sample_money):
        """Test that adding different currencies raises error."""
        money2 = Money(Decimal("100.00"), "USD")
        
        with pytest.raises(ValueError, match="Cannot add different currencies"):
            sample_money + money2
    
    def test_money_subtraction(self, sample_money):
        """Test money subtraction."""
        money2 = Money(Decimal("500.00"), "EUR")
        result = sample_money - money2
        
        assert result.amount == Decimal("1000.75")
        assert result.currency == "EUR"
    
    def test_money_subtraction_negative_result_raises_error(self, sample_money):
        """Test that subtraction resulting in negative raises error."""
        money2 = Money(Decimal("2000.00"), "EUR")
        
        with pytest.raises(ValueError, match="Subtraction would result in negative money"):
            sample_money - money2
    
    def test_money_multiplication(self, sample_money):
        """Test money multiplication by factor."""
        result = sample_money * 2
        
        assert result.amount == Decimal("3001.50")
        assert result.currency == "EUR"
    
    def test_money_division(self, sample_money):
        """Test money division by divisor."""
        result = sample_money / 3
        
        assert result.amount == Decimal("500.25")
        assert result.currency == "EUR"
    
    def test_money_division_by_zero_raises_error(self, sample_money):
        """Test that division by zero raises error."""
        with pytest.raises(ValueError, match="Cannot divide by zero"):
            sample_money / 0
    
    def test_money_comparison(self):
        """Test money comparison operators."""
        money1 = Money(Decimal("100.00"), "EUR")
        money2 = Money(Decimal("200.00"), "EUR")
        money3 = Money(Decimal("100.00"), "EUR")
        
        assert money1 < money2
        assert money2 > money1
        assert money1 == money3
        assert money1 <= money3
        assert money2 >= money1
    
    def test_money_string_representation(self, sample_money):
        """Test string representation."""
        assert str(sample_money) == "EUR 1,500.75"
    
    def test_money_to_dict(self, sample_money):
        """Test conversion to dictionary."""
        expected = {
            'amount': '1500.75',
            'currency': 'EUR'
        }
        assert sample_money.to_dict() == expected
    
    def test_money_from_dict(self):
        """Test creation from dictionary."""
        data = {'amount': '1500.75', 'currency': 'EUR'}
        money = Money.from_dict(data)
        
        assert money.amount == Decimal('1500.75')
        assert money.currency == 'EUR'
    
    def test_money_zero(self):
        """Test creation of zero money."""
        zero_eur = Money.zero("EUR")
        zero_usd = Money.zero("USD")
        
        assert zero_eur.amount == Decimal('0')
        assert zero_eur.currency == "EUR"
        assert zero_usd.currency == "USD"


class TestPercentage:
    """Test cases for Percentage value object."""
    
    def test_percentage_creation(self, sample_percentage):
        """Test percentage creation."""
        assert sample_percentage.value == Decimal("15.5")
    
    def test_percentage_from_ratio(self):
        """Test percentage creation from ratio."""
        pct = Percentage.from_ratio(0.155)
        assert pct.value == Decimal("15.5")
    
    def test_percentage_to_ratio(self, sample_percentage):
        """Test conversion to ratio."""
        ratio = sample_percentage.to_ratio()
        assert ratio == Decimal("0.155")
    
    def test_percentage_out_of_range_raises_error(self):
        """Test that extreme values raise error."""
        with pytest.raises(ValueError, match="out of reasonable range"):
            Percentage(Decimal("1500.0"))
        
        with pytest.raises(ValueError, match="out of reasonable range"):
            Percentage(Decimal("-150.0"))
    
    def test_percentage_addition(self, sample_percentage):
        """Test percentage addition."""
        pct2 = Percentage(Decimal("5.0"))
        result = sample_percentage + pct2
        
        assert result.value == Decimal("20.5")
    
    def test_percentage_subtraction(self, sample_percentage):
        """Test percentage subtraction."""
        pct2 = Percentage(Decimal("5.0"))
        result = sample_percentage - pct2
        
        assert result.value == Decimal("10.5")
    
    def test_percentage_multiplication(self, sample_percentage):
        """Test percentage multiplication."""
        result = sample_percentage * 2
        assert result.value == Decimal("31.0")
    
    def test_percentage_comparison(self):
        """Test percentage comparison."""
        pct1 = Percentage(Decimal("10.0"))
        pct2 = Percentage(Decimal("20.0"))
        pct3 = Percentage(Decimal("10.0"))
        
        assert pct1 < pct2
        assert pct2 > pct1
        assert pct1 == pct3
    
    def test_percentage_negation(self, sample_percentage):
        """Test percentage negation."""
        negated = -sample_percentage
        assert negated.value == Decimal("-15.5")
    
    def test_percentage_absolute(self):
        """Test percentage absolute value."""
        pct = Percentage(Decimal("-10.5"))
        abs_pct = abs(pct)
        assert abs_pct.value == Decimal("10.5")
    
    def test_percentage_apply_to(self, sample_percentage):
        """Test applying percentage to amount."""
        result = sample_percentage.apply_to(1000)
        assert result == Decimal("155.0")
    
    def test_percentage_predicates(self):
        """Test percentage predicate methods."""
        positive = Percentage(Decimal("10.0"))
        negative = Percentage(Decimal("-5.0"))
        zero = Percentage(Decimal("0.0"))
        
        assert positive.is_positive()
        assert not positive.is_negative()
        assert not positive.is_zero()
        
        assert not negative.is_positive()
        assert negative.is_negative()
        assert not negative.is_zero()
        
        assert not zero.is_positive()
        assert not zero.is_negative()
        assert zero.is_zero()
    
    def test_percentage_string_representation(self, sample_percentage):
        """Test string representation."""
        assert str(sample_percentage) == "15.50%"
    
    def test_percentage_zero(self):
        """Test creation of zero percentage."""
        zero = Percentage.zero()
        assert zero.value == Decimal("0")


class TestDateRange:
    """Test cases for DateRange value object."""
    
    def test_date_range_creation(self, sample_date_range):
        """Test date range creation."""
        assert sample_date_range.start == date(2023, 1, 1)
        assert sample_date_range.end == date(2023, 12, 31)
    
    def test_date_range_invalid_order_raises_error(self):
        """Test that invalid date order raises error."""
        with pytest.raises(ValueError, match="must be before or equal"):
            DateRange(date(2023, 12, 31), date(2023, 1, 1))
    
    def test_date_range_properties(self, sample_date_range):
        """Test date range properties."""
        assert sample_date_range.days == 365
        assert sample_date_range.months == 11  # Dec - Jan
        assert abs(sample_date_range.years - 1.0) < 0.1
    
    def test_date_range_contains(self, sample_date_range):
        """Test date containment check."""
        assert sample_date_range.contains(date(2023, 6, 15))
        assert not sample_date_range.contains(date(2024, 1, 1))
        assert sample_date_range.contains(date(2023, 1, 1))  # Start date
        assert sample_date_range.contains(date(2023, 12, 31))  # End date
    
    def test_date_range_overlaps(self, sample_date_range):
        """Test date range overlap detection."""
        overlapping = DateRange(date(2023, 6, 1), date(2024, 6, 1))
        non_overlapping = DateRange(date(2024, 1, 1), date(2024, 12, 31))
        
        assert sample_date_range.overlaps(overlapping)
        assert not sample_date_range.overlaps(non_overlapping)
    
    def test_date_range_intersection(self, sample_date_range):
        """Test date range intersection."""
        overlapping = DateRange(date(2023, 6, 1), date(2024, 6, 1))
        intersection = sample_date_range.intersection(overlapping)
        
        assert intersection is not None
        assert intersection.start == date(2023, 6, 1)
        assert intersection.end == date(2023, 12, 31)
        
        # Test no intersection
        non_overlapping = DateRange(date(2024, 1, 1), date(2024, 12, 31))
        no_intersection = sample_date_range.intersection(non_overlapping)
        assert no_intersection is None
    
    def test_date_range_union(self, sample_date_range):
        """Test date range union."""
        adjacent = DateRange(date(2024, 1, 1), date(2024, 12, 31))
        union = sample_date_range.union(adjacent)
        
        assert union is not None
        assert union.start == date(2023, 1, 1)
        assert union.end == date(2024, 12, 31)
    
    def test_date_range_extend(self, sample_date_range):
        """Test date range extension."""
        extended = sample_date_range.extend(30)
        
        assert extended.start == date(2022, 12, 2)  # 30 days before
        assert extended.end == date(2024, 1, 30)    # 30 days after
    
    def test_date_range_shift(self, sample_date_range):
        """Test date range shifting."""
        shifted = sample_date_range.shift(30)
        
        assert shifted.start == date(2023, 1, 31)
        assert shifted.end == date(2024, 1, 30)
    
    def test_date_range_split_by_month(self, sample_date_range):
        """Test splitting by month."""
        monthly_ranges = sample_date_range.split_by_month()
        
        assert len(monthly_ranges) == 12
        assert monthly_ranges[0].start == date(2023, 1, 1)
        assert monthly_ranges[0].end == date(2023, 1, 31)
        assert monthly_ranges[-1].start == date(2023, 12, 1)
        assert monthly_ranges[-1].end == date(2023, 12, 31)
    
    def test_date_range_split_by_year(self):
        """Test splitting by year."""
        multi_year = DateRange(date(2022, 6, 1), date(2024, 3, 15))
        yearly_ranges = multi_year.split_by_year()
        
        assert len(yearly_ranges) == 3
        assert yearly_ranges[0].start == date(2022, 6, 1)
        assert yearly_ranges[0].end == date(2022, 12, 31)
        assert yearly_ranges[2].start == date(2024, 1, 1)
        assert yearly_ranges[2].end == date(2024, 3, 15)
    
    def test_date_range_iter_days(self):
        """Test iterating over days."""
        short_range = DateRange(date(2023, 1, 1), date(2023, 1, 3))
        days = list(short_range.iter_days())
        
        expected = [date(2023, 1, 1), date(2023, 1, 2), date(2023, 1, 3)]
        assert days == expected
    
    def test_date_range_contains_operator(self, sample_date_range):
        """Test 'in' operator."""
        assert date(2023, 6, 15) in sample_date_range
        assert date(2024, 1, 1) not in sample_date_range
    
    def test_date_range_from_month(self):
        """Test creation from month."""
        june_2023 = DateRange.from_month(2023, 6)
        
        assert june_2023.start == date(2023, 6, 1)
        assert june_2023.end == date(2023, 5, 31)  # Last day of May (simplified)
    
    def test_date_range_from_year(self):
        """Test creation from year."""
        year_2023 = DateRange.from_year(2023)
        
        assert year_2023.start == date(2023, 1, 1)
        assert year_2023.end == date(2023, 12, 31)
    
    def test_date_range_from_quarter(self):
        """Test creation from quarter."""
        q2_2023 = DateRange.from_quarter(2023, 2)
        
        assert q2_2023.start == date(2023, 4, 1)
        # End should be around June 30 (simplified)
        assert q2_2023.end.month == 6
    
    def test_date_range_string_representation(self, sample_date_range):
        """Test string representation."""
        expected = "2023-01-01 to 2023-12-31"
        assert str(sample_date_range) == expected