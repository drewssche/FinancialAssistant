# Request Budgets

Source of truth for request-count ceilings used by automated regression gate.

## Budget Table
| Scenario | Endpoint | Max requests |
| --- | --- | ---: |
| Open Dashboard | `GET /api/v1/dashboard/summary` | 1 |
| Open Dashboard | `GET /api/v1/debts/cards` | 1 |
| Open Dashboard | `GET /api/v1/operations` | 1 |
| Operations Search | `GET /api/v1/operations` | 1 |
| Operations Search Burst (Typing) | `PUT /api/v1/preferences` | 1 |
| Create Operation + Refresh | `POST /api/v1/operations` | 1 |
| Create Operation + Refresh (Legacy Worst-Case Alias) | `GET /api/v1/dashboard/summary` | 1 |
| Create Operation + Refresh (Legacy Worst-Case Alias) | `GET /api/v1/operations` | 2 |
| Create Operation + Refresh (Dashboard Active) | `GET /api/v1/dashboard/summary` | 1 |
| Create Operation + Refresh (Dashboard Active) | `GET /api/v1/operations` | 2 |
| Create Operation + Refresh (Non-Dashboard Active) | `GET /api/v1/dashboard/summary` | 0 |
| Create Operation + Refresh (Non-Dashboard Active) | `GET /api/v1/operations` | 1 |
| Debts Search | `GET /api/v1/debts/cards` | 1 |
| Open Item Catalog | `GET /api/v1/operations/item-templates` | 1 |
| Item Catalog Search (Local Snapshot Complete) | `GET /api/v1/operations/item-templates` | 0 |
| Item Catalog Search (Server Fallback) | `GET /api/v1/operations/item-templates` | 1 |
| Item Catalog Group Toggle Burst | `PUT /api/v1/preferences` | 1 |
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
  "operations_search_burst_typing": {
    "PUT /api/v1/preferences": 1
  },
  "create_operation_refresh": {
    "POST /api/v1/operations": 1,
    "GET /api/v1/dashboard/summary": 1,
    "GET /api/v1/operations": 2
  },
  "create_operation_refresh_dashboard_active": {
    "POST /api/v1/operations": 1,
    "GET /api/v1/dashboard/summary": 1,
    "GET /api/v1/operations": 2
  },
  "create_operation_refresh_non_dashboard_active": {
    "POST /api/v1/operations": 1,
    "GET /api/v1/dashboard/summary": 0,
    "GET /api/v1/operations": 1
  },
  "debts_search": {
    "GET /api/v1/debts/cards": 1
  },
  "open_item_catalog": {
    "GET /api/v1/operations/item-templates": 1
  },
  "item_catalog_search_local_snapshot_complete": {
    "GET /api/v1/operations/item-templates": 0
  },
  "item_catalog_search_server_fallback": {
    "GET /api/v1/operations/item-templates": 1
  },
  "item_catalog_group_toggle_burst": {
    "PUT /api/v1/preferences": 1
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
