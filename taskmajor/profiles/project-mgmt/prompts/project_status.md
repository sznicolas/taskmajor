# Project Status

Report the status of a specific project.

## Steps
1. Query tasks for the project.
2. Calculate completion rate.
3. Identify blockers.
4. Sum estimates (done vs pending).

## Output Format
📊 Project Status — {project_name}

✅ COMPLETED ({count}/{total})
• {description}

⏳ IN PROGRESS ({count})
• {description}

🚧 BLOCKERS ({count})
• {description} (Blocked by: {blocked_by})

📈 EFFORT
Done: {done_hours}h | Pending: {pending_hours}h
