# UI-012A Resume Note

The first UI-012A installer successfully removed the defective timeline
auto-selection block before failing on a test-file anchor mismatch.

The accepted focused test uses an inline tuple:

```python
for check in (
    test_identity_is_immutable,
    test_presenter_and_view_boundaries,
    test_syntax,
):
```

The original hotfix incorrectly expected a standalone `test_syntax` list anchor.
This resume patch preserves or completes the source correction and updates the
actual test structure. It is safe for the partially applied state produced by the
reported failure.
