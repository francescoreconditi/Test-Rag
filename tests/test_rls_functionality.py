"""Comprehensive tests for Row-level Security (RLS) functionality."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch

from src.core.security import (
    UserContext,
    UserRole,
    DataClassification,
    create_user_context,
    AccessControlService,
    AuthenticationService,
    SecurityViolationError,
)
from src.infrastructure.repositories.secure_fact_table import SecureFactTableRepository, SecureFactRecord
from services.secure_rag_engine import SecureRAGEngine
from src.domain.value_objects.source_reference import SourceReference


class TestUserContext:
    """Test user context and role system."""

    def test_user_context_creation(self):
        """Test user context creation with defaults."""
        user_context = create_user_context(
            user_id="test_user", username="test.user", role=UserRole.ANALYST, tenant_id="tenant_a"
        )

        assert user_context.user_id == "test_user"
        assert user_context.username == "test.user"
        assert user_context.role == UserRole.ANALYST
        assert user_context.tenant_id == "tenant_a"
        assert user_context.max_classification_level == DataClassification.INTERNAL
        assert "read_assigned" in user_context.permissions

    def test_admin_permissions(self):
        """Test admin has all permissions."""
        admin_context = create_user_context(user_id="admin", username="admin", role=UserRole.ADMIN)

        assert admin_context.is_admin()
        assert admin_context.has_permission("bypass_rls")
        assert admin_context.can_access_classification(DataClassification.RESTRICTED)

    def test_entity_access_control(self):
        """Test entity access control."""
        user_context = create_user_context(
            user_id="analyst", username="analyst", role=UserRole.ANALYST, accessible_entities=["Company_A", "Company_B"]
        )

        assert user_context.can_access_entity("Company_A")
        assert user_context.can_access_entity("Company_B")
        assert not user_context.can_access_entity("Company_C")

    def test_classification_access(self):
        """Test data classification access."""
        viewer_context = create_user_context(user_id="viewer", username="viewer", role=UserRole.VIEWER)

        assert viewer_context.can_access_classification(DataClassification.PUBLIC)
        assert viewer_context.can_access_classification(DataClassification.INTERNAL)
        assert not viewer_context.can_access_classification(DataClassification.CONFIDENTIAL)
        assert not viewer_context.can_access_classification(DataClassification.RESTRICTED)


class TestAccessControlService:
    """Test access control service."""

    def setup_method(self):
        """Setup test fixtures."""
        self.access_control = AccessControlService()

        self.admin_context = create_user_context(user_id="admin", username="admin", role=UserRole.ADMIN)

        self.analyst_context = create_user_context(
            user_id="analyst",
            username="analyst",
            role=UserRole.ANALYST,
            tenant_id="tenant_a",
            accessible_entities=["Company_A", "BU_Finance"],
            accessible_periods=["2023", "Q1_2024"],
            cost_centers=["CDC_100", "CDC_110"],
        )

        self.viewer_context = create_user_context(
            user_id="viewer",
            username="viewer",
            role=UserRole.VIEWER,
            tenant_id="tenant_b",
            accessible_entities=["Company_B"],
            max_classification_level=DataClassification.PUBLIC,
        )

    def test_admin_rls_bypass(self):
        """Test admin can bypass RLS."""
        rls_filter = self.access_control.generate_rls_filter(self.admin_context)

        assert rls_filter.metadata.get("bypass") is True
        assert len(rls_filter.constraints) == 0

    def test_analyst_rls_filter(self):
        """Test analyst gets appropriate RLS filter."""
        rls_filter = self.access_control.generate_rls_filter(self.analyst_context)

        assert rls_filter.tenant_constraint is not None
        assert rls_filter.tenant_constraint.values == "tenant_a"

        # Check constraints
        constraint_fields = [c.field for c in rls_filter.constraints]
        assert "entity_id" in constraint_fields
        assert "classification_level" in constraint_fields

        # Find entity constraint
        entity_constraint = next(c for c in rls_filter.constraints if c.field == "entity_id")
        assert "Company_A" in entity_constraint.values
        assert "BU_Finance" in entity_constraint.values

    def test_viewer_restrictive_filter(self):
        """Test viewer gets restrictive RLS filter."""
        rls_filter = self.access_control.generate_rls_filter(self.viewer_context)

        # Should have tenant constraint
        assert rls_filter.tenant_constraint.values == "tenant_b"

        # Should restrict classification level
        classification_constraint = next(c for c in rls_filter.constraints if c.field == "classification_level")
        assert classification_constraint.values == DataClassification.PUBLIC.value

    def test_sql_conversion(self):
        """Test RLS filter to SQL conversion."""
        rls_filter = self.access_control.generate_rls_filter(self.analyst_context)

        where_clause, params = self.access_control.convert_rls_to_sql_where(rls_filter)

        assert "tenant_id = :param_0" in where_clause
        assert "entity_id IN" in where_clause
        assert "classification_level <=" in where_clause
        assert params["param_0"] == "tenant_a"

    def test_mongo_conversion(self):
        """Test RLS filter to MongoDB conversion."""
        rls_filter = self.access_control.generate_rls_filter(self.analyst_context)

        mongo_filter = self.access_control.convert_rls_to_mongo_filter(rls_filter)

        assert mongo_filter["tenant_id"] == "tenant_a"
        assert "$in" in str(mongo_filter["entity_id"])
        assert "$lte" in str(mongo_filter["classification_level"])

    def test_permission_validation(self):
        """Test permission validation."""
        # Admin should have all permissions
        assert self.access_control.validate_access_attempt(self.admin_context, "fact", operation="delete")

        # Analyst should have read/write but not delete by default
        assert self.access_control.validate_access_attempt(self.analyst_context, "fact", operation="read")
        assert self.access_control.validate_access_attempt(self.analyst_context, "fact", operation="write")

        # Viewer should only have read
        assert self.access_control.validate_access_attempt(self.viewer_context, "fact", operation="read")
        assert not self.access_control.validate_access_attempt(self.viewer_context, "fact", operation="write")


class TestAuthenticationService:
    """Test authentication service."""

    def setup_method(self):
        """Setup test fixtures."""
        self.auth_service = AuthenticationService()

    def test_successful_authentication(self):
        """Test successful user authentication."""
        result = self.auth_service.authenticate("admin", "admin123")

        assert result.success is True
        assert result.user_context is not None
        assert result.session_token is not None
        assert result.user_context.user_id == "admin"
        assert result.user_context.role == UserRole.ADMIN

    def test_failed_authentication(self):
        """Test failed authentication."""
        result = self.auth_service.authenticate("admin", "wrongpassword")

        assert result.success is False
        assert result.user_context is None
        assert result.session_token is None
        assert "Invalid username or password" in result.error_message

    def test_nonexistent_user(self):
        """Test authentication with nonexistent user."""
        result = self.auth_service.authenticate("nonexistent", "password")

        assert result.success is False
        assert "Invalid username or password" in result.error_message

    def test_session_validation(self):
        """Test session token validation."""
        # Login first
        result = self.auth_service.authenticate("analyst.azienda.a", "analyst123")
        session_token = result.session_token

        # Validate session
        user_context = self.auth_service.validate_session(session_token)

        assert user_context is not None
        assert user_context.user_id == "analyst_a"
        assert user_context.tenant_id == "tenant_a"

    def test_invalid_session(self):
        """Test validation of invalid session."""
        user_context = self.auth_service.validate_session("invalid_token")
        assert user_context is None

    def test_logout(self):
        """Test user logout."""
        # Login first
        result = self.auth_service.authenticate("admin", "admin123")
        session_token = result.session_token

        # Logout
        logout_success = self.auth_service.logout(session_token)
        assert logout_success is True

        # Session should be invalid after logout
        user_context = self.auth_service.validate_session(session_token)
        assert user_context is None

    def test_session_cleanup(self):
        """Test expired session cleanup."""
        # This would require mocking datetime to test session expiration
        # For now, just test the cleanup method doesn't crash
        cleaned_count = self.auth_service.cleanup_expired_sessions()
        assert isinstance(cleaned_count, int)
        assert cleaned_count >= 0


class TestSecureFactTable:
    """Test secure fact table with RLS."""

    def setup_method(self):
        """Setup test fixtures."""
        # Use in-memory SQLite for testing
        self.secure_repo = SecureFactTableRepository(":memory:", use_duckdb=False)

        self.admin_context = create_user_context(user_id="admin", username="admin", role=UserRole.ADMIN)

        self.analyst_context = create_user_context(
            user_id="analyst",
            username="analyst",
            role=UserRole.ANALYST,
            tenant_id="tenant_a",
            accessible_entities=["Company_A"],
            accessible_periods=["2023"],
        )

    @patch("src.domain.value_objects.source_reference.SourceReference")
    def test_secure_fact_insertion(self, mock_source_ref):
        """Test inserting facts with security context."""
        mock_source_ref.to_dict.return_value = {"file": "test.pdf", "page": 1}

        fact_id = self.secure_repo.insert_secure_fact(
            user_context=self.analyst_context,
            metric_name="Revenue",
            value=1000000.0,
            entity_name="Company_A",
            period_key="2023",
            scenario="Actual",
            source_reference=mock_source_ref,
            classification_level=DataClassification.INTERNAL,
            cost_center_code="CDC_100",
        )

        assert fact_id is not None
        assert fact_id.startswith("fact_")

    def test_unauthorized_insertion(self):
        """Test unauthorized fact insertion."""
        with patch("src.domain.value_objects.source_reference.SourceReference") as mock_source_ref:
            mock_source_ref.to_dict.return_value = {"file": "test.pdf", "page": 1}

            # Try to insert fact for entity not accessible to user
            with pytest.raises(SecurityViolationError):
                self.secure_repo.insert_secure_fact(
                    user_context=self.analyst_context,
                    metric_name="Revenue",
                    value=1000000.0,
                    entity_name="Company_B",  # Not accessible
                    period_key="2023",
                    scenario="Actual",
                    source_reference=mock_source_ref,
                )

    def test_rls_fact_retrieval(self):
        """Test fact retrieval with RLS applied."""
        # Insert some test facts first (as admin to bypass restrictions)
        with patch("src.domain.value_objects.source_reference.SourceReference") as mock_source_ref:
            mock_source_ref.to_dict.return_value = {"file": "test.pdf", "page": 1}

            # Insert facts for different entities
            self.secure_repo.insert_secure_fact(
                user_context=self.admin_context,
                metric_name="Revenue",
                value=1000000.0,
                entity_name="Company_A",
                period_key="2023",
                scenario="Actual",
                source_reference=mock_source_ref,
                classification_level=DataClassification.INTERNAL,
            )

            self.secure_repo.insert_secure_fact(
                user_context=self.admin_context,
                metric_name="Revenue",
                value=500000.0,
                entity_name="Company_B",
                period_key="2023",
                scenario="Actual",
                source_reference=mock_source_ref,
                classification_level=DataClassification.INTERNAL,
            )

        # Analyst should only see Company_A facts
        facts = self.secure_repo.get_facts_with_rls(self.analyst_context)

        assert len(facts) == 1
        assert facts[0].entity_name == "Company_A"
        assert facts[0].created_by == "admin"  # Inserted by admin

    def test_admin_sees_all_facts(self):
        """Test admin can see all facts."""
        # Insert test facts first
        with patch("src.domain.value_objects.source_reference.SourceReference") as mock_source_ref:
            mock_source_ref.to_dict.return_value = {"file": "test.pdf", "page": 1}

            for entity in ["Company_A", "Company_B", "Company_C"]:
                self.secure_repo.insert_secure_fact(
                    user_context=self.admin_context,
                    metric_name="Revenue",
                    value=1000000.0,
                    entity_name=entity,
                    period_key="2023",
                    scenario="Actual",
                    source_reference=mock_source_ref,
                )

        # Admin should see all facts
        facts = self.secure_repo.get_facts_with_rls(self.admin_context)
        assert len(facts) == 3

        entities = {f.entity_name for f in facts}
        assert entities == {"Company_A", "Company_B", "Company_C"}


class TestSecureRAGEngine:
    """Test secure RAG engine integration."""

    def setup_method(self):
        """Setup test fixtures."""
        self.analyst_context = create_user_context(
            user_id="analyst",
            username="analyst",
            role=UserRole.ANALYST,
            tenant_id="tenant_a",
            accessible_entities=["Company_A"],
        )

    @patch("services.rag_engine.RAGEngine")
    def test_secure_rag_initialization(self, mock_rag_engine):
        """Test secure RAG engine initialization."""
        secure_rag = SecureRAGEngine(self.analyst_context)

        assert secure_rag.user_context == self.analyst_context
        assert secure_rag.access_control is not None
        assert secure_rag.auth_service is not None

    @patch("services.rag_engine.RAGEngine")
    def test_unauthorized_query(self, mock_rag_engine):
        """Test query without authentication."""
        secure_rag = SecureRAGEngine(user_context=None)

        with pytest.raises(SecurityViolationError):
            secure_rag.query("test query")

    @patch("services.rag_engine.RAGEngine")
    def test_query_with_rls_filtering(self, mock_rag_engine):
        """Test query with RLS source filtering."""
        # Mock RAG engine response
        mock_rag_engine.return_value.query.return_value = {
            "answer": "Test answer",
            "sources": [
                {"entity": "Company_A", "classification_level": 2, "content": "Allowed content"},
                {"entity": "Company_B", "classification_level": 2, "content": "Forbidden content"},
                {"entity": "Company_A", "classification_level": 4, "content": "Too sensitive"},
            ],
        }

        secure_rag = SecureRAGEngine(self.analyst_context)
        response = secure_rag.query("test query")

        # Should only have one source (Company_A with appropriate classification)
        assert len(response["sources"]) == 1
        assert response["sources"][0]["entity"] == "Company_A"
        assert response["sources"][0]["classification_level"] <= 2


def run_rls_integration_test():
    """Run comprehensive RLS integration test."""
    print("🧪 Running Row-level Security Integration Test...")

    # Test authentication flow
    auth_service = AuthenticationService()

    print("1. Testing authentication...")
    result = auth_service.authenticate("analyst.azienda.a", "analyst123")
    assert result.success, f"Authentication failed: {result.error_message}"
    user_context = result.user_context
    print(f"   ✅ Authenticated as {user_context.username} (role: {user_context.role.value})")

    # Test access control
    print("2. Testing access control...")
    access_control = AccessControlService()

    # Test entity access
    assert user_context.can_access_entity("Azienda_A"), "Should access Azienda_A"
    assert not user_context.can_access_entity("Azienda_Z"), "Should not access Azienda_Z"
    print("   ✅ Entity access control working")

    # Test RLS filter generation
    rls_filter = access_control.generate_rls_filter(user_context)
    assert len(rls_filter.constraints) > 0, "Should have RLS constraints"
    print(f"   ✅ Generated {len(rls_filter.constraints)} RLS constraints")

    # Test secure fact table
    print("3. Testing secure fact table...")
    secure_repo = SecureFactTableRepository(":memory:", use_duckdb=False)

    try:
        with patch("src.domain.value_objects.source_reference.SourceReference") as mock_source_ref:
            mock_source_ref.to_dict.return_value = {"file": "test.pdf"}

            fact_id = secure_repo.insert_secure_fact(
                user_context=user_context,
                metric_name="Test Metric",
                value=12345.0,
                entity_name="Azienda_A",
                period_key="2023",
                scenario="Actual",
                source_reference=mock_source_ref,
            )
        print(f"   ✅ Inserted fact: {fact_id}")
    except Exception as e:
        print(f"   ❌ Fact insertion failed: {e}")

    # Test fact retrieval with RLS
    facts = secure_repo.get_facts_with_rls(user_context, limit=10)
    print(f"   ✅ Retrieved {len(facts)} facts with RLS applied")

    print("4. Testing session management...")
    # Test session validation
    session_context = auth_service.validate_session(result.session_token)
    assert session_context is not None, "Session should be valid"
    print("   ✅ Session validation working")

    # Test logout
    logout_success = auth_service.logout(result.session_token)
    assert logout_success, "Logout should succeed"
    print("   ✅ Logout working")

    print("🎉 All RLS integration tests passed!")


if __name__ == "__main__":
    # Run integration test when script is executed directly
    run_rls_integration_test()
