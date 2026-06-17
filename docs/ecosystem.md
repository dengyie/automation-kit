# Ecosystem

`automation-kit` is the shared foundation repository.

- `automation_core`: business-agnostic runtime primitives
- `automation_runner`: public workflow authoring and execution surface
- `adapters`: thin official backend integrations
- `examples`: thin reference consumers only

Business applications belong in separate repositories such as
`automation-app-damai` and `automation-app-dianping`.
Optional reusable capabilities belong in separate repositories such as
`automation-plugin-ocr`.
