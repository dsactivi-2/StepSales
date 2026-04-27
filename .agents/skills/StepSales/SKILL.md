```markdown
# StepSales Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill teaches the core development patterns and conventions used in the StepSales TypeScript codebase. You'll learn how to structure files, write imports and exports, follow commit message conventions, and understand the approach to testing. This guide is ideal for contributors seeking to maintain consistency and quality in the StepSales project.

## Coding Conventions

### File Naming
- **Style:** Snake case
- **Example:**  
  ```text
  order_controller.ts
  user_service.ts
  ```

### Imports
- **Style:** Relative imports
- **Example:**
  ```typescript
  import { calculateTotal } from './utils/calculate_total';
  import { Order } from '../models/order';
  ```

### Exports
- **Style:** Named exports
- **Example:**
  ```typescript
  export function calculateTotal(items: Item[]): number {
    // ...
  }

  export const ORDER_STATUS = {
    PENDING: 'pending',
    COMPLETE: 'complete'
  };
  ```

### Commit Messages
- **Pattern:** Freeform, commonly starting with `add`
- **Example:**
  ```
  add order summary component and update calculation logic
  ```

## Workflows

### Adding a New Feature
**Trigger:** When implementing a new feature or module  
**Command:** `/add-feature`

1. Create a new file using snake_case naming (e.g., `new_feature.ts`).
2. Use relative imports to include dependencies.
3. Export all functions or constants using named exports.
4. Write a descriptive commit message, preferably starting with `add`.
5. If applicable, create a corresponding test file named `new_feature.test.ts`.

### Writing Tests
**Trigger:** When adding or updating code that requires testing  
**Command:** `/write-test`

1. Create a test file with the pattern `*.test.ts` (e.g., `order_controller.test.ts`).
2. Write tests for all exported functions and constants.
3. Use the project's preferred (unknown) testing framework.
4. Run tests to ensure correctness before committing.

## Testing Patterns

- **Test File Naming:**  
  Test files follow the pattern `*.test.ts`.
  ```text
  order_controller.test.ts
  utils.test.ts
  ```
- **Testing Framework:**  
  No specific framework detected; follow existing patterns or consult the team.
- **Best Practice:**  
  Ensure all exported logic is covered by corresponding test files.

## Commands
| Command        | Purpose                                         |
|----------------|-------------------------------------------------|
| /add-feature   | Scaffold and document a new feature/module      |
| /write-test    | Create and run tests for new or updated code    |
```