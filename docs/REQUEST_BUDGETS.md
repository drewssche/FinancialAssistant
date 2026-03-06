# Request Budgets

Source of truth for request-count ceilings used by automated regression gate.

## Budget Table
| Scenario | Endpoint | Max requests |
| --- | --- | ---: |
| Open Dashboard | `GET /api/v1/dashboard/summary` | 1 |
| Open Dashboard | `GET /api/v1/debts/cards` | 1 |
| Open Dashboard | `GET /api/v1/operations` | 1 |
| Operations Search | `GET /api/v1/operations` | 1 |
| Create Operation + Refresh | `POST /api/v1/operations` | 1 |
| Create Operation + Refresh | `GET /api/v1/dashboard/summary` | 1 |
| Create Operation + Refresh | `GET /api/v1/operations` | 2 |
| Debts Search | `GET /api/v1/debts/cards` | 1 |
| Section Switch (No Front Cache) | `GET /api/v1/operations` | 2 |
| Section Switch (No Front Cache) | `GET /api/v1/debts/cards` | 2 |
| Section Switch (No Front Cache) | `GET /api/v1/categories/groups` | 2 |
| Section Switch (No Front Cache) | `GET /api/v1/categories` | 4 |
| Section Switch (Front Cache TTL) | `GET /api/v1/operations` | 1 |
| Section Switch (Front Cache TTL) | `GET /api/v1/debts/cards` | 1 |
| Section Switch (Front Cache TTL) | `GET /api/v1/categories/groups` | 1 |
| Section Switch (Front Cache TTL) | `GET /api/v1/categories` | 2 |

<!-- REQUEST_BUDGETS_JSON_START -->
```json
{
  "open_dashboard": {
    "GET /api/v1/dashboard/summary": 1,
    "GET /api/v1/debts/cards": 1,
    "GET /api/v1/operations": 1
  },
  "operations_search": {
    "GET /api/v1/operations": 1
  },
  "create_operation_refresh": {
    "POST /api/v1/operations": 1,
    "GET /api/v1/dashboard/summary": 1,
    "GET /api/v1/operations": 2
  },
  "debts_search": {
    "GET /api/v1/debts/cards": 1
  },
  "section_switch_no_front_cache": {
    "GET /api/v1/operations": 2,
    "GET /api/v1/debts/cards": 2,
    "GET /api/v1/categories/groups": 2,
    "GET /api/v1/categories": 4
  },
  "section_switch_front_cache_ttl": {
    "GET /api/v1/operations": 1,
    "GET /api/v1/debts/cards": 1,
    "GET /api/v1/categories/groups": 1,
    "GET /api/v1/categories": 2
  }
}
```
<!-- REQUEST_BUDGETS_JSON_END -->
