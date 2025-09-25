# PR Notes

## Outstanding from Current Request
- Phase 5 panels show executed CLI after runs complete, but do not yet surface pre-run previews using the new IPC helper. Extend the renderer to call `window.CWT.run.preview` (or equivalent) so users can inspect the CLI before launching these commands.
