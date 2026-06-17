# Ecosystem

`automation-kit` is the shared foundation repository.

- `automation_core`: business-agnostic runtime primitives
- `automation_runner`: public workflow authoring and execution surface
- `adapters`: thin official backend integrations
- `examples`: thin reference consumers only

Business applications belong in separate repositories such as
`automation-app-damai` and `automation-app-dianping`.
Visual challenge capabilities belong in `slidex`, including OCR, captcha
solving, screenshot recognition, and manual visual fallback.

## Repository Map

- core: `https://github.com/dengyie/automation-kit`
- app: `https://github.com/dengyie/automation-app-damai`
- app: `https://github.com/dengyie/automation-app-dianping`
- visual platform: `https://github.com/dengyie/slidex`

The ecosystem baseline assumes these repositories are public so downstream
projects can inspect contracts, examples, and compatibility notes without
private coordination.

`slidex` remains optional. `automation-kit` must not import it directly, and
applications should inject visual challenge solvers only when a workflow needs
OCR, captcha solving, screenshot recognition, or manual visual fallback.
