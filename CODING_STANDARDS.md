# CELUS Coding Standards Manual

This document outlines the coding standards, patterns, and best practices used in the CELUS project. It's designed to help new developers understand the project's specific conventions and maintain consistency across the codebase.

## Table of Contents

1. [Project Overview](#project-overview)
2. [Development Environment](#development-environment)
3. [Code Organization](#code-organization)
4. [Django Models](#django-models)
5. [API Development](#api-development)
6. [Testing Standards](#testing-standards)
7. [Business Logic Organization](#business-logic-organization)
8. [Error Handling](#error-handling)
9. [Background Tasks (Celery)](#background-tasks-celery)
10. [Dependencies and Libraries](#dependencies-and-libraries)
11. [Code Quality Tools](#code-quality-tools)
12. [Inconsistencies and Improvements](#inconsistencies-and-improvements)

## Project Overview

CELUS is a Django-based web application for harvesting and visualization of usage data from electronic information sources. The project uses:

- **Django 4.2** with PostgreSQL as the primary database
- **Django REST Framework** for API development
- **Celery** for background task processing
- **ClickHouse** for analytics and reporting
- **Poetry** for dependency management
- **pytest** for testing

## Development Environment

### Setup

- Use Poetry for dependency management: `poetry install`
- Run tests with: `poetry run pytest`
- Use Python 3.9+ (as specified in pyproject.toml)

### Code Quality Tools

- **Ruff** for linting and formatting (configured in pyproject.toml)
- **pytest** for testing with Django integration
- **pre-commit** hooks for code quality

## Code Organization

### App Structure

The project follows Django's app-based architecture with the following main apps:

```
apps/
├── core/           # Core functionality, user management, base models
├── logs/           # Data import, reporting, analytics
├── publications/   # Platform and title management
├── organizations/  # Organization management
├── sushi/          # SUSHI protocol implementation
├── api/            # API endpoints and views
├── charts/         # Chart definitions and visualization
├── annotations/    # User annotations system
├── tags/           # Tagging system
├── events/         # Event system
├── export/         # Data export functionality
└── scheduler/      # Task scheduling
```

### Import Organization

Follow this import order (enforced by Ruff):

1. Standard library imports
2. Third-party imports
3. Django imports
4. Local app imports

**Example:**

```python
import logging
from datetime import date
from typing import Optional

import requests
from django.db import models
from django.utils.timezone import now

from core.models import User
from logs.exceptions import DataAlreadyPresent
```

## Django Models

### Model Structure

- Use descriptive model names and field names
- Always include `__str__` methods for models
- Use `CreatedUpdatedMixin` for models that need timestamps
- Use `SourceFileMixin` for models that handle file uploads

### Field Patterns

```python
class ExampleModel(CreatedUpdatedMixin, models.Model):
    # Use descriptive field names
    name = models.CharField(max_length=250)
    short_name = models.CharField(max_length=100)

    # Use appropriate field types
    ext_id = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="ID used in original source of this user data"
    )

    # Use JSONField for flexible data
    extra_data = models.JSONField(
        default=dict,
        help_text="User state data that do not deserve a dedicated field",
        blank=True
    )

    # Foreign keys with proper on_delete
    source = models.ForeignKey(
        DataSource,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                name="unique-user-email",
                condition=~models.Q(email="")
            )
        ]
        ordering = ("name",)
```

### Model Managers and QuerySets

- Create custom QuerySets for complex queries
- Use managers to encapsulate common query patterns

```python
class CustomQuerySet(models.QuerySet):
    def active(self):
        return self.filter(is_active=True)

    def for_organization(self, org):
        return self.filter(organization=org)

class CustomManager(models.Manager):
    def get_queryset(self):
        return CustomQuerySet(self.model, using=self._db)

    def active(self):
        return self.get_queryset().active()
```

## API Development

### ViewSet Patterns

Use Django REST Framework ViewSets with consistent patterns:

```python
class ExampleViewSet(ModelViewSet):
    queryset = ExampleModel.objects.all()
    serializer_class = ExampleSerializer
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter, DjangoFilterBackend]
    search_fields = ["name", "description"]
    filterset_fields = ["status", "organization"]

    permission_classes = [
        IsAuthenticated & (
            SuperuserOrAdminPermission |
            OrganizationRequiredPermission
        )
    ]
```

### Serializers

- Use `ModelSerializer` for most cases
- Include read-only fields for computed properties
- Use `PrimaryKeyRelatedField` for write-only foreign keys

```python
class ExampleSerializer(ModelSerializer):
    organization = OrganizationSerializer(read_only=True)
    organization_id = PrimaryKeyRelatedField(
        source="organization",
        write_only=True,
        queryset=Organization.objects.all()
    )
    can_edit = BooleanField(read_only=True)

    class Meta:
        model = ExampleModel
        fields = ("id", "name", "organization", "organization_id", "can_edit")
```

### URL Patterns

- Use consistent URL patterns
- Group related endpoints under common prefixes
- Use descriptive names for URL patterns

```python
urlpatterns = [
    path("", include("logs.urls")),
    path("", include("organizations.urls")),
    path("api/", include("api.urls")),
]
```

## Testing Standards

### Test Organization

- Use pytest with Django integration
- Group tests in classes by functionality
- Use descriptive test method names
- Use parametrized tests for multiple scenarios

### Test Patterns

```python
@pytest.mark.django_db
class TestExampleModel:
    @pytest.mark.parametrize(
        ["input_data", "expected_result"],
        [
            ({"name": "Test"}, True),
            ({"name": ""}, False),
        ]
    )
    def test_validation(self, input_data, expected_result):
        # Test implementation
        pass

    def test_creation(self, user_factory):
        user = user_factory()
        # Test implementation
        pass
```

### Fixtures

- Use factory_boy for test data creation
- Create reusable fixtures in `conftest.py`
- Use descriptive fixture names

```python
@pytest.fixture
def sample_organization():
    return OrganizationFactory(name="Test Org")

@pytest.fixture
def user_with_organization(sample_organization):
    user = UserFactory()
    UserOrganization.objects.create(
        user=user,
        organization=sample_organization
    )
    return user
```

### Test Data

- Use `test_scenarios` module for complex test data
- Use factories for simple test data
- Avoid hardcoded test data when possible

## Business Logic Organization

### Logic Modules

- Place business logic in `logic/` subdirectories within apps
- Use descriptive module names
- Keep logic modules focused on specific functionality

```
apps/logs/logic/
├── attempt_import.py
├── cleanup.py
├── clickhouse.py
├── custom_import.py
├── export.py
├── interest/
│   └── computation.py
├── materialized_reports.py
└── reporting/
    └── slicer.py
```

### Function Patterns

- Use type hints for function parameters and return values
- Use descriptive function names
- Keep functions focused on single responsibilities

```python
def import_one_sushi_attempt(
    attempt: SushiFetchAttempt,
    counter_version: Optional[int] = None,
    organization: Optional[Organization] = None,
    platform: Optional[Platform] = None,
) -> dict:
    """
    Import a single SUSHI attempt.

    Args:
        attempt: The SUSHI fetch attempt to import
        counter_version: Optional counter version override
        organization: Optional organization override
        platform: Optional platform override

    Returns:
        Dictionary containing import statistics
    """
    # Implementation
```

## Error Handling

### Custom Exceptions

- Create specific exception classes for different error types
- Inherit from appropriate base exceptions
- Include helpful error messages and context

```python
class DataAlreadyPresent(DataStructureError):
    """
    Exception raised when trying to import data that already exists.
    """
    pass

class BadRequestException(APIException):
    status_code = 400
    default_code = "bad request"
    default_detail = "Incorrect input data for the request"
```

### Error Handling Patterns

- Use try-except blocks for expected errors
- Log errors appropriately
- Use the `@email_if_fails` decorator for critical tasks

```python
@email_if_fails
def critical_task():
    try:
        # Task implementation
        pass
    except SpecificException as e:
        logger.error("Specific error occurred: %s", e)
        raise
    except Exception as e:
        logger.error("Unexpected error: %s", e)
        raise
```

## Background Tasks (Celery)

### Task Structure

- Use `@celery.shared_task` decorator
- Include `@logged_task` for logging
- Use `@email_if_fails` for error reporting
- Use `@atomic` for database transactions

```python
@celery.shared_task
@logged_task
@email_if_fails
@atomic
def process_data_task(data_id: int):
    """
    Process data in background.

    Args:
        data_id: ID of the data to process
    """
    # Task implementation
```

### Task Organization

- Group related tasks in `tasks.py` files
- Use descriptive task names
- Include proper error handling
- Use appropriate task routing

### Task Scheduling

- Define scheduled tasks in `CELERY_BEAT_SCHEDULE`
- Use appropriate intervals and timeouts
- Consider task dependencies

## Dependencies and Libraries

### External Libraries

The project uses several key external libraries:

- **celus-nibbler**: Data parsing and processing
- **celus-nigiri**: SUSHI protocol implementation
- **celus-pycounter**: COUNTER report processing
- **hcube**: Data aggregation and analysis
- **pandas**: Data manipulation
- **requests**: HTTP client

### Library Usage Patterns

- Import only what you need
- Use aliases for conflicting names
- Delay imports when possible for performance

```python
# Good: Specific import
from celus_nigiri import CounterRecord

# Good: Alias for conflicting names
from hcube.api.models.aggregation import Sum as HSum

# Good: Delayed import for performance
def parse_file(self, path: pathlib.Path, platform: str) -> NibblerOutput:
    from celus_nibbler.definitions import Definition
    # Use Definition here
```

## Code Quality Tools

### Ruff Configuration

The project uses Ruff for linting and formatting with these settings:

- Line length: 100 characters
- Target Python version: 3.9
- Specific ignore rules for test files and Django patterns

### Pre-commit Hooks

- Use pre-commit for automated code quality checks
- Configure hooks for Ruff, tests, and other quality checks

### Testing Requirements

- All tests must pass before merging
- Use `poetry run pytest` to run tests
- Maintain test coverage above 80%

---

# Frontend Coding Standards

## Frontend Overview

The CELUS frontend is built with Vue.js 3 and uses the following technology stack:

- **Vue 3** with Composition API and Options API
- **Vuetify 3** for UI components and theming
- **Vuex 4** for state management
- **Vue Router 4** for routing
- **Vite** for build tooling and development server
- **Vitest** for testing
- **ESLint** for linting
- **Yarn** for package management

## Project Structure

### Frontend Directory Structure

```
design/ui/
├── src/
│   ├── components/          # Reusable Vue components
│   │   ├── account/         # Authentication components
│   │   ├── admin/           # Admin-specific components
│   │   ├── charts/          # Chart and visualization components
│   │   ├── reporting/       # Reporting components
│   │   ├── sushi/           # SUSHI-related components
│   │   ├── tags/            # Tagging system components
│   │   └── util/            # Utility components
│   ├── layouts/             # Layout components
│   ├── libs/                # Utility libraries and helpers
│   ├── locales/             # Internationalization files
│   ├── mixins/              # Vue mixins for shared functionality
│   ├── pages/               # Page components (routes)
│   ├── plugins/             # Vue plugins configuration
│   ├── router/              # Vue Router configuration
│   ├── store/               # Vuex store modules
│   ├── styles/              # Global styles and SCSS
│   └── workers/             # Web workers
├── specs/                   # Test files
├── public/                  # Static assets
└── package.json
```

## Vue Component Standards

### Component Structure

Follow this order for Vue component sections:

1. `<template>` - HTML template
2. `<script>` - JavaScript logic
3. `<style>` - Component styles

### Options API Pattern

Use the Options API for most components with this structure:

```vue
<template>
  <div class="component-name">
    <!-- Template content -->
  </div>
</template>

<script>
import { mapActions, mapGetters, mapState } from "vuex";

export default {
  name: "ComponentName",

  components: {
    // Component dependencies
  },

  mixins: [
    // Shared mixins
  ],

  props: {
    // Component props with validation
    propName: {
      type: String,
      required: true,
      default: "",
    },
  },

  data() {
    return {
      // Component state
    };
  },

  computed: {
    // Computed properties
    ...mapState({
      // Vuex state mappings
    }),
    ...mapGetters({
      // Vuex getter mappings
    }),
  },

  watch: {
    // Watchers
  },

  created() {
    // Lifecycle hooks
  },

  mounted() {
    // Lifecycle hooks
  },

  methods: {
    // Component methods
    ...mapActions({
      // Vuex action mappings
    }),
  },
};
</script>

<style lang="scss" scoped>
/* Component styles */
</style>
```

### Composition API Pattern

Use Composition API for complex components:

```vue
<template>
  <div class="component-name">
    <!-- Template content -->
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from "vue";
import { useStore } from "vuex";

const props = defineProps({
  propName: {
    type: String,
    required: true,
    default: "",
  },
});

const emit = defineEmits(["update:modelValue"]);

const store = useStore();

// Reactive data
const data = ref(null);

// Computed properties
const computedValue = computed(() => {
  return store.getters.someValue;
});

// Methods
const handleClick = () => {
  emit("update:modelValue", newValue);
};

// Lifecycle
onMounted(() => {
  // Setup logic
});
</script>
```

### Component Naming

- Use PascalCase for component names
- Use descriptive names that indicate purpose
- Prefix with module name when appropriate (e.g., `SushiCredentialsEditDialog`)

### Props and Events

- Define props with proper validation
- Use descriptive prop names
- Define events in `emits` option for Composition API
- Use kebab-case for event names in templates

```javascript
props: {
  platformId: {
    required: true,
    type: Number
  },
  uploadObjectId: {
    required: false,
    type: Number
  }
},

emits: ["update:modelValue", "change", "error"]
```

## State Management (Vuex)

### Store Module Structure

Organize Vuex modules with this pattern:

```javascript
export default {
  namespaced: true,

  state: {
    // Module state
  },

  getters: {
    // Computed state
  },

  actions: {
    // Async operations
    async loadData({ commit, state }, params) {
      try {
        const response = await http({ url: "/api/data", params });
        commit("setData", response.data);
        return response.data;
      } catch (error) {
        console.error("Error loading data:", error);
        throw error;
      }
    },
  },

  mutations: {
    // State mutations
    setData(state, data) {
      state.data = data;
    },
  },
};
```

### State Management Patterns

- Use namespaced modules for organization
- Keep mutations synchronous
- Use actions for async operations
- Map state and getters in components using `mapState` and `mapGetters`
- Use `mapActions` for dispatching actions

## API Communication

### HTTP Client Setup

Use the centralized HTTP client from `@/libs/http`:

```javascript
import http from "@/libs/http";

// Basic usage
const { response, error } = await http({
  url: "/api/endpoint",
  method: "get",
  params: { id: 1 },
});

// With component cancellation
const { response, error } = await this.http({
  url: "/api/endpoint",
  method: "post",
  data: formData,
  component: this._cid,
});
```

### API Call Patterns

- Always use the `http` wrapper for API calls
- Include component cancellation for long-running requests
- Handle errors appropriately
- Use proper HTTP methods (GET, POST, PUT, DELETE)

### Error Handling

```javascript
const { response, error } = await this.http({
  url: "/api/endpoint",
  label: "Loading data",
  errorTexts: {
    404: "Data not found",
    500: "Server error",
  },
});

if (error) {
  // Error is already handled by the http wrapper
  return;
}

// Process successful response
const data = response.data;
```

## Styling Standards

### SCSS Usage

- Use SCSS for component styles
- Use `scoped` attribute for component-specific styles
- Follow BEM methodology for CSS class naming
- Use Vuetify's design tokens when possible

```scss
<style lang="scss" scoped>
.component-name {
  &__element {
    // Element styles
  }

  &--modifier {
    // Modifier styles
  }

  .vuetify-class {
    // Override Vuetify styles
  }
}
</style>
```

### Vuetify Integration

- Use Vuetify components consistently
- Follow Vuetify's design system
- Use Vuetify's spacing and color utilities
- Customize theme through `src/styles/settings.scss`

## Testing Standards

### Test Structure

Use Vitest for testing with this structure:

```javascript
import { describe, expect, test } from "vitest";
import { mount } from "./setup";
import ComponentName from "@/components/ComponentName";

describe("ComponentName", () => {
  test("should render correctly", () => {
    const wrapper = mount(ComponentName, {
      props: { propName: "test" },
    });

    expect(wrapper.html()).toContain("expected content");
  });

  test("should handle user interaction", async () => {
    const wrapper = mount(ComponentName);

    await wrapper.find("button").trigger("click");

    expect(wrapper.emitted("click")).toBeTruthy();
  });
});
```

### Test Patterns

- Use descriptive test names
- Test component behavior, not implementation details
- Use `mount` from test setup for component testing
- Mock external dependencies when necessary
- Test both success and error scenarios

### Test Data

- Use realistic test data
- Create test data factories for complex objects
- Use consistent test data across related tests

## Internationalization (i18n)

### Translation Files

- Store translations in YAML files in `src/locales/`
- Use descriptive keys that indicate context
- Group related translations together

```yaml
# src/locales/common.yaml
buttons:
  save: "Save"
  cancel: "Cancel"
  delete: "Delete"

messages:
  success: "Operation completed successfully"
  error: "An error occurred"
```

### Usage in Components

```vue
<template>
  <div>
    <h1>{{ $t("pages.title") }}</h1>
    <v-btn>{{ $t("buttons.save") }}</v-btn>
  </div>
</template>

<script>
export default {
  computed: {
    pageTitle() {
      return this.$t("pages.title");
    },
  },
};
</script>
```

## Performance Considerations

### Component Optimization

- Use `v-show` vs `v-if` appropriately
- Implement proper key attributes for lists
- Use `v-memo` for expensive computations
- Lazy load components when appropriate

### Bundle Optimization

- Use dynamic imports for code splitting
- Optimize images and assets
- Use Vite's built-in optimizations
- Monitor bundle size

## Code Organization

### File Naming

- Use PascalCase for Vue component files
- Use camelCase for JavaScript utility files
- Use kebab-case for SCSS files
- Use descriptive names that indicate purpose

### Import Organization

```javascript
// 1. Vue and framework imports
import { ref, computed, onMounted } from "vue";
import { mapActions, mapGetters } from "vuex";

// 2. Third-party library imports
import axios from "axios";
import { format } from "date-fns";

// 3. Internal imports
import http from "@/libs/http";
import ComponentName from "@/components/ComponentName";
```

### Mixins Usage

- Use mixins for shared functionality
- Keep mixins focused on specific concerns
- Document mixin behavior clearly
- Avoid deep mixin hierarchies

## Development Workflow

### Development Server

```bash
# Start development server
yarn dev

# Build for production
yarn build

# Run tests
yarn test

# Lint code
yarn lint
```

### Code Quality

- Use ESLint for code linting
- Follow Vue.js style guide
- Use Prettier for code formatting
- Write meaningful commit messages

### Git Workflow

- Use feature branches for new features
- Write descriptive commit messages
- Use conventional commit format when possible
- Keep commits focused and atomic
