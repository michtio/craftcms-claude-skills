# Scaffolding

- Always use `ddev craft make <type> --with-docblocks` to scaffold new components.
- Never manually create boilerplate that the generator handles.
- After scaffolding, customize: add section headers, `@author {{authorName}}`, `@since` version, `@throws` chains, and project naming conventions.
- Available generators: `element-type`, `service`, `controller`, `command`, `queue-job`, `model`, `record`, `field-type`, `validator`, `widget-type`, `utility`, `asset-bundle`, `behavior`, `twig-extension`, `element-action`, `element-condition-rule`, `element-exporter`, `gql-directive`.
