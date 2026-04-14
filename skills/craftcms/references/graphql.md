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
- Mutation resolvers that don't validate before saving — elements silently fail or throw unstructured exceptions instead of returning `userErrors`.
- Using `!empty()` for optional integer arguments like `limit` — `0` is a valid value but `!empty(0)` is `true`. Use `isset()` for nullable integers.
- Tokens are stored in the database only, not project config — forgetting to create tokens per environment leaves staging/production with no API access.

## Table of Contents

- [Scaffold](#scaffold)
- [Architecture: Interface -> Type -> Generator](#architecture-interface--type--generator)
- [Interface Definition](#interface-definition)
- [Arguments Class](#arguments-class)
- [Query Registration](#query-registration)
- [Query Resolvers](#query-resolvers)
- [Schema Components (Access Control)](#schema-components-access-control)
- [Mutations](#mutations)
- [Error Handling in Mutations](#error-handling-in-mutations)
- [Custom Directives](#custom-directives)
- [Event Registration](#event-registration-all-in-plugin-init)
- [Event Reference](#event-reference)
- [Token Management](#token-management)
- [Consumer Query Patterns](#consumer-query-patterns)
- [Testing GraphQL](#testing-graphql)

## Scaffold

```bash
ddev craft make gql-directive --with-docblocks
```

Other GQL components (types, queries, mutations, resolvers) have no generator — create manually following the patterns below.

## Architecture: Interface -> Type -> Generator

Every custom element exposed via GraphQL follows a three-class chain: **Interface** (extends `craft\gql\interfaces\Element`, defines shared fields), **Type** (extends `craft\gql\types\elements\Element`, declares interface), **Generator** (implements `craft\gql\base\GeneratorInterface`, creates concrete `ObjectType` per context).

```
src/gql/
├── arguments/elements/    ├── mutations/              ├── types/elements/
├── directives/            ├── queries/                ├── types/generators/
├── interfaces/elements/   ├── resolvers/elements/     └── types/input/
                           └── resolvers/mutations/
```

## Interface Definition

```php
use craft\gql\interfaces\Element;
use craft\gql\GqlEntityRegistry;
use craft\gql\TypeManager;
use GraphQL\Type\Definition\InterfaceType;
use GraphQL\Type\Definition\Type;

class MyElementInterface extends Element
{
    public static function getTypeGenerator(): string { return MyElementType::class; }

    public static function getType($fields = null): Type
    {
        if ($type = GqlEntityRegistry::getEntity(static::getName())) { return $type; }
        $type = GqlEntityRegistry::createEntity(static::getName(), new InterfaceType([
            'name' => static::getName(),
            'fields' => static::class . '::getFieldDefinitions',
            'description' => 'Interface for custom elements.',
            'resolveType' => static::class . '::resolveElementTypeName',
        ]));
        MyElementType::generateTypes();
        return $type;
    }

    public static function getName(): string { return 'MyElementInterface'; }

    public static function getFieldDefinitions(): array
    {
        $fields = array_merge(parent::getFieldDefinitions(), [
            'customField' => ['name' => 'customField', 'type' => Type::string(), 'description' => 'A custom field.'],
        ]);
        // REQUIRED — lets other plugins extend your type's fields
        return TypeManager::prepareFieldDefinitions($fields, static::getName());
    }
}
```

Always call `TypeManager::prepareFieldDefinitions()` before returning. This fires `EVENT_DEFINE_GQL_TYPE_FIELDS`, allowing other plugins to modify your type's fields.

## Arguments Class

Arguments define the query parameters consumers can pass. Referenced by query registration but often left undefined — here is the complete pattern.

```php
use GraphQL\Type\Definition\Type;

class MyElementArguments
{
    public static function getArguments(): array
    {
        return [
            'id' => ['name' => 'id', 'type' => Type::listOf(Type::int())],
            'handle' => ['name' => 'handle', 'type' => Type::listOf(Type::string())],
            'limit' => ['name' => 'limit', 'type' => Type::int()],
            'offset' => ['name' => 'offset', 'type' => Type::int()],
            'orderBy' => ['name' => 'orderBy', 'type' => Type::string()],
            'status' => ['name' => 'status', 'type' => Type::listOf(Type::string())],
        ];
    }
}
```

`Type::int()` for singles, `Type::listOf(Type::int())` for arrays, `Type::boolean()` for flags. Use `listOf()` for arguments accepting multiple values — Craft element queries accept arrays natively.

## Query Registration

```php
use craft\gql\base\Query;
use GraphQL\Type\Definition\Type;

class MyElementQuery extends Query
{
    public static function getQueries(bool $checkToken = true): array
    {
        if ($checkToken && !MyGqlHelper::canQueryMyElements()) { return []; }
        return [
            'myElements' => [
                'type' => Type::listOf(MyElementInterface::getType()),
                'args' => MyElementArguments::getArguments(),
                'resolve' => MyElementResolver::class . '::resolve',
            ],
            'myElement' => [
                'type' => MyElementInterface::getType(),
                'args' => MyElementArguments::getArguments(),
                'resolve' => MyElementResolver::class . '::resolveOne',
            ],
        ];
    }
}
```

Craft convention: plural query returns a list (`entries`), singular returns one result (`entry`).

## Query Resolvers

Resolvers bridge GraphQL arguments to Craft element queries. Extend `craft\gql\base\ElementResolver` for elements.

```php
use craft\gql\base\ElementResolver;
use GraphQL\Type\Definition\ResolveInfo;
use myplugin\elements\MyElement;

class MyElementResolver extends ElementResolver
{
    public static function resolve(
        mixed $source,
        array $arguments,
        mixed $context,
        ResolveInfo $resolveInfo,
    ): mixed {
        $query = MyElement::find();

        // Array arguments — use !empty() since empty arrays are falsy
        if (!empty($arguments['id'])) { $query->id($arguments['id']); }
        if (!empty($arguments['handle'])) { $query->handle($arguments['handle']); }
        if (!empty($arguments['status'])) { $query->status($arguments['status']); }

        // Integer arguments — use isset() because 0 is a valid value
        if (isset($arguments['limit'])) { $query->limit($arguments['limit']); }
        if (isset($arguments['offset'])) { $query->offset($arguments['offset']); }

        // String arguments
        if (!empty($arguments['orderBy'])) { $query->orderBy($arguments['orderBy']); }

        return $query->all();
    }

    public static function resolveOne(
        mixed $source,
        array $arguments,
        mixed $context,
        ResolveInfo $resolveInfo,
    ): mixed {
        $query = MyElement::find();
        if (!empty($arguments['id'])) { $query->id($arguments['id']); }
        if (!empty($arguments['handle'])) { $query->handle($arguments['handle']); }
        return $query->one();
    }
}
```

**`!empty()` vs `isset()`:** Use `!empty()` for arrays/strings — empty means "no filter." Use `isset()` for integers like `limit` — `0` is valid but `!empty(0)` is `true`.

## Schema Components (Access Control)

Without schema components, your types appear in the public schema with no access control:

```php
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_SCHEMA_COMPONENTS,
    function(RegisterGqlSchemaComponentsEvent $event) {
        $event->queries = array_merge($event->queries, [
            'My Elements' => ['myelements.all:read' => ['label' => Craft::t('my-plugin', 'View all elements')]],
        ]);
        $event->mutations = array_merge($event->mutations, [
            'My Elements' => ['myelements.all:edit' => ['label' => Craft::t('my-plugin', 'Edit all elements')]],
        ]);
    }
);
```

### Custom GQL Helper

Extend `craft\helpers\Gql` to check token scopes in resolvers and queries:

```php
class MyGqlHelper extends \craft\helpers\Gql
{
    public static function canQueryMyElements(): bool
    {
        return isset(self::extractAllowedEntitiesFromSchema('read')['myelements']);
    }
    public static function canMutateMyElements(): bool
    {
        return isset(self::extractAllowedEntitiesFromSchema('edit')['myelements']);
    }
}
```

## Mutations

Mutations require three classes: an input type, a mutation definition, and a mutation resolver.

### Input Type

```php
use craft\gql\GqlEntityRegistry;
use GraphQL\Type\Definition\InputObjectType;
use GraphQL\Type\Definition\Type;

class MyElementInput
{
    public static function getType(): InputObjectType
    {
        $typeName = 'MyElementInput';
        if ($type = GqlEntityRegistry::getEntity($typeName)) {
            return $type;
        }
        return GqlEntityRegistry::createEntity($typeName, new InputObjectType([
            'name' => $typeName,
            'fields' => [
                'title' => ['name' => 'title', 'type' => Type::string()],
                'handle' => ['name' => 'handle', 'type' => Type::string()],
                'enabled' => ['name' => 'enabled', 'type' => Type::boolean()],
            ],
        ]));
    }
}
```

### Mutation Definition

```php
use craft\gql\base\Mutation;
use GraphQL\Type\Definition\Type;

class MyElementMutation extends Mutation
{
    public static function getMutations(): array
    {
        if (!MyGqlHelper::canMutateMyElements()) { return []; }
        return [
            'saveMyElement' => [
                'type' => MyElementInterface::getType(),
                'args' => [
                    'id' => ['name' => 'id', 'type' => Type::int()],
                    'input' => ['name' => 'input', 'type' => Type::nonNull(MyElementInput::getType())],
                ],
                'resolve' => MyElementMutationResolver::class . '::saveMyElement',
            ],
            'deleteMyElement' => [
                'type' => Type::boolean(),
                'args' => ['id' => ['name' => 'id', 'type' => Type::nonNull(Type::int())]],
                'resolve' => MyElementMutationResolver::class . '::deleteMyElement',
            ],
        ];
    }
}
```

### Mutation Resolver

```php
use craft\gql\base\MutationResolver;
use GraphQL\Error\UserError;
use GraphQL\Type\Definition\ResolveInfo;
use myplugin\elements\MyElement;

class MyElementMutationResolver extends MutationResolver
{
    /** @throws UserError if the element fails validation or is not found */
    public static function saveMyElement(mixed $source, array $arguments, mixed $context, ResolveInfo $resolveInfo): MyElement
    {
        $input = $arguments['input'];

        if ($id = $arguments['id'] ?? null) {
            $element = MyElement::find()->id($id)->one() ?? throw new UserError("Element not found: {$id}");
        } else {
            $element = new MyElement();
        }

        if (isset($input['title'])) { $element->title = $input['title']; }
        if (isset($input['handle'])) { $element->handle = $input['handle']; }
        if (isset($input['enabled'])) { $element->enabled = $input['enabled']; }

        if (!Craft::$app->getElements()->saveElement($element)) {
            $errors = [];
            foreach ($element->getFirstErrors() as $attr => $msg) { $errors[] = "{$attr}: {$msg}"; }
            throw new UserError('Validation failed: ' . implode(', ', $errors));
        }
        return $element;
    }

    /** @throws UserError if the element is not found */
    public static function deleteMyElement(mixed $source, array $arguments, mixed $context, ResolveInfo $resolveInfo): bool
    {
        $element = MyElement::find()->id($arguments['id'])->one() ?? throw new UserError("Not found: {$arguments['id']}");
        return Craft::$app->getElements()->deleteElement($element);
    }
}
```

## Error Handling in Mutations

- **Validation** — throw `GraphQL\Error\UserError` with structured messages (see mutation resolver above). Renders in the response `errors` array.
- **Authorization** — throw `craft\errors\GqlException` when the token lacks permissions.
- **Not found** — return `null` for queries, throw `UserError` for mutations where the ID is required.
- **Response:** `{ "data": { "saveMyElement": null }, "errors": [{ "message": "...", "path": ["saveMyElement"] }] }`

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

    public static function name(): string { return 'myDirective'; }

    public static function apply(mixed $source, mixed $value, array $arguments, ResolveInfo $resolveInfo): mixed
    {
        return strtoupper($value);
    }
}
```

## Event Registration (All in Plugin `init()`)

```php
// Types must be registered first — queries and mutations depend on them
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_TYPES, function(RegisterGqlTypesEvent $event) {
    $event->types[] = MyElementInterface::class;
});
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_QUERIES, function(RegisterGqlQueriesEvent $event) {
    $event->queries = array_merge($event->queries, MyElementQuery::getQueries());
});
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_MUTATIONS, function(RegisterGqlMutationsEvent $event) {
    $event->mutations = array_merge($event->mutations, MyElementMutation::getMutations());
});
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_DIRECTIVES, function(RegisterGqlDirectivesEvent $event) {
    $event->directives[] = MyDirective::class;
});
Event::on(Gql::class, Gql::EVENT_REGISTER_GQL_SCHEMA_COMPONENTS, ...); // See Schema Components section
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

## Token Management

### Creating tokens

Tokens can be created in the CP (GraphQL -> Tokens) or via CLI:

```bash
# List available schemas and their UUIDs
ddev craft graphql/list-schemas

# Create a token for a specific schema
ddev craft graphql/create-token --schema=<schema-uid> --name="My API Token"
# The token is printed to stdout — save it immediately
```

### Authentication

```
Authorization: Bearer {your-token-here}
```

Or as a query parameter (less secure, avoid in production): `https://mysite.com/api?token={token}`

### Important notes

- Tokens are DB-only — NOT in project config. Must be created per environment. Store values in env vars.
- **Public schema** — unauthenticated, no token. Disabled by default. Enable in CP: GraphQL -> Schemas.
- **Admin "full" schema** — CP GraphiQL only. No API access, by design.

## Consumer Query Patterns

Common queries against Craft's built-in GraphQL API. No plugin needed.

### Entries

```graphql
{
  entries(section: "blog", limit: 10, orderBy: "postDate DESC") {
    ... on blog_article_Entry {
      title, slug, postDate
      heroImage { url @transform(width: 800) }
      body
    }
  }
}
```

Inline fragments are required. Type name pattern: `{sectionHandle}_{entryTypeHandle}_Entry`.

### Assets and transforms

```graphql
{ assets(volume: "images", limit: 20) { url @transform(width: 400, height: 300, mode: "crop"), title, width, height } }
```

### Relations

```graphql
{
  entry(slug: "my-post") {
    ... on blog_article_Entry {
      relatedArticles { title, url }
      author { fullName, photo { url } }
    }
  }
}
```

### Matrix / nested entries

```graphql
{
  entry(slug: "about") {
    ... on pages_page_Entry {
      bodyBuilder {
        ... on bodyBuilder_textBlock_Entry { text }
        ... on bodyBuilder_imageBlock_Entry { image { url }, caption }
      }
    }
  }
}
```

Matrix type pattern: `{fieldHandle}_{entryTypeHandle}_Entry`.

### Global sets, categories, users, pagination

```graphql
{ globalSet(handle: "siteSettings") { ... on siteSettings_GlobalSet { tagline } } }
{ categories(group: "topics") { title, slug, level, children { title } } }
{ users(group: "authors") { fullName, email, photo { url } } }  # Requires schema permissions
{ entryCount(section: "blog") entries(section: "blog", limit: 10, offset: 20) { title } }
```

No cursor-based pagination — use `entryCount`/`assetCount` with `limit`/`offset`.

## Testing GraphQL

### Craft test helper (no HTTP)

```php
use craft\test\TestCase;

it('queries custom elements', function () {
    $result = TestCase::graphql('{ myElements(limit: 5) { title, handle } }');
    expect($result['data']['myElements'])->toBeArray()->toHaveCount(5);
});

it('creates an element via mutation', function () {
    $result = TestCase::graphql('mutation { saveMyElement(input: { title: "Test" }) { id, title } }');
    expect($result['data']['saveMyElement'])->toHaveKey('id')->title->toBe('Test');
});

// Multi-site: be explicit about site context
it('queries for a specific site', function () {
    $result = TestCase::graphql('{ entries(site: "fr", section: "blog") { title } }');
    expect($result['data']['entries'])->toBeArray();
});
```

### Testing via HTTP

```bash
curl -X POST https://mysite.ddev.site/api \
  -H "Content-Type: application/json" -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"query": "{ entries(section: \"blog\", limit: 3) { title } }"}'
```

See `testing.md` for the full Pest testing reference.
