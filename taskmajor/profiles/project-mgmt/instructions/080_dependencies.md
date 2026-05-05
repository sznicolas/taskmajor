# Dependencies

- Use `depends: <task_id>` to link tasks.
- A task with a dependency is blocked until the predecessor is done.
- Check `taskmajor://queue/blockers` to see what is holding up progress.
- When planning, ensure dependencies are ordered correctly.
