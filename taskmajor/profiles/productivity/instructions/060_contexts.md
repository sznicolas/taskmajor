# Tags (Optional)

Use tags for additional categorization if needed.

Common tags: `+work`, `+home`, `+errands`, `+computer`, `+phone`.

Filter by tag when the user asks (ex: "What tasks at home?" → `+home`).

## Energy (UDA)
- `energy` complements tags: combine context and energy when recommending tasks, e.g. `query_tasks(filter:"status:pending +home energy:low")`.
- Use tags for location/tool and `energy` for effort/mental load.
