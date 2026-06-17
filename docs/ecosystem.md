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

## Repository Map

- core: `https://github.com/dengyie/automation-kit`
- app: `https://github.com/dengyie/automation-app-damai`
- app: `https://github.com/dengyie/automation-app-dianping`
- plugin: `https://github.com/dengyie/automation-plugin-ocr`

The ecosystem baseline assumes these repositories are public so downstream
projects can inspect contracts, examples, and compatibility notes without
private coordination.
