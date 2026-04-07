# GraphQL Extension

## Documentation

- Extending GraphQL: https://craftcms.com/docs/5.x/extend/graphql.html
- GraphQL API (consumer): https://craftcms.com/docs/5.x/development/graphql.html
- Class reference: https://docs.craftcms.com/api/v5/craft-gql-base-query.html

## Common Pitfalls

- Skipping `TypeManager::prepareFieldDefinitions()` — other plugins can't extend your types, breaking the extension chain.
- Not registering schema components — your types become available in the public schema with no access control.
- Returning field definitions without checking the active token's scope — all data exposed regardless of permissions.
- Forgetting `EVENT_REGISTER_GQL_TYPES` — interface and type classes must be registered before anything else works.
- Using `ddev craft make gql-directive` for query-level logic — directives transform resolved values, they don't modify queries.

## Table of Contents

- [Scaffold](#scaffold)
- [Architecture: Interface → Type → Generator](#architecture-interface--type--generator)
- [Interface Definition](#interface-definition)
- [Query Registration](#query-registration)
- [Schema Components (Access Control)](#schema-components-access-control)
- [Custom Directives](#custom-directives)
- [Event Registration](#event-registration-all-in-plugin-init)
- [Event Reference](#event-reference)

## Scaffold

```bash
ddev craft make gql-directive --with-docblocks
```

Other GQL components (types, queries, mutations, resolvers) have no generator — create manually following the patterns below.

## Architecture: Interface → Type → Generator

Every custom element exposed via GraphQL follows a three-class chain:

1. **Interface** — extends `craft\gql\interfaces\Element`. Defines abstract field definitions shared across all variants.
2. **Type** — extends `craft\gql\types\elements\Element`. Declares which interface it implements.
3. **Generator** — implements `craft\gql\base\GeneratorInterface`. Dynamically creates concrete `ObjectType` instances per context (e.g., per entry type, per widget type).

### Directory Structure

```
src/gql/
├── arguments/elements/MyElement.php
├── directives/MyDirective.php
├── interfaces/elements/MyElement.php
├── mutations/MyElement.php
├── queries/MyElement.php
├── resolvers/elements/MyElement.php
├── resolvers/mutations/MyElement.php
├── types/elements/MyElement.php
├── types/generators/MyElementType.php
└── types/input/MyElement.php
```

## Interface Definition

```php
use craft\gql\interfaces\Element;
use craft\gql\GqlEntityRegistry;
use craft\gql\TypeManager;
use GraphQL\Type\Definition\ObjectType;
use GraphQL\Type\Definition\Type;

class MyElementInterface extends Element
{
    public static function getTypeGenerator(): string
    {
        return MyElementType::class;
    }

    public static function getType($fields = null): Type
    {
        if ($type = GqlEntityRegistry::getEntity(static::getName())) {
            return $type;
        }

        $type = GqlEntityRegistry::createEntity(static::getName(), new InterfaceType([
            'name' => static::getName(),
            'fields' => static::class . '::getFieldDefinitions',
            'description' => 'Interface for custom elements.',
            'resolveType' => static::class . '::resolveElementTypeName',
        ]));

        MyElementType::generateTypes();

        return $type;
    }

    public static function getName(): string
    {
        return 'MyElementInterface';
    }

    public static function getFieldDefinitions(): array
    {
        $fields = array_merge(parent::getFieldDefinitions(), [
            'customField' => [
                'name' => 'customField',
                'type' => Type::string(),
                'description' => 'A custom field.',
            ],
        ]);

        // REQUIRED — lets other plugins extend your type's fields
        return TypeManager::prepareFieldDefinitions($fields, static::getName());
    }
}
```

**Critical:** Always call `TypeManager::prepareFieldDefinitions()` before returning. This fires `TypeManager::EVENT_DEFINE_GQL_TYPE_FIELDS`, allowing other plugins to modify your type's fields. Skipping this breaks the extension chain.

## Query Registration

```php
use craft\gql\base\Query;
use GraphQL\Type\Definition\Type;

class MyElementQuery extends Query
{
    public static function getQueries(bool $checkToken = true): array
    {
        if ($checkToken && !MyGqlHelper::canQueryMyElements()) {
            return [];
        }

        return [
            'myElements' => [
                'type' => Type::listOf(MyElementInterface::getType()),
                'args' => MyElementArguments::getArguments(),
                'resolve' => MyElementResolver::class . '::resolve',
                'description' => 'Query custom elements.',
            ],
        ];
    }
}
```

## Schema Components (Access Control)

Register schema components so admins can control access per GQL token. Without this, your types are available in the public schema by default:

```php
use craft\events\RegisterGqlSchemaComponentsEvent;
use craft\services\Gql;

Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_SCHEMA_COMPONENTS,
    function(RegisterGqlSchemaComponentsEvent $event) {
        $event->queries = array_merge($event->queries, [
            'My Elements' => [
                'myelements.all:read' => ['label' => Craft::t('my-plugin', 'View all elements')],
            ],
        ]);
        $event->mutations = array_merge($event->mutations, [
            'My Elements' => [
                'myelements.all:edit' => ['label' => Craft::t('my-plugin', 'Edit all elements')],
            ],
        ]);
    }
);
```

### Custom GQL Helper

Extend `craft\helpers\Gql` to check token scopes in resolvers and queries:

```php
use craft\helpers\Gql;

class MyGqlHelper extends Gql
{
    public static function canQueryMyElements(): bool
    {
        $allowedEntities = self::extractAllowedEntitiesFromSchema('read');
        return isset($allowedEntities['myelements']);
    }

    public static function canMutateMyElements(): bool
    {
        $allowedEntities = self::extractAllowedEntitiesFromSchema('edit');
        return isset($allowedEntities['myelements']);
    }
}
```

## Custom Directives

Directives transform **resolved values** — they fire after data is fetched. They are not governed by schema permissions.

```php
use craft\gql\base\Directive;
use craft\gql\GqlEntityRegistry;
use GraphQL\Language\DirectiveLocation;
use GraphQL\Type\Definition\ResolveInfo;

class MyDirective extends Directive
{
    public static function create(): GqlDirective
    {
        $typeName = static::name();

        return GqlEntityRegistry::getOrCreate($typeName, fn() => new self([
            'name' => $typeName,
            'locations' => [DirectiveLocation::FIELD],
            'args' => [/* argument definitions */],
            'description' => 'Transforms the resolved value.',
        ]));
    }

    public static function name(): string
    {
        return 'myDirective';
    }

    public static function apply(
        mixed $source,
        mixed $value,
        array $arguments,
        ResolveInfo $resolveInfo
    ): mixed {
        // Transform $value based on $arguments
        return strtoupper($value);
    }
}
```

## Event Registration (All in Plugin `init()`)

```php
// Register types (must come first)
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_TYPES,
    function(RegisterGqlTypesEvent $event) {
        $event->types[] = MyElementInterface::class;
    }
);

// Register queries
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_QUERIES,
    function(RegisterGqlQueriesEvent $event) {
        $event->queries = array_merge($event->queries, MyElementQuery::getQueries());
    }
);

// Register mutations
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_MUTATIONS,
    function(RegisterGqlMutationsEvent $event) {
        $event->mutations = array_merge($event->mutations, MyElementMutation::getMutations());
    }
);

// Register directives
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_DIRECTIVES,
    function(RegisterGqlDirectivesEvent $event) {
        $event->directives[] = MyDirective::class;
    }
);

// Register schema components (access control)
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_SCHEMA_COMPONENTS, ...);
```

## Event Reference

| Event | Class | Purpose |
|-------|-------|---------|
| `EVENT_REGISTER_GQL_TYPES` | `Gql` | Register interface/type classes |
| `EVENT_REGISTER_GQL_QUERIES` | `Gql` | Register query definitions |
| `EVENT_REGISTER_GQL_MUTATIONS` | `Gql` | Register mutation definitions |
| `EVENT_REGISTER_GQL_DIRECTIVES` | `Gql` | Register directive classes |
| `EVENT_REGISTER_GQL_SCHEMA_COMPONENTS` | `Gql` | Register schema permission toggles |
| `EVENT_BEFORE_EXECUTE_GQL_QUERY` | `Gql` | Pre-execution hook (set `$event->result` to short-circuit) |
| `EVENT_AFTER_EXECUTE_GQL_QUERY` | `Gql` | Post-execution hook |
| `EVENT_DEFINE_GQL_TYPE_FIELDS` | `TypeManager` | Add/modify fields on any type |
| `EVENT_DEFINE_GQL_ARGUMENT_HANDLERS` | `ArgumentManager` | Register argument preprocessing |
